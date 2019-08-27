"""Logic to check the operations in all the user graphs.
This runs at the start of the database-c step, so it excludes the
graphs produced later, notably for the GC.  These are "low-level"
graphs that are assumed to be safe.

Here are again the rules around this check.

- any graph that contains only "safe" lloperations is itself "safe".
  The "safe" lloperations are the ones marked "tryfold" in
  rtyper.lltypesystem.lloperation, plus the ones listed explicitly below,
  plus a few variants of specific operations coded in graph_in_unsafe().

- any graph decorated with @objectmodel.sandbox_review() is "safe".
  The different flags we can pass to @sandbox_review() are explained next,
  but the decorated graph is itself always "safe".

- "unsafe" operations are all special rare operations, plus most importantly
  all *writes* into raw memory.  We assume that *reads* from anywhere are
  OK to ignore: any information that reaches the sandboxed process can be
  detected and used by anything that runs inside this process (i.e. there
  is no really "secret" data inside the sandboxed subprocess itself).
  At worst, random reads will lead to segfaults.  But random writes are not
  safe because that could corrupt memory---e.g. overwrite some GC object
  header, or even (although I'm not sure how) actually cause the sandboxed
  process to misbehave in more important ways like doing actual system calls
  that are supposed to be forbidden.

- the decorator @sandbox_review(check_caller=True) means that the graph is
  safe, but any call to this graph from somewhere else is an unsafe operation.
  This forces all callers to also be reviewed and marked with some form of
  @sandbox_review().

- @sandbox_review(reviewed=True) means that the graph is safe and all
  calls to this graph are also safe.  This should only be used on functions
  that do internally "unsafe" stuff like writing to raw memory but don't
  take arguments that could lead them to do bogus things.  A typical counter-
  example is a function that takes a raw pointer and that writes something to
  it; this should *not* be marked with reviewed=True.  On the other hand, many
  RPython wrappers to external C functions can be reviewed=True because
  they translate GC-safe information (say an RPython string) to raw memory,
  do the call, and translate the result back to GC-safe information.

- @sandbox_review(abort=True) is reserved for cases where calling this
  function at runtime should just immediately abort the subprocess.

Note that all flags above should be considered independently of what the
actual C function calls are supposed to do.  For example, the RPython
wrapper rposix.system() is something you definitely don't want to allow as-is,
but the wrapper and the call to the C function are fine.  It's up to the
controlling process to refuse to reply to the system() external call
(either by having it return ENOSYS or a similar error, or by killing the
sandboxed process completely).

Like system(), all calls to external C functions are *by default* removed and
turned into I/O on stdin/stdout, asking the parent controlling process what
to do.  This is controlled in more details by rffi.llexternal().  It takes
its own argument "sandboxsafe", which can be one of the following values:

- sandboxsafe=False (the default): the external C call is not done but turned
  into I/O on stdin/stdout.  Moreover, *if* the function takes or returns a
  raw pointer, then it is flagged with @sandbox_review(check_caller=True) to
  ensure that all callers do something sane with these raw pointers.  If
  the C function only takes and returns integer or float arguments, there is
  no real need, so in this case we flag @sandbox_review(reviewed=True) instead.

- sandboxsafe=True: means the external call should be done straight from the
  sandboxed process.  Reserved for specific functions like rposix.c_strerror(),
  or some memory-manipulation functions used by the GC itself.

- sandboxsafe="abort": like @sandbox_review(abort=True).

- sandboxsafe="check_caller": forces @sandbox_review(check_caller=True).
  Useful for llexternal() functions that appear to return an integer but
  that's really some address that must be carefully managed.

- sandboxsafe="nowrite": forces @sandbox_review(reviewed=True).  This is OK
  for C functions that have pointer arguments but none of them can point
  to anything that will be written to (hence the name).  The idea is that
  for the common case of a function that takes a "const char *" argument,
  we should just mark that function as reviewed=True, because it is safe:
  the controller process will at most read things from the sandboxed process,
  namely what the pointer points to, but it should not attempt to do any
  write into the sandboxed process' memory.  Typically the caller itself
  calls rffi.str2charp() and rffi.free_charp() around the call, but these
  are also @sandbox_review(reviewed=True) helpers, so such a caller doesn't
  need to be explicitly reviewed.

"""


from rpython.flowspace.model import SpaceOperation, Constant
from rpython.rtyper.rmodel import inputconst
from rpython.rtyper.lltypesystem import lltype, llmemory, rstr
from rpython.rtyper.lltypesystem.lloperation import LL_OPERATIONS
from rpython.translator.unsimplify import varoftype
from rpython.tool.ansi_print import AnsiLogger

class UnsafeException(Exception):
    pass

log = AnsiLogger("sandbox")

safe_operations = set([
    'keepalive', 'threadlocalref_get', 'threadlocalref_store',
    'malloc', 'malloc_varsize', 'free',
    'getfield', 'getarrayitem', 'getinteriorfield', 'raw_load',
    'cast_opaque_ptr', 'cast_ptr_to_int',
    'gc_thread_run', 'gc_stack_bottom',
    'gc_thread_before_fork', 'gc_thread_after_fork',
    'shrink_array', 'gc_pin', 'gc_unpin', 'gc_can_move', 'gc_id',
    'gc_identityhash', 'weakref_create', 'weakref_deref',
    'gc_fq_register', 'gc_fq_next_dead',
    'gc_set_max_heap_size', 'gc_ignore_finalizer', 'gc_add_memory_pressure',
    'gc_writebarrier', 'gc__collect',
    'length_of_simple_gcarray_from_opaque',
    'debug_fatalerror', 'debug_print_traceback', 'debug_flush',
    'hint', 'debug_start', 'debug_stop', 'debug_print', 'debug_offset',
    'jit_force_quasi_immutable', 'jit_force_virtual', 'jit_marker',
    'jit_is_virtual',
    ])
gc_set_operations = set([
    'setfield', 'setarrayitem', 'setinteriorfield',
    ])
for opname, opdesc in LL_OPERATIONS.items():
    if opdesc.tryfold:
        safe_operations.add(opname)

def graph_review(graph):
    return getattr(getattr(graph, 'func', None), '_sandbox_review_', None)

def make_abort_graph(graph):
    ll_err = rstr.conststr("reached forbidden function %r" % (graph.name,))
    c_err = inputconst(lltype.typeOf(ll_err), ll_err)
    op = SpaceOperation('debug_fatalerror', [c_err], varoftype(lltype.Void))
    graph.startblock.operations.insert(0, op)

def is_gc_ptr(TYPE):
    return isinstance(TYPE, lltype.Ptr) and TYPE.TO._gckind == 'gc'


class GraphChecker(object):

    def __init__(self, translator):
        self.translator = translator

    def graph_is_unsafe(self, graph):
        for block, op in graph.iterblockops():
            opname = op.opname

            if opname in safe_operations:
                pass

            elif opname in gc_set_operations:
                if op.args[0].concretetype.TO._gckind != 'gc':
                    return "non-GC memory write: %r" % (op,)

            elif opname == 'direct_call':
                c_target = op.args[0]
                assert isinstance(c_target, Constant)
                TYPE = lltype.typeOf(c_target.value)
                assert isinstance(TYPE.TO, lltype.FuncType)
                obj = c_target.value._obj
                if hasattr(obj, 'graph'):
                    g2 = obj.graph
                    if graph_review(g2) == 'check_caller':
                        return ("direct_call to a graph with "
                                "check_caller=True: %r" % (op,))
                elif getattr(obj, '_safe_not_sandboxed', False) is not False:
                    ss = obj._safe_not_sandboxed
                    if ss is not True:
                        return ("direct_call to llfunc with "
                                "sandboxsafe=%r: %r" % (ss, obj))
                elif getattr(obj, 'external', None) is not None:
                    # either obj._safe_not_sandboxed is True, and then it's
                    # fine; or obj._safe_not_sandboxed is False, and then
                    # this will be transformed into a stdin/stdout stub
                    pass
                else:
                    # not 'external', but no 'graph' either?
                    return "direct_call to %r" % (obj,)

            elif opname == 'indirect_call':
                graph_list = op.args[-1].value
                for g2 in graph_list:
                    if graph_review(g2) == 'check_caller':
                        return ("indirect_call that can go to at least one "
                                "graph with check_caller=True: %r" % (op,))

            elif opname in ('cast_ptr_to_adr', 'force_cast',
                            'cast_int_to_ptr'):
                if is_gc_ptr(op.result.concretetype):
                    return "result is a GC ptr: %r" % (op,)

            else:
                return "unsupported llop: %r" % (opname,)

    def check(self):
        unsafe = {}
        for graph in self.translator.graphs:
            review = graph_review(graph)
            if review is not None:
                if review in ('reviewed', 'check_caller'):
                    continue
                elif review == 'abort':
                    make_abort_graph(graph)
                    continue
                else:
                    assert False, repr(review)

            problem = self.graph_is_unsafe(graph)
            if problem is not None:
                unsafe[graph] = problem
        if unsafe:
            raise UnsafeException(
                '\n'.join('%r: %s' % kv for kv in unsafe.items()))


def check_all_graphs(translator):
    log("Checking the graphs for sandbox-unsafe operations")
    checker = GraphChecker(translator)
    checker.check()

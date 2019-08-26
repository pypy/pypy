"""Logic to check the operations in all the user graphs.
This runs at the start of the database-c step, so it excludes the
graphs produced later, notably for the GC.  These are "low-level"
graphs that are assumed to be safe.
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
    'gc_thread_run', 'gc_stack_bottom', 'gc_thread_after_fork',
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
                if is_gc_ptr(op.args[0].concretetype):
                    return "argument is a GC ptr: %r" % (opname,)
                if is_gc_ptr(op.result.concretetype):
                    return "result is a GC ptr: %r" % (opname,)

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

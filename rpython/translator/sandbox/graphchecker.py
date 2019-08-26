"""Logic to check the operations in all the user graphs.
This runs at the start of the database-c step, so it excludes the
graphs produced later, notably for the GC.  These are "low-level"
graphs that are assumed to be safe.
"""

from rpython.flowspace.model import SpaceOperation, Constant
from rpython.rtyper.rmodel import inputconst
from rpython.rtyper.lltypesystem import lltype, llmemory, rstr
from rpython.rtyper.lltypesystem.rffi import sandbox_check_type
from rpython.rtyper.lltypesystem.lloperation import LL_OPERATIONS
from rpython.translator.unsimplify import varoftype
from rpython.tool.ansi_print import AnsiLogger

class UnsafeException(Exception):
    pass

log = AnsiLogger("sandbox")

safe_operations = set([
    'keepalive', 'threadlocalref_get', 'threadlocalref_store',
    'malloc', 'malloc_varsize', 'free',
    'getfield', 'getarrayitem', 'getinteriorfield',
    'gc_thread_run',
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
                        return "caller has not been checked: %r" % (op,)
                elif getattr(obj, 'sandboxsafe', False):
                    pass
                elif getattr(obj, 'external', None) is not None:
                    # either obj._safe_not_sandboxed is True, and then it's
                    # fine; or obj._safe_not_sandboxed is False, and then
                    # this will be transformed into a stdin/stdout stub
                    pass
                else:
                    return "direct_call to %r" % (obj,)

            elif opname == 'force_cast':
                if sandbox_check_type(op.result.concretetype):
                    return "force_cast to pointer type: %r" % (op,)
                if sandbox_check_type(op.args[0].concretetype):
                    return "force_cast from pointer type: %r" % (op,)
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

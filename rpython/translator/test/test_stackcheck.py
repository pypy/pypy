from rpython.conftest import option
from rpython.translator.translator import TranslationContext, graphof
from rpython.translator.backendopt.all import backend_optimizations
from rpython.translator.transform import insert_ll_stackcheck
from rpython.memory.gctransform import shadowstack

def _follow_path_naive(block, cur_path, accum):
    cur_path = (cur_path, block)
    if not block.exits:
        ops = []
        while cur_path:
            block = cur_path[1]
            ops.extend(reversed(block.operations))
            cur_path = cur_path[0]
        accum.append(list(reversed(ops)))
        return
    for link in block.exits:
        _follow_path_naive(link.target, cur_path, accum)

# explodes on loops!
def paths_naive(g):
    accum = []
    _follow_path_naive(g.startblock, None, accum)
    return accum

def direct_target(spaceop):
    obj = spaceop.args[0].value._obj
    if hasattr(obj, 'graph'):
        return obj.graph.name
    return obj._name

def direct_calls(p):
    names = []
    for spaceop in p:
        if spaceop.opname == 'direct_call':
            names.append(direct_target(spaceop))
    return names

SLOWPATH_NAME = 'stack_check_slowpath__Signed'
# First call in the inlined stack_check body; present on every path (fast and slow).
FASTPATH_SENTINEL = 'LL_stack_get_end'

def check(g, funcname, ignore=None):
    paths = paths_naive(g)
    relevant = []
    for p in paths:
        funcs_called = direct_calls(p)
        if funcname in funcs_called and ignore not in funcs_called:
            assert FASTPATH_SENTINEL in funcs_called
            assert (funcs_called.index(funcname) >
                    funcs_called.index(FASTPATH_SENTINEL))
            relevant.append(p)
    return relevant
    

class A(object):
    def __init__(self, n):
        self.n = n

def f(a):
    x = A(a.n+1)
    if x.n == 10:
        return
    f(x)

def g(n):
    f(A(n))
    return 0

def test_simple():
    t = TranslationContext()
    a = t.buildannotator()
    a.build_types(g, [int])
    a.simplify()
    t.buildrtyper().specialize()        
    backend_optimizations(t)
    t.checkgraphs()
    n = insert_ll_stackcheck(t)
    t.checkgraphs()
    assert n == 1
    if option.view:
        t.view()
    check(graphof(t, f), 'f')

def test_gctransformed():
    t = TranslationContext()
    a = t.buildannotator()
    a.build_types(g, [int])
    a.simplify()
    t.buildrtyper().specialize()        
    backend_optimizations(t)
    t.checkgraphs()
    n = insert_ll_stackcheck(t)
    t.checkgraphs()
    assert n == 1
    exctransf = t.getexceptiontransformer()
    f_graph = graphof(t, f)
    exctransf.create_exception_handling(f_graph)
    if option.view:
        f_graph.show()
    check(f_graph, 'f')    

    class GCTransform(shadowstack.ShadowStackFrameworkGCTransformer):
        from rpython.memory.gc.generation import GenerationGC as \
                                                          GCClass
        GC_PARAMS = {}

    gctransf = GCTransform(t)
    gctransf.transform_graph(f_graph)
    if option.view:
        f_graph.show()
    relevant = check(f_graph, 'f')        
    for p in relevant:
        in_between = False
        reload = 0
        for spaceop in p:
            if spaceop.opname == 'direct_call':
                target = direct_target(spaceop)
                if target == 'f':
                    in_between = False
                elif target == FASTPATH_SENTINEL:
                    in_between = True
            if in_between and spaceop.opname == 'gc_reload_possibly_moved':
                reload += 1
                
        assert reload == 0

def all_direct_calls(g):
    """Return all direct_call target names across every block in the graph."""
    names = []
    for block in g.iterblocks():
        for op in block.operations:
            if op.opname == 'direct_call':
                names.append(direct_target(op))
    return names

def test_fastpath_inlined():
    # After insert_ll_stackcheck the stack_check function must be inlined at
    # each call site: no direct_call to stack_check___ should remain, and the
    # slow-path call must be present instead.
    t = TranslationContext()
    a = t.buildannotator()
    a.build_types(g, [int])
    a.simplify()
    t.buildrtyper().specialize()
    backend_optimizations(t)
    t.checkgraphs()
    insert_ll_stackcheck(t)
    t.checkgraphs()
    calls = all_direct_calls(graphof(t, f))
    assert 'stack_check___' not in calls
    assert SLOWPATH_NAME in calls

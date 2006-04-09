import py
from pypy.translator.translator import TranslationContext
from pypy.translator.backendopt.inline import inline_function
from pypy.translator.backendopt.all import backend_optimizations
from pypy.translator.translator import TranslationContext, graphof
from pypy.rpython.llinterp import LLInterpreter
from pypy.objspace.flow.model import checkgraph, flatten, Block
from pypy.conftest import option

from pypy.translator.backendopt.mallocprediction import *

def rtype(fn, signature):
    t = TranslationContext()
    t.buildannotator().build_types(fn, signature)
    t.buildrtyper().specialize()
    graph = graphof(t, fn)
    if option.view:
        t.view()
    return t, graph
    

def check_inlining(t, graph, args, result):
    callgraph, caller_candidates = find_malloc_removal_candidates(t)
    nice_callgraph = {}
    for caller, callee in callgraph:
        nice_callgraph.setdefault(caller, {})[callee] = True
    inline_and_remove(t)
    if option.view:
        t.view()
    interp = LLInterpreter(t.rtyper)
    res = interp.eval_graph(graph, args)
    assert res == result
    return nice_callgraph, caller_candidates

def test_fn():
    class A:
        pass
    class B(A):
        pass
    def g(a, b, i):
        a.b = b
        b.i = i
        return a.b.i
    def h(x):
        return x + 42
    def fn(i):
        a = A()
        b = B()
        x = h(i)
        return g(a, b, x)
    t, graph = rtype(fn, [int])
    callgraph, caller_candidates = check_inlining(t, graph, [0], 42)
    assert caller_candidates == {graph: True}
    assert len(callgraph) == 1
    ggraph = graphof(t, g)
    assert callgraph[graph] == {ggraph: True}

def test_multiple_calls():
    class A:
        pass
    class B(A):
        pass
    def g2(b, i): 
        b.i = h(i)
    def g1(a, b, i):
        a.b = b
        g2(b, h(i))
        return a.b.i
    def h(x):
        return x + 42
    def fn(i):
        a = A()
        b = B()
        x = h(i)
        return g1(a, b, x)
    t, graph = rtype(fn, [int])
    callgraph, caller_candidates = check_inlining(t, graph, [0], 3 * 42)
    print callgraph
    assert caller_candidates == {graph: True}
    assert len(callgraph) == 1
    g1graph = graphof(t, g1)
    g2graph = graphof(t, g2)
    assert callgraph[graph] == {g1graph: True}
    callgraph, caller_candidates = check_inlining(t, graph, [0], 3 * 42)
    assert callgraph[graph] == {g2graph: True}
    
def test_pystone():
    from pypy.translator.goal.targetrpystonex import make_target_definition
    entrypoint, _, _ = make_target_definition(10)
    # does not crash
    t, graph = rtype(entrypoint, [int])
    total = clever_inlining_and_malloc_removal(t)
    assert total == 12

def test_richards():
    from pypy.translator.goal.richards import entry_point
    t, graph = rtype(entry_point, [int])
    total = clever_inlining_and_malloc_removal(t)
    assert total == 11

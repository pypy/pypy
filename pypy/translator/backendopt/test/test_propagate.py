from pypy.translator.translator import Translator
from pypy.translator.backendopt.propagate import *
from pypy.rpython.llinterp import LLInterpreter


def get_graph(fn, signature):
    t = Translator(fn)
    t.annotate(signature)
    t.specialize()
    t.backend_optimizations(ssa_form=False, propagate=False) 
    graph = t.getflowgraph()
    return graph, t

def check_graph(graph, args, expected_result, t):
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    res = interp.eval_function(None, args, graph=graph)
    assert res == expected_result

def check_get_graph(fn, signature, args, expected_result):
    graph, t = get_graph(fn, signature)
    check_graph(graph, args, expected_result, t)
    return graph

def test_inline_and():
    def f(x):
        return x != 1 and x != 5 and x != 42
    def g(x):
        ret = 0
        for i in range(x):
            if f(x):
                ret += x
            else:
                ret += x + 1
        return ret
    graph, t = get_graph(g, [int])
    propagate_consts(graph)
    assert len(graph.startblock.exits[0].args) == 4
    check_graph(graph, [100], g(100), t)
    
def test_dont_fold_return():
    def f(x):
        return
    graph, t = get_graph(f, [int])
    propagate_consts(graph)
    assert len(graph.startblock.exits[0].args) == 1
    check_graph(graph, [1], None, t)

def test_constant_fold():
    def f(x):
        return 1
    def g(x):
        return 1 + f(x)
    graph, t = get_graph(g, [int])
    constant_folding(graph, t)
    assert len(graph.startblock.operations) == 0
    check_graph(graph, [1], g(1), t)

def test_constant_fold_call():
    def s(x):
        res = 0
        for i in range(1, x + 1):
            res += i
        return res
    def g(x):
        return s(100) + s(1) + x
    graph, t = get_graph(g, [int])
    while constant_folding(graph, t):
        pass
    assert len(graph.startblock.operations) == 1
    check_graph(graph, [10], g(10), t)

def test_fold_const_blocks():
    def s(x):
        res = 0
        i = 1
        while i < x:
            res += i
            i += 1
        return res
    def g(x):
        return s(100) + s(99) + x
    graph, t = get_graph(g, [int])
    partial_folding(graph, t)
    constant_folding(graph, t)
    assert len(graph.startblock.operations) == 1
    check_graph(graph, [10], g(10), t)


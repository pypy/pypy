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
    assert len(graph.startblock.operations) == 4
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
    assert len(graph.startblock.operations) == 3
    check_graph(graph, [10], g(10), t)

def getitem(l, i):  #LookupError, KeyError
    if not isinstance(i, int):
        raise TypeError
    if i < 0:
        i = len(l) - i
    if i>= len(l):
        raise IndexError
    return l[i]

def test_dont_coalesce_except():
    def fn(n):
        lst = range(10)
        try:
            getitem(lst,n)
        except:
            pass
        return 4
    graph, t = get_graph(fn, [int])
    coalesce_links(graph)
    check_graph(graph, [-1], fn(-1), t)

def list_default_argument(i1, l1=[0]):
    l1.append(i1)
    return len(l1) + l1[-2]

def call_list_default_argument(i1):
    return list_default_argument(i1)
    
def test_call_list_default_argument():
    graph, t = get_graph(call_list_default_argument, [int])
    t.backend_optimizations(propagate=True, ssa_form=False) 
    for i in range(10):
        check_graph(graph, [i], call_list_default_argument(i), t)

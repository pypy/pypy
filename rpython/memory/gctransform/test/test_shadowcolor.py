from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.test.test_llinterp import gengraph
from rpython.conftest import option
from rpython.memory.gctransform.shadowcolor import *


def make_graph(f, argtypes):
    t, rtyper, graph = gengraph(f, argtypes, viewbefore=False)
    if getattr(option, 'view', False):
        graph.show()
    return graph

def summary(interesting_vars):
    result = {}
    for v in interesting_vars:
        name = v._name.rstrip('_')
        result[name] = result.get(name, 0) + 1
    return result


def test_find_predecessors_1():
    def f(a, b):
        c = a + b
        return c
    graph = make_graph(f, [int, int])
    pred = find_precessors(graph, [(graph.returnblock, graph.getreturnvar())])
    assert summary(pred) == {'c': 1, 'v': 1}

def test_find_predecessors_2():
    def f(a, b):
        c = a + b
        while a > 0:
            a -= 2
        return c
    graph = make_graph(f, [int, int])
    pred = find_precessors(graph, [(graph.returnblock, graph.getreturnvar())])
    assert summary(pred) == {'c': 3, 'v': 1}

def test_find_predecessors_3():
    def f(a, b):
        while b > 100:
            b -= 2
        if b > 10:
            c = a + b      # 'c' created in this block
        else:
            c = a - b      # 'c' created in this block
        return c           # 'v' is the return var
    graph = make_graph(f, [int, int])
    pred = find_precessors(graph, [(graph.returnblock, graph.getreturnvar())])
    assert summary(pred) == {'c': 2, 'v': 1}

def test_find_predecessors_4():
    def f(a, b):           # 'a' in the input block
        while b > 100:     # 'a' in the loop header block
            b -= 2         # 'a' in the loop body block
        if b > 10:         # 'a' in the condition block
            while b > 5:   # nothing
                b -= 2     # nothing
            c = a + b      # 'c' created in this block
        else:
            c = a
        return c           # 'v' is the return var
    graph = make_graph(f, [int, int])
    pred = find_precessors(graph, [(graph.returnblock, graph.getreturnvar())])
    assert summary(pred) == {'a': 4, 'c': 1, 'v': 1}


def test_interesting_vars_0():
    def f(a, b):
        pass
    graph = make_graph(f, [llmemory.GCREF, int])
    assert not find_interesting_variables(graph)

def test_interesting_vars_1():
    def f(a, b):
        llop.gc_push_roots(lltype.Void, a)
        llop.gc_pop_roots(lltype.Void, a)
    graph = make_graph(f, [llmemory.GCREF, int])
    assert summary(find_interesting_variables(graph)) == {'a': 1}

def test_interesting_vars_2():
    def f(a, b, c):
        llop.gc_push_roots(lltype.Void, a)
        llop.gc_pop_roots(lltype.Void, a)
        while b > 0:
            b -= 5
        llop.gc_push_roots(lltype.Void, c)
        llop.gc_pop_roots(lltype.Void, c)
    graph = make_graph(f, [llmemory.GCREF, int, llmemory.GCREF])
    assert summary(find_interesting_variables(graph)) == {'a': 1, 'c': 1}

def test_interesting_vars_3():
    def f(a, b):
        llop.gc_push_roots(lltype.Void, a)
        llop.gc_pop_roots(lltype.Void, a)
        while b > 0:   # 'a' remains interesting across the blocks of this loop
            b -= 5
        llop.gc_push_roots(lltype.Void, a)
        llop.gc_pop_roots(lltype.Void, a)
    graph = make_graph(f, [llmemory.GCREF, int])
    assert summary(find_interesting_variables(graph)) == {'a': 4}

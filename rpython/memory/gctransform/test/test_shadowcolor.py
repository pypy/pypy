from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.test.test_llinterp import gengraph
from rpython.conftest import option
from rpython.memory.gctransform.shadowcolor import find_interesting_variables


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

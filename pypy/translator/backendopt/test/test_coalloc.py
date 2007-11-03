from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.backendopt.coalloc import AbstractDataFlowInterpreter
from pypy.rpython.llinterp import LLInterpreter
from pypy.rlib.objectmodel import instantiate
from pypy import conftest

import py

def build_adi(function, types):
    t = TranslationContext()
    t.buildannotator().build_types(function, types)
    t.buildrtyper().specialize()
    if conftest.option.view:
        t.view()
    adi = AbstractDataFlowInterpreter(t)
    graph = graphof(t, function)
    adi.schedule_function(graph)
    adi.complete()
    return t, adi, graph

def test_simple():
    class A(object):
        pass
    def f():
        a = A()
        a.x = 1
        return a.x
    t, adi, graph = build_adi(f, [])
    avar = graph.startblock.operations[0].result
    state = adi.getstate(avar)
    assert len(state.creation_points) == 1
    crep = state.creation_points.keys()[0]

def test_branch():
    class T:
        pass
    def fn2(x, y):
        t = T()
        t.x = x
        t.y = y
        if x > 0:
            return t.x + t.y
        else:
            return t.x - t.y
    t, adi, graph = build_adi(fn2, [int, int])
    tvar = graph.startblock.operations[0].result
    state = adi.getstate(tvar)
    assert len(state.creation_points) == 1
    crep = state.creation_points.keys()[0]
    assert crep.creation_method == "malloc"

def test_loop():
    class A(object):
        pass
    def f():
        a = A()
        i = 0
        while i < 3:
            a.x = i
            a = A()
            i += 1
        return a.x
    t, adi, graph = build_adi(f, [])
    avar = graph.startblock.operations[0].result
    state = adi.getstate(avar)
    assert len(state.creation_points) == 1
    crep = state.creation_points.keys()[0]
    assert crep.creation_method == "malloc"
    avarinloop = graph.startblock.exits[0].target.inputargs[1]
    state1 = adi.getstate(avarinloop)
    assert crep in state1.creation_points
    assert len(state1.creation_points) == 2

def test_global():
    class A(object):
        pass
    globala = A()
    def f():
        a = A()
        a.next = None
        globala.next = a
    t, adi, graph = build_adi(f, [])
    avar = graph.startblock.operations[0].result
    state = adi.getstate(avar)
    assert len(state.creation_points) == 1
    crep = state.creation_points.keys()[0]
    assert crep.creation_method == "malloc"
    const = graph.startblock.operations[-1].args[0]
    state = adi.getstate(const)
    assert len(state.creation_points) == 1
    crep = state.creation_points.keys()[0]
    assert crep.creation_method == "constant"

def test_aliasing():
    class A:
        pass
    def fn6(n):
        a1 = A()
        a1.x = 5
        a2 = A()
        a2.x = 6
        if n > 0:
            a = a1
        else:
            a = a2
        a.x = 12
        return a1.x
    t, adi, graph = build_adi(fn6, [int])
    avar = graph.startblock.exits[0].target.inputargs[1]
    state = adi.getstate(avar)
    assert len(state.creation_points) == 2
    for crep in state.creation_points.keys():
        assert crep.creation_method == "malloc"


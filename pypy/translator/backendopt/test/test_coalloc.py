from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.backendopt.coalloc import AbstractDataFlowInterpreter, malloc_to_coalloc
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

def check_malloc_to_coalloc(function, types, args, expected_result, must_remove=-1):
    t = TranslationContext()
    t.buildannotator().build_types(function, types)
    t.buildrtyper().specialize()
    interp = LLInterpreter(t.rtyper)
    graph = graphof(t, function)
    res = interp.eval_graph(graph, args)
    assert res == expected_result
    num = malloc_to_coalloc(t)
    if must_remove == -1:
        for block in graph.iterblocks():
            for op in block.operations:
                assert op.opname != "malloc"
    else:
        assert num == must_remove
    if conftest.option.view:
        t.view()
    res = interp.eval_graph(graph, args)
    assert res == expected_result
    return t


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

def test_coalloc_constants():
    class A(object):
        pass
    a = A()
    def f():
        n = A()
        a.next = n
        return 1
    check_malloc_to_coalloc(f, [], [], 1)

def test_nocoalloc_aliasing():
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
    t = check_malloc_to_coalloc(fn6, [int], [2], 12, must_remove=0)

def test_coalloc_with_arg():
    class A(object):
        pass
    def g(b):
        b.x = A()
    def f():
        a = A()
        g(a)
        a.i = 2
        return 4
    t = check_malloc_to_coalloc(f, [], [], 4, must_remove=1)

def test_coalloc_with_arg_set_in_same_block():
    class A(object):
        pass
    a1 = A()
    def g(cond, b):
        if cond:
            b = a1
        b.x = A()
    def f(cond):
        a2 = A()
        g(cond, a2)
        return 4
    t = check_malloc_to_coalloc(f, [bool], [True], 4, must_remove=1)

def test_coalloc_with_arg_several_creationpoints():
    class A(object):
        pass
    a1 = A()
    def g(cond, b):
        a = A()
        if cond:
            b = a1
        b.x = a
    def f(cond):
        a2 = A()
        g(cond, a2)
        return 4
    t = check_malloc_to_coalloc(f, [bool], [True], 4, must_remove=1)


def test_coalloc_list():
    class A(object):
        pass
    a1 = A()
    def f(count):
        i = 0
        l = []
        while i < count:
            l.append(A())
            i += 1
        return len(l)
    t = check_malloc_to_coalloc(f, [int], [8], 8, must_remove=1)

def test_coalloc_dict():
    class A(object):
        pass
    a1 = A()
    def f(count):
        i = 0
        d = {}
        while i < count:
            d[i] = A()
            i += 1
        return len(d)
    t = check_malloc_to_coalloc(f, [int], [8], 8, must_remove=1)

def test_nocoalloc_bug():
    class A(object):
        pass
    a1 = A()
    def g(a):
        a.items = A()
    def f(count):
        a = A()
        a.length = count
        g(a)
        return a.length
    t = check_malloc_to_coalloc(f, [int], [8], 8, must_remove=1)

from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.backendopt.escape import AbstractDataFlowInterpreter 

def build_adi(function, types):
    t = TranslationContext()
    t.buildannotator().build_types(function, types)
    t.buildrtyper().specialize()
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
    assert crep.changes
    assert not crep.escapes

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
    assert crep.changes
    assert not crep.escapes

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
    assert crep.changes
    assert not crep.escapes
    avarinloop = graph.startblock.exits[0].target.inputargs[1]
    #t.view()
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
    assert crep.changes
    assert crep.escapes

def test_classattrs():
    class A:
        attr = 666
    class B(A):
        attr = 42
    def fn5():
        b = B()
        return b.attr
    t, adi, graph = build_adi(fn5, [])
    bvar = graph.startblock.operations[0].result
    state = adi.getstate(bvar)
    assert len(state.creation_points) == 1
    crep = state.creation_points.keys()[0]
    assert crep.changes
    assert not crep.escapes

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
        assert crep.changes
        assert not crep.escapes

def test_call():
    class A(object):
        pass
    globala = A()
    def g(b):
        return b.i + 2
    def f():
        a = A()
        a.i = 2
        return g(a)
    t, adi, graph = build_adi(f, [])
    g_graph = graphof(t, g)
    bvar = g_graph.startblock.inputargs[0]
    bstate = adi.getstate(bvar)
    assert len(bstate.creation_points) == 1
    bcrep = bstate.creation_points.keys()[0]
    assert not bcrep.changes
    assert not bcrep.escapes
    avar = graph.startblock.operations[0].result
    astate = adi.getstate(avar)
    assert len(astate.creation_points) == 1
    acrep = astate.creation_points.keys()[0]
    assert acrep.changes
    assert not acrep.escapes

def test_substruct():
    class A(object):
        pass
    class B(object):
        pass
    def g(a, b):
        a.b = b
        a.b.x = 1
        return a.b
    def f():
        a0 = A()
        b0 = B()
        return g(a0, b0).x
    t, adi, graph = build_adi(f, [])
    g_graph = graphof(t, g)
    a0var = graph.startblock.operations[0].result
    b0var = graph.startblock.operations[3].result 
    a0state = adi.getstate(a0var)
    b0state = adi.getstate(b0var)
    assert len(a0state.creation_points) == 1
    a0crep = a0state.creation_points.keys()[0]
    assert not a0crep.escapes
    assert a0crep.changes
    assert len(b0state.creation_points) == 1
    b0crep = b0state.creation_points.keys()[0]
    assert b0crep.escapes
    assert b0crep.changes

def test_multiple_calls():
    class A(object):
        pass
    def h(a, b):
        a.x = 1
        return b
    def g(a, b):
        return h(b, a)
    def f():
        a1 = A()
        a2 = A()
        a3 = A()
        a4 = h(a1, a2)
        a5 = g(a3, a4)
    t, adi, graph = build_adi(f, [])
    a1var = graph.startblock.operations[0].result
    a2var = graph.startblock.operations[3].result
    a3var = graph.startblock.operations[6].result
    a1state = adi.getstate(a1var)
    a2state = adi.getstate(a2var)
    a3state = adi.getstate(a3var)
    assert len(a1state.creation_points) == 1
    assert len(a2state.creation_points) == 1
    assert len(a3state.creation_points) == 1
    a1crep = a1state.creation_points.keys()[0]
    a2crep = a2state.creation_points.keys()[0]
    a3crep = a3state.creation_points.keys()[0]
    assert a1crep.changes and a2crep.changes and a3crep.changes
    assert not a1crep.escapes and a2crep.escapes and a3crep.escapes

def test_indirect_call():
    class A(object):
        pass
    def f1(a):
        return a.x
    def f2(a):
        return a.x + 1
    def g1(a):
        return a
    def g2(a):
        return None
    def f(i):
        a1 = A()
        a2 = A()
        a1.x = 1
        a2.x = 2
        if i:
            f = f1
            g = g1
        else:
            f = f2
            g = g2
        x = f(a1)
        a0 = g(a2)
        if a0 is not None:
            return x
        else:
            return 42
    t, adi, graph = build_adi(f, [int])
    a1var = graph.startblock.operations[0].result
    a2var = graph.startblock.operations[3].result
    a1state = adi.getstate(a1var)
    a2state = adi.getstate(a2var)
    assert len(a1state.creation_points) == 1
    assert len(a2state.creation_points) == 1
    a1crep = a1state.creation_points.keys()[0]
    a2crep = a2state.creation_points.keys()[0]
    assert a1crep.changes and a2crep.changes
    assert not a1crep.escapes and a2crep.escapes

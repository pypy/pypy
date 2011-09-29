from pypy.rpython.test.test_llinterp import gengraph, interpret
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rlib import rgc # Force registration of gc.collect
import gc
import py, sys

def test_collect():
    def f():
        return gc.collect()

    t, typer, graph = gengraph(f, [])
    ops = list(graph.iterblockops())
    assert len(ops) == 1
    op = ops[0][1]
    assert op.opname == 'gc__collect'
    assert len(op.args) == 0

    res = interpret(f, [])

    assert res is None

def test_collect_0():
    if sys.version_info < (2, 5):
        py.test.skip("requires Python 2.5 to call gc.collect() with an arg")

    def f():
        return gc.collect(0)

    t, typer, graph = gengraph(f, [])
    ops = list(graph.iterblockops())
    assert len(ops) == 1
    op = ops[0][1]
    assert op.opname == 'gc__collect'
    assert len(op.args) == 1
    assert op.args[0].value == 0

    res = interpret(f, [])

    assert res is None

def test_can_move():
    T0 = lltype.GcStruct('T')
    T1 = lltype.GcArray(lltype.Float)
    def f(i):
        if i:
            return rgc.can_move(lltype.malloc(T0))
        else:
            return rgc.can_move(lltype.malloc(T1, 1))

    t, typer, graph = gengraph(f, [int])
    ops = list(graph.iterblockops())
    res = [op for op in ops if op[1].opname == 'gc_can_move']
    assert len(res) == 2

    res = interpret(f, [1])

    assert res == True

def test_ll_arraycopy_1():
    TYPE = lltype.GcArray(lltype.Signed)
    a1 = lltype.malloc(TYPE, 10)
    a2 = lltype.malloc(TYPE, 6)
    for i in range(10): a1[i] = 100 + i
    for i in range(6):  a2[i] = 200 + i
    rgc.ll_arraycopy(a1, a2, 4, 2, 3)
    for i in range(10):
        assert a1[i] == 100 + i
    for i in range(6):
        if 2 <= i < 5:
            assert a2[i] == a1[i+2]
        else:
            assert a2[i] == 200 + i

def test_ll_arraycopy_2():
    TYPE = lltype.GcArray(lltype.Void)
    a1 = lltype.malloc(TYPE, 10)
    a2 = lltype.malloc(TYPE, 6)
    rgc.ll_arraycopy(a1, a2, 4, 2, 3)
    # nothing to assert here, should not crash...

def test_ll_arraycopy_3():
    S = lltype.Struct('S')    # non-gc
    TYPE = lltype.GcArray(lltype.Ptr(S))
    a1 = lltype.malloc(TYPE, 10)
    a2 = lltype.malloc(TYPE, 6)
    org1 = [None] * 10
    org2 = [None] * 6
    for i in range(10): a1[i] = org1[i] = lltype.malloc(S, immortal=True)
    for i in range(6):  a2[i] = org2[i] = lltype.malloc(S, immortal=True)
    rgc.ll_arraycopy(a1, a2, 4, 2, 3)
    for i in range(10):
        assert a1[i] == org1[i]
    for i in range(6):
        if 2 <= i < 5:
            assert a2[i] == a1[i+2]
        else:
            assert a2[i] == org2[i]

def test_ll_arraycopy_4():
    S = lltype.GcStruct('S')
    TYPE = lltype.GcArray(lltype.Ptr(S))
    a1 = lltype.malloc(TYPE, 10)
    a2 = lltype.malloc(TYPE, 6)
    org1 = [None] * 10
    org2 = [None] * 6
    for i in range(10): a1[i] = org1[i] = lltype.malloc(S)
    for i in range(6):  a2[i] = org2[i] = lltype.malloc(S)
    rgc.ll_arraycopy(a1, a2, 4, 2, 3)
    for i in range(10):
        assert a1[i] == org1[i]
    for i in range(6):
        if 2 <= i < 5:
            assert a2[i] == a1[i+2]
        else:
            assert a2[i] == org2[i]

def test_ll_arraycopy_5(monkeypatch):
    S = lltype.GcStruct('S')
    TYPE = lltype.GcArray(lltype.Ptr(S))
    def f():
        a1 = lltype.malloc(TYPE, 10)
        a2 = lltype.malloc(TYPE, 6)
        rgc.ll_arraycopy(a2, a1, 0, 1, 5)

    CHK = lltype.Struct('CHK', ('called', lltype.Bool))
    check = lltype.malloc(CHK, immortal=True)

    def raw_memcopy(*args):
        check.called = True

    monkeypatch.setattr(llmemory, "raw_memcopy", raw_memcopy)

    interpret(f, [])

    assert check.called



def test_ll_shrink_array_1():
    py.test.skip("implement ll_shrink_array for GcStructs or GcArrays that "
                 "don't have the shape of STR or UNICODE")

def test_ll_shrink_array_2():
    S = lltype.GcStruct('S', ('x', lltype.Signed),
                             ('vars', lltype.Array(lltype.Signed)))
    s1 = lltype.malloc(S, 5)
    s1.x = 1234
    for i in range(5):
        s1.vars[i] = 50 + i
    s2 = rgc.ll_shrink_array(s1, 3)
    assert lltype.typeOf(s2) == lltype.Ptr(S)
    assert s2.x == 1234
    assert len(s2.vars) == 3
    for i in range(3):
        assert s2.vars[i] == 50 + i

def test_get_referents():
    class X(object):
        __slots__ = ['stuff']
    x1 = X()
    x1.stuff = X()
    x2 = X()
    lst = rgc.get_rpy_referents(rgc.cast_instance_to_gcref(x1))
    lst2 = [rgc.try_cast_gcref_to_instance(X, x) for x in lst]
    assert x1.stuff in lst2
    assert x2 not in lst2

def test_get_memory_usage():
    class X(object):
        pass
    x1 = X()
    n = rgc.get_rpy_memory_usage(rgc.cast_instance_to_gcref(x1))
    assert n >= 8 and n <= 64

def test_raw_memory_owner():
    T = lltype.Struct('X', ('x', lltype.Signed))

    @rgc.owns_raw_memory('p')
    class X(object):
        p = lltype.nullptr(T)
        
        def __init__(self, arg):
            if arg:
                self.p = lltype.malloc(T, flavor='raw')
    
    a = X(3)
    b = X(0)
    ptr2 = b.p
    ptr = a.p
    del a, b
    gc.collect()
    assert ptr._was_freed()
    assert not ptr2

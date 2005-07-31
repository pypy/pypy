from pypy.rpython.memory.lltypesimulation import *
from pypy.rpython.lltype import GcStruct, Ptr, Signed, Char

def test_struct():
    S0 = GcStruct("s0", ('a', Signed), ('b', Signed), ('c', Char))
    s0 = malloc(S0)
    print s0
    assert s0.a == 0
    assert s0.b == 0
    assert s0.c == '\x00'
    s0.a = 42
    s0.b = 43
    s0.c = 'x'
    assert s0.a == 42
    assert s0.b == 43
    assert s0.c == 'x'
    s0.a = 1
    s0.b = s0.a
    assert s0.a == 1
    assert s0.b == 1

def DONOTtest_array():
    Ar = lltype.GcArray(('v', Signed))
    x = malloc(Ar,0)
    print x
    assert len(x) == 0
    x = malloc(Ar,3)
    print x
    assert typeOf(x) == Ptr(Ar)
    assert typeOf(x[0].v) == Signed
    assert x[0].v == 0
    x[0].v = 1
    x[1].v = 2
    x[2].v = 3
    assert [x[z].v for z in range(3)] == [1, 2, 3]

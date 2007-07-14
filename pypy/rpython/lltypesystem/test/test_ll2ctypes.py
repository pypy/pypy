import ctypes
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.ll2ctypes import lltype2ctypes


def test_primitive():
    assert lltype2ctypes(5) == 5
    assert lltype2ctypes('?') == '?'

def test_simple_struct():
    S = lltype.Struct('S', ('x', lltype.Signed), ('y', lltype.Signed))
    s = lltype.malloc(S, flavor='raw')
    s.x = 123
    sc = lltype2ctypes(s)
    assert isinstance(sc.contents, ctypes.Structure)
    assert sc.contents.x == 123
    sc.contents.x = 456
    assert s.x == 456
    s.x = 789
    assert sc.contents.x == 789
    s.y = 52
    assert sc.contents.y == 52
    lltype.free(s, flavor='raw')

def test_simple_array():
    A = lltype.Array(lltype.Signed)
    a = lltype.malloc(A, 10, flavor='raw')
    a[0] = 100
    a[1] = 101
    a[2] = 102
    ac = lltype2ctypes(a)
    assert isinstance(ac.contents, ctypes.Structure)
    assert ac.contents.length == 10
    assert ac.contents.items[1] == 101
    ac.contents.items[2] = 456
    assert a[2] == 456
    a[3] = 789
    assert ac.contents.items[3] == 789
    lltype.free(a, flavor='raw')

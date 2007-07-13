import ctypes
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.lltype2ctypes import lltype2ctypes


def test_primitive():
    assert lltype2ctypes(5) == 5
    assert lltype2ctypes('?') == '?'

def test_simple_struct():
    S = lltype.Struct('S', ('x', lltype.Signed))
    s = lltype.malloc(S, flavor='raw')
    s.x = 123
    sc = lltype2ctypes(s)
    assert isinstance(sc.contents, ctypes.Structure)
    assert sc.contents.x == 123
    sc.contents.x = 456
    assert s.x == 456
    s.x = 789
    assert sc.contents.x == 789
    lltype.free(s, flavor='raw')

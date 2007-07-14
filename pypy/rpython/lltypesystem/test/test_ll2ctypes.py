import py
import ctypes
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.lltypesystem.ll2ctypes import lltype2ctypes, ctypes2lltype


def test_primitive():
    assert lltype2ctypes(5) == 5
    assert lltype2ctypes('?') == ord('?')
    assert lltype2ctypes('\xE0') == 0xE0
    assert ctypes2lltype(lltype.Signed, 5) == 5
    assert ctypes2lltype(lltype.Char, ord('a')) == 'a'
    assert ctypes2lltype(lltype.Char, 0xFF) == '\xFF'

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
    ac = lltype2ctypes(a, normalize=False)
    assert isinstance(ac.contents, ctypes.Structure)
    assert ac.contents.length == 10
    assert ac.contents.items[1] == 101
    ac.contents.items[2] = 456
    assert a[2] == 456
    a[3] = 789
    assert ac.contents.items[3] == 789
    lltype.free(a, flavor='raw')

def test_array_nolength():
    A = lltype.Array(lltype.Signed, hints={'nolength': True})
    a = lltype.malloc(A, 10, flavor='raw')
    a[0] = 100
    a[1] = 101
    a[2] = 102
    ac = lltype2ctypes(a, normalize=False)
    assert isinstance(ac.contents, ctypes.Structure)
    assert ac.contents.items[1] == 101
    ac.contents.items[2] = 456
    assert a[2] == 456
    a[3] = 789
    assert ac.contents.items[3] == 789
    assert ctypes.sizeof(ac.contents) == 10 * ctypes.sizeof(ctypes.c_long)
    lltype.free(a, flavor='raw')

def test_charp():
    s = rffi.str2charp("hello")
    sc = lltype2ctypes(s, normalize=False)
    assert sc.contents.items[0] == ord('h')
    assert sc.contents.items[1] == ord('e')
    assert sc.contents.items[2] == ord('l')
    assert sc.contents.items[3] == ord('l')
    assert sc.contents.items[4] == ord('o')
    assert sc.contents.items[5] == 0
    assert not hasattr(sc.contents, 'length')
    sc.contents.items[1] = ord('E')
    assert s[1] == 'E'
    s[0] = 'H'
    assert sc.contents.items[0] == ord('H')

def test_strlen():
    strlen = rffi.llexternal('strlen', [rffi.CCHARP], lltype.Signed,
                             includes=['string.h'])
    s = rffi.str2charp("xxx")
    res = strlen(s)
    rffi.free_charp(s)
    assert res == 3

def test_func_not_in_clib():
    foobar = rffi.llexternal('I_really_dont_exist', [], lltype.Signed)
    py.test.raises(NotImplementedError, foobar)

    foobar = rffi.llexternal('I_really_dont_exist', [], lltype.Signed,
                             libraries=['m'])    # math library
    py.test.raises(NotImplementedError, foobar)

    foobar = rffi.llexternal('I_really_dont_exist', [], lltype.Signed,
                             libraries=['m', 'z'])  # math and zlib libraries
    py.test.raises(NotImplementedError, foobar)

    foobar = rffi.llexternal('I_really_dont_exist', [], lltype.Signed,
                             libraries=['I_really_dont_exist_either'])
    py.test.raises(NotImplementedError, foobar)

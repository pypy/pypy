import py
import sys
import ctypes
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.lltypesystem.ll2ctypes import lltype2ctypes, ctypes2lltype
from pypy.rlib.rarithmetic import r_uint


def test_primitive():
    assert lltype2ctypes(5) == 5
    assert lltype2ctypes('?') == ord('?')
    assert lltype2ctypes('\xE0') == 0xE0
    assert ctypes2lltype(lltype.Signed, 5) == 5
    assert ctypes2lltype(lltype.Char, ord('a')) == 'a'
    assert ctypes2lltype(lltype.Char, 0xFF) == '\xFF'
    assert lltype2ctypes(5.25) == 5.25
    assert ctypes2lltype(lltype.Float, 5.25) == 5.25
    assert lltype2ctypes(r_uint(-1)) == sys.maxint * 2 + 1
    res = ctypes2lltype(lltype.Unsigned, sys.maxint * 2 + 1)
    assert (res, type(res)) == (r_uint(-1), r_uint)

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
    s = rffi.str2charp("")
    res = strlen(s)
    rffi.free_charp(s)
    assert res == 0

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

def test_cstruct_to_ll():
    S = lltype.Struct('S', ('x', lltype.Signed), ('y', lltype.Signed))
    s = lltype.malloc(S, flavor='raw')
    s2 = lltype.malloc(S, flavor='raw')
    s.x = 123
    sc = lltype2ctypes(s)
    t = ctypes2lltype(lltype.Ptr(S), sc)
    assert lltype.typeOf(t) == lltype.Ptr(S)
    assert s == t
    assert not (s != t)
    assert t == s
    assert not (t != s)
    assert t != lltype.nullptr(S)
    assert not (t == lltype.nullptr(S))
    assert lltype.nullptr(S) != t
    assert not (lltype.nullptr(S) == t)
    assert t != s2
    assert not (t == s2)
    assert s2 != t
    assert not (s2 == t)
    assert t.x == 123
    t.x += 1
    assert s.x == 124
    s.x += 1
    assert t.x == 125
    lltype.free(s, flavor='raw')
    lltype.free(s2, flavor='raw')

def test_carray_to_ll():
    A = lltype.Array(lltype.Signed, hints={'nolength': True})
    a = lltype.malloc(A, 10, flavor='raw')
    a2 = lltype.malloc(A, 10, flavor='raw')
    a[0] = 100
    a[1] = 101
    a[2] = 110
    ac = lltype2ctypes(a)
    b = ctypes2lltype(lltype.Ptr(A), ac)
    assert lltype.typeOf(b) == lltype.Ptr(A)
    assert b == a
    assert not (b != a)
    assert a == b
    assert not (a != b)
    assert b != lltype.nullptr(A)
    assert not (b == lltype.nullptr(A))
    assert lltype.nullptr(A) != b
    assert not (lltype.nullptr(A) == b)
    assert b != a2
    assert not (b == a2)
    assert a2 != b
    assert not (a2 == b)
    assert b[2] == 110
    b[2] *= 2
    assert a[2] == 220
    a[2] *= 3
    assert b[2] == 660
    lltype.free(a, flavor='raw')
    lltype.free(a2, flavor='raw')

def test_strchr():
    # XXX int vs long issues
    strchr = rffi.llexternal('strchr', [rffi.CCHARP, lltype.Signed],
                             rffi.CCHARP,
                             includes=['string.h'])
    s = rffi.str2charp("hello world")
    res = strchr(s, ord('r'))
    assert res[0] == 'r'
    assert res[1] == 'l'
    assert res[2] == 'd'
    assert res[3] == '\x00'
    rffi.free_charp(s)

def test_frexp():
    A = lltype.FixedSizeArray(lltype.Signed, 1)
    frexp = rffi.llexternal('frexp', [lltype.Float, lltype.Ptr(A)],
                            lltype.Float,   # lltype.Float == C "double" :-/
                            includes=['math.h'],
                            libraries=['m'])
    p = lltype.malloc(A, flavor='raw')
    res = frexp(2.5, p)
    assert res == 0.625
    assert p[0] == 2
    lltype.free(p, flavor='raw')

def test_rand():
    rand = rffi.llexternal('rand', [], lltype.Signed,
                           includes=['stdlib.h'])
    srand = rffi.llexternal('srand', [lltype.Unsigned], lltype.Void,
                            includes=['stdlib.h'])
    srand(r_uint(123))
    res1 = rand()
    res2 = rand()
    res3 = rand()
    srand(r_uint(123))
    res1b = rand()
    res2b = rand()
    res3b = rand()
    assert res1 == res1b
    assert res2 == res2b
    assert res3 == res3b

# def test_qsort():...
# def test_signal():...

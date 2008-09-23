import py
import sys, struct
import ctypes
from pypy.rpython.lltypesystem import lltype, rffi, llmemory
from pypy.rpython.tool import rffi_platform
from pypy.rpython.lltypesystem.ll2ctypes import lltype2ctypes, ctypes2lltype
from pypy.rpython.lltypesystem.ll2ctypes import standard_c_lib
from pypy.rpython.lltypesystem.ll2ctypes import uninitialized2ctypes
from pypy.rpython.lltypesystem.ll2ctypes import ALLOCATED, force_cast
from pypy.rpython.annlowlevel import llhelper
from pypy.rlib import rposix
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.tool.udir import udir
from pypy.rpython.test.test_llinterp import interpret

class TestLL2Ctypes(object):

    def setup_method(self, meth):
        ALLOCATED.clear()

    def test_primitive(self):
        assert lltype2ctypes(5) == 5
        assert lltype2ctypes('?') == ord('?')
        assert lltype2ctypes('\xE0') == 0xE0
        assert lltype2ctypes(unichr(1234)) == 1234
        assert ctypes2lltype(lltype.Signed, 5) == 5
        assert ctypes2lltype(lltype.Char, ord('a')) == 'a'
        assert ctypes2lltype(lltype.UniChar, ord(u'x')) == u'x'
        assert ctypes2lltype(lltype.Char, 0xFF) == '\xFF'
        assert lltype2ctypes(5.25) == 5.25
        assert ctypes2lltype(lltype.Float, 5.25) == 5.25
        assert lltype2ctypes(u'x') == ord(u'x')
        res = lltype2ctypes(rffi.r_singlefloat(-3.5))
        assert isinstance(res, ctypes.c_float)
        assert res.value == -3.5
        res = ctypes2lltype(lltype.SingleFloat, ctypes.c_float(-3.5))
        assert isinstance(res, rffi.r_singlefloat)
        assert float(res) == -3.5
        assert lltype2ctypes(rffi.r_ulong(-1)) == sys.maxint * 2 + 1
        res = ctypes2lltype(lltype.Unsigned, sys.maxint * 2 + 1)
        assert (res, type(res)) == (rffi.r_ulong(-1), rffi.r_ulong)

        res = lltype2ctypes(llmemory.sizeof(lltype.Signed))
        assert res == struct.calcsize("l")
        S = lltype.Struct('S', ('x', lltype.Signed), ('y', lltype.Signed))
        res = lltype2ctypes(llmemory.sizeof(S))
        assert res == struct.calcsize("ll")

        p = lltype.nullptr(S)
        cptr = lltype2ctypes(p)
        assert not cptr
        py.test.raises(ValueError, 'cptr.contents')   # NULL pointer access
        res = ctypes2lltype(lltype.Ptr(S), cptr)
        assert res == p
        assert not ALLOCATED     # detects memory leaks in the test

    def test_simple_struct(self):
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
        assert not ALLOCATED     # detects memory leaks in the test

    def test_struct_ptrs(self):
        S2 = lltype.Struct('S2', ('y', lltype.Signed))
        S1 = lltype.Struct('S', ('x', lltype.Signed), ('p', lltype.Ptr(S2)))
        s1 = lltype.malloc(S1, flavor='raw')
        s2a = lltype.malloc(S2, flavor='raw')
        s2b = lltype.malloc(S2, flavor='raw')
        s2a.y = ord('a')
        s2b.y = ord('b')
        sc1 = lltype2ctypes(s1)
        sc1.contents.x = 50
        assert s1.x == 50
        sc1.contents.p = lltype2ctypes(s2a)
        assert s1.p == s2a
        s1.p.y -= 32
        assert sc1.contents.p.contents.y == ord('A')
        s1.p = s2b
        sc1.contents.p.contents.y -= 32
        assert s2b.y == ord('B')
        lltype.free(s1, flavor='raw')
        lltype.free(s2a, flavor='raw')
        lltype.free(s2b, flavor='raw')
        assert not ALLOCATED     # detects memory leaks in the test

    def test_simple_array(self):
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
        assert not ALLOCATED     # detects memory leaks in the test

    def test_array_inside_struct(self):
        # like rstr.STR, but not Gc
        STR = lltype.Struct('STR', ('x', lltype.Signed), ('y', lltype.Array(lltype.Char)))
        a = lltype.malloc(STR, 3, flavor='raw')
        a.y[0] = 'x'
        a.y[1] = 'y'
        a.y[2] = 'z'
        ac = lltype2ctypes(a)
        assert ac.contents.y.length == 3
        assert ac.contents.y.items[2] == ord('z')
        lltype.free(a, flavor='raw')
        assert not ALLOCATED

    def test_array_nolength(self):
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
        assert not ALLOCATED     # detects memory leaks in the test

    def test_charp(self):
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
        rffi.free_charp(s)
        assert not ALLOCATED     # detects memory leaks in the test

    def test_unicharp(self):
        SP = rffi.CArrayPtr(lltype.UniChar)
        s = lltype.malloc(SP.TO, 4, flavor='raw')
        s[0] = u'x'
        s[1] = u'y'
        s[2] = u'z'
        s[3] = u'\x00'
        sc = lltype2ctypes(s, normalize=False)
        assert sc.contents.items[0] == ord(u'x')
        assert sc.contents.items[1] == ord(u'y')
        assert sc.contents.items[2] == ord(u'z')
        assert not hasattr(sc.contents, 'length')
        lltype.free(s, flavor='raw')
        assert not ALLOCATED
        
    def test_strlen(self):
        eci = ExternalCompilationInfo(includes=['string.h'])
        strlen = rffi.llexternal('strlen', [rffi.CCHARP], rffi.SIZE_T,
                                 compilation_info=eci)
        s = rffi.str2charp("xxx")
        res = strlen(s)
        rffi.free_charp(s)
        assert res == 3     # actually r_size_t(3)
        s = rffi.str2charp("")
        res = strlen(s)
        rffi.free_charp(s)
        assert res == 0     # actually r_size_t(0)
        assert not ALLOCATED     # detects memory leaks in the test

    def test_func_not_in_clib(self):
        eci = ExternalCompilationInfo(libraries=['m'])
        foobar = rffi.llexternal('I_really_dont_exist', [], lltype.Signed)
        py.test.raises(NotImplementedError, foobar)

        foobar = rffi.llexternal('I_really_dont_exist', [], lltype.Signed,
                                 compilation_info=eci)    # math library
        py.test.raises(NotImplementedError, foobar)

        eci = ExternalCompilationInfo(libraries=['m', 'z'])
        foobar = rffi.llexternal('I_really_dont_exist', [], lltype.Signed,
                                 compilation_info=eci)  # math and zlib
        py.test.raises(NotImplementedError, foobar)

        eci = ExternalCompilationInfo(libraries=['I_really_dont_exist_either'])
        foobar = rffi.llexternal('I_really_dont_exist', [], lltype.Signed,
                                 compilation_info=eci)
        py.test.raises(NotImplementedError, foobar)
        assert not ALLOCATED     # detects memory leaks in the test

    def test_cstruct_to_ll(self):
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
        assert not ALLOCATED     # detects memory leaks in the test

    def test_carray_to_ll(self):
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
        assert not ALLOCATED     # detects memory leaks in the test

    def test_strchr(self):
        eci = ExternalCompilationInfo(includes=['string.h'])
        strchr = rffi.llexternal('strchr', [rffi.CCHARP, rffi.INT],
                                 rffi.CCHARP, compilation_info=eci)
        s = rffi.str2charp("hello world")
        res = strchr(s, ord('r'))
        assert res[0] == 'r'
        assert res[1] == 'l'
        assert res[2] == 'd'
        assert res[3] == '\x00'
        # XXX maybe we should also allow res[-1], res[-2]...
        rffi.free_charp(s)
        assert not ALLOCATED     # detects memory leaks in the test

    def test_frexp(self):
        if sys.platform != 'win32':
            eci = ExternalCompilationInfo(includes=['math.h'],
                                          libraries=['m'])
        else:
            eci = ExternalCompilationInfo(includes=['math.h'])
        A = lltype.FixedSizeArray(rffi.INT, 1)
        frexp = rffi.llexternal('frexp', [rffi.DOUBLE, lltype.Ptr(A)],
                                rffi.DOUBLE, compilation_info=eci)
        p = lltype.malloc(A, flavor='raw')
        res = frexp(2.5, p)
        assert res == 0.625
        assert p[0] == 2
        lltype.free(p, flavor='raw')
        assert not ALLOCATED     # detects memory leaks in the test

    def test_rand(self):
        eci = ExternalCompilationInfo(includes=['stdlib.h'])
        rand = rffi.llexternal('rand', [], rffi.INT,
                               compilation_info=eci)
        srand = rffi.llexternal('srand', [rffi.UINT], lltype.Void,
                                compilation_info=eci)
        srand(rffi.r_uint(123))
        res1 = rand()
        res2 = rand()
        res3 = rand()
        srand(rffi.r_uint(123))
        res1b = rand()
        res2b = rand()
        res3b = rand()
        assert res1 == res1b
        assert res2 == res2b
        assert res3 == res3b
        assert not ALLOCATED     # detects memory leaks in the test

    def test_opaque_obj(self):
        if sys.platform == 'win32':
            py.test.skip("No gettimeofday on win32")
        eci = ExternalCompilationInfo(
            includes = ['sys/time.h', 'time.h']
        )
        TIMEVALP = rffi.COpaquePtr('struct timeval', compilation_info=eci)
        TIMEZONEP = rffi.COpaquePtr('struct timezone', compilation_info=eci)
        gettimeofday = rffi.llexternal('gettimeofday', [TIMEVALP, TIMEZONEP],
                                       rffi.INT, compilation_info=eci)
        ll_timevalp = lltype.malloc(TIMEVALP.TO, flavor='raw')
        ll_timezonep = lltype.malloc(TIMEZONEP.TO, flavor='raw')
        res = gettimeofday(ll_timevalp, ll_timezonep)
        assert res != -1
        lltype.free(ll_timezonep, flavor='raw')
        lltype.free(ll_timevalp, flavor='raw')
        assert not ALLOCATED     # detects memory leaks in the test

    def test_simple_cast(self):
        assert rffi.cast(rffi.SIGNEDCHAR, 0x123456) == 0x56
        assert rffi.cast(rffi.SIGNEDCHAR, 0x123481) == -127
        assert rffi.cast(rffi.CHAR, 0x123456) == '\x56'
        assert rffi.cast(rffi.CHAR, 0x123481) == '\x81'
        assert rffi.cast(rffi.UCHAR, 0x123481) == 0x81
        assert not ALLOCATED     # detects memory leaks in the test

    def test_forced_ptr_cast(self):
        import array
        A = lltype.Array(lltype.Signed, hints={'nolength': True})
        B = lltype.Array(lltype.Char, hints={'nolength': True})
        a = lltype.malloc(A, 10, flavor='raw')
        for i in range(10):
            a[i] = i*i

        b = rffi.cast(lltype.Ptr(B), a)

        checker = array.array('l')
        for i in range(10):
            checker.append(i*i)
        expected = checker.tostring()

        for i in range(len(expected)):
            assert b[i] == expected[i]

        c = rffi.cast(rffi.VOIDP, a)
        addr = lltype2ctypes(c)
        #assert addr == ctypes.addressof(a._obj._ctypes_storage)
        d = ctypes2lltype(rffi.VOIDP, addr)
        assert lltype.typeOf(d) == rffi.VOIDP
        assert c == d
        e = rffi.cast(lltype.Ptr(A), d)
        for i in range(10):
            assert e[i] == i*i

        c = lltype.nullptr(rffi.VOIDP.TO)
        addr = rffi.cast(lltype.Signed, c)
        assert addr == 0

        lltype.free(a, flavor='raw')
        assert not ALLOCATED     # detects memory leaks in the test

    def test_adr_cast(self):
        from pypy.rpython.annlowlevel import llstr
        from pypy.rpython.lltypesystem.rstr import STR
        P = lltype.Ptr(lltype.FixedSizeArray(lltype.Char, 1))
        def f():
            a = llstr("xyz")
            b = (llmemory.cast_ptr_to_adr(a) + llmemory.offsetof(STR, 'chars')
                 + llmemory.itemoffsetof(STR.chars, 0))
            buf = rffi.cast(rffi.VOIDP, b)
            return buf[2]
        assert f() == 'z'
        res = interpret(f, [])
        assert res == 'z'
    
    def test_funcptr1(self):
        def dummy(n):
            return n+1

        FUNCTYPE = lltype.FuncType([lltype.Signed], lltype.Signed)
        cdummy = lltype2ctypes(llhelper(lltype.Ptr(FUNCTYPE), dummy))
        assert isinstance(cdummy,
                          ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_long))
        res = cdummy(41)
        assert res == 42
        lldummy = ctypes2lltype(lltype.Ptr(FUNCTYPE), cdummy)
        assert lltype.typeOf(lldummy) == lltype.Ptr(FUNCTYPE)
        res = lldummy(41)
        assert res == 42
        assert not ALLOCATED     # detects memory leaks in the test

    def test_funcptr2(self):
        FUNCTYPE = lltype.FuncType([rffi.CCHARP], lltype.Signed)
        cstrlen = standard_c_lib.strlen
        llstrlen = ctypes2lltype(lltype.Ptr(FUNCTYPE), cstrlen)
        assert lltype.typeOf(llstrlen) == lltype.Ptr(FUNCTYPE)
        p = rffi.str2charp("hi there")
        res = llstrlen(p)
        assert res == 8
        cstrlen2 = lltype2ctypes(llstrlen)
        cp = lltype2ctypes(p)
        assert cstrlen2.restype == ctypes.c_long
        res = cstrlen2(cp)
        assert res == 8
        rffi.free_charp(p)
        assert not ALLOCATED     # detects memory leaks in the test

    def test_qsort(self):
        CMPFUNC = lltype.FuncType([rffi.VOIDP, rffi.VOIDP], rffi.INT)
        qsort = rffi.llexternal('qsort', [rffi.VOIDP,
                                          rffi.SIZE_T,
                                          rffi.SIZE_T,
                                          lltype.Ptr(CMPFUNC)],
                                lltype.Void)

        lst = [23, 43, 24, 324, 242, 34, 78, 5, 3, 10]
        A = lltype.Array(lltype.Signed, hints={'nolength': True})
        a = lltype.malloc(A, 10, flavor='raw')
        for i in range(10):
            a[i] = lst[i]

        SIGNEDPTR = lltype.Ptr(lltype.FixedSizeArray(lltype.Signed, 1))

        def my_compar(p1, p2):
            p1 = rffi.cast(SIGNEDPTR, p1)
            p2 = rffi.cast(SIGNEDPTR, p2)
            print 'my_compar:', p1[0], p2[0]
            return rffi.cast(rffi.INT, cmp(p1[0], p2[0]))

        qsort(rffi.cast(rffi.VOIDP, a),
              rffi.cast(rffi.SIZE_T, 10),
              rffi.cast(rffi.SIZE_T, llmemory.sizeof(lltype.Signed)),
              llhelper(lltype.Ptr(CMPFUNC), my_compar))

        for i in range(10):
            print a[i],
        print
        lst.sort()
        for i in range(10):
            assert a[i] == lst[i]
        lltype.free(a, flavor='raw')
        assert not ALLOCATED     # detects memory leaks in the test

    # def test_signal(self):...

    def test_uninitialized2ctypes(self):
        # for now, uninitialized fields are filled with 0xDD in the ctypes data
        def checkobj(o, size):
            p = ctypes.cast(ctypes.c_void_p(ctypes.addressof(o)),
                            ctypes.POINTER(ctypes.c_ubyte*size))
            for i in range(size):
                assert p.contents[i] == 0xDD

        def checkval(v, fmt):
            res = struct.pack(fmt, v)
            assert res == "\xDD" * len(res)

        checkval(uninitialized2ctypes(rffi.CHAR), 'B')
        checkval(uninitialized2ctypes(rffi.SHORT), 'h')
        checkval(uninitialized2ctypes(rffi.INT), 'i')
        checkval(uninitialized2ctypes(rffi.UINT), 'I')
        checkval(uninitialized2ctypes(rffi.LONGLONG), 'q')
        checkval(uninitialized2ctypes(rffi.DOUBLE), 'd')
        checkobj(uninitialized2ctypes(rffi.INTP),
                 ctypes.sizeof(ctypes.c_void_p))
        checkobj(uninitialized2ctypes(rffi.CCHARP),
                 ctypes.sizeof(ctypes.c_void_p))

        S = lltype.Struct('S', ('x', lltype.Signed), ('y', lltype.Signed))
        s = lltype.malloc(S, flavor='raw')
        sc = lltype2ctypes(s)
        checkval(sc.contents.x, 'l')
        checkval(sc.contents.y, 'l')
        lltype.free(s, flavor='raw')
        assert not ALLOCATED     # detects memory leaks in the test

    def test_substructures(self):
        S1  = lltype.Struct('S1', ('x', lltype.Signed))
        BIG = lltype.Struct('BIG', ('s1a', S1), ('s1b', S1))
        s = lltype.malloc(BIG, flavor='raw')
        s.s1a.x = 123
        s.s1b.x = 456
        sc = lltype2ctypes(s)
        assert sc.contents.s1a.x == 123
        assert sc.contents.s1b.x == 456
        sc.contents.s1a.x += 1
        sc.contents.s1b.x += 10
        assert s.s1a.x == 124
        assert s.s1b.x == 466
        s.s1a.x += 3
        s.s1b.x += 30
        assert sc.contents.s1a.x == 127
        assert sc.contents.s1b.x == 496
        lltype.free(s, flavor='raw')

        s = lltype.malloc(BIG, flavor='raw')
        s1ac = lltype2ctypes(s.s1a)
        s1ac.contents.x = 53
        sc = lltype2ctypes(s)
        assert sc.contents.s1a.x == 53
        sc.contents.s1a.x += 1
        assert s1ac.contents.x == 54
        assert s.s1a.x == 54
        s.s1a.x += 2
        assert s1ac.contents.x == 56
        assert sc.contents.s1a.x == 56
        sc.contents.s1a.x += 3
        assert s1ac.contents.x == 59
        assert s.s1a.x == 59

        t = ctypes2lltype(lltype.Ptr(BIG), sc)
        assert t == s
        assert t.s1a == s.s1a
        assert t.s1a.x == 59
        s.s1b.x = 8888
        assert t.s1b == s.s1b
        assert t.s1b.x == 8888
        t1 = ctypes2lltype(lltype.Ptr(S1), s1ac)
        assert t.s1a == t1
        assert t1.x == 59
        t1.x += 1
        assert sc.contents.s1a.x == 60
        lltype.free(s, flavor='raw')
        assert not ALLOCATED     # detects memory leaks in the test

    def test_recursive_struct(self):
        SX = lltype.ForwardReference()
        S1 = lltype.Struct('S1', ('p', lltype.Ptr(SX)), ('x', lltype.Signed))
        SX.become(S1)
        # a chained list
        s1 = lltype.malloc(S1, flavor='raw')
        s2 = lltype.malloc(S1, flavor='raw')
        s3 = lltype.malloc(S1, flavor='raw')
        s1.x = 111
        s2.x = 222
        s3.x = 333
        s1.p = s2
        s2.p = s3
        s3.p = lltype.nullptr(S1)
        sc1 = lltype2ctypes(s1)
        sc2 = sc1.contents.p
        sc3 = sc2.contents.p
        assert not sc3.contents.p
        assert sc1.contents.x == 111
        assert sc2.contents.x == 222
        assert sc3.contents.x == 333
        sc3.contents.x += 1
        assert s3.x == 334
        s3.x += 2
        assert sc3.contents.x == 336
        lltype.free(s1, flavor='raw')
        lltype.free(s2, flavor='raw')
        lltype.free(s3, flavor='raw')
        # a self-cycle
        s1 = lltype.malloc(S1, flavor='raw')
        s1.x = 12
        s1.p = s1
        sc1 = lltype2ctypes(s1)
        assert sc1.contents.x == 12
        assert (ctypes.addressof(sc1.contents.p.contents) ==
                ctypes.addressof(sc1.contents))
        s1.x *= 5
        assert sc1.contents.p.contents.p.contents.p.contents.x == 60
        lltype.free(s1, flavor='raw')
        # a longer cycle
        s1 = lltype.malloc(S1, flavor='raw')
        s2 = lltype.malloc(S1, flavor='raw')
        s1.x = 111
        s1.p = s2
        s2.x = 222
        s2.p = s1
        sc1 = lltype2ctypes(s1)
        assert sc1.contents.x == 111
        assert sc1.contents.p.contents.x == 222
        assert (ctypes.addressof(sc1.contents.p.contents) !=
                ctypes.addressof(sc1.contents))
        assert (ctypes.addressof(sc1.contents.p.contents.p.contents) ==
                ctypes.addressof(sc1.contents))
        lltype.free(s1, flavor='raw')
        lltype.free(s2, flavor='raw')
        assert not ALLOCATED     # detects memory leaks in the test

    def test_indirect_recursive_struct(self):
        S2Forward = lltype.ForwardReference()
        S1 = lltype.Struct('S1', ('p', lltype.Ptr(S2Forward)))
        A2 = lltype.Array(lltype.Ptr(S1), hints={'nolength': True})
        S2 = lltype.Struct('S2', ('a', lltype.Ptr(A2)))
        S2Forward.become(S2)
        s1 = lltype.malloc(S1, flavor='raw')
        a2 = lltype.malloc(A2, 10, flavor='raw')
        s2 = lltype.malloc(S2, flavor='raw')
        s2.a = a2
        a2[5] = s1
        s1.p = s2
        ac2 = lltype2ctypes(a2, normalize=False)
        sc1 = ac2.contents.items[5]
        sc2 = sc1.contents.p
        assert (ctypes.addressof(sc2.contents.a.contents) ==
                ctypes.addressof(ac2.contents))
        lltype.free(s1, flavor='raw')
        lltype.free(a2, flavor='raw')
        lltype.free(s2, flavor='raw')
        assert not ALLOCATED     # detects memory leaks in the test

    def test_arrayofstruct(self):
        S1 = lltype.Struct('S1', ('x', lltype.Signed))
        A = lltype.Array(S1, hints={'nolength': True})
        a = lltype.malloc(A, 5, flavor='raw')
        a[0].x = 100
        a[1].x = 101
        a[2].x = 102
        a[3].x = 103
        a[4].x = 104
        ac = lltype2ctypes(a, normalize=False)
        assert ac.contents.items[0].x == 100
        assert ac.contents.items[2].x == 102
        ac.contents.items[3].x += 500
        assert a[3].x == 603
        a[4].x += 600
        assert ac.contents.items[4].x == 704
        a1 = ctypes2lltype(lltype.Ptr(A), ac)
        assert a1 == a
        assert a1[2].x == 102
        aitem1 = ctypes2lltype(lltype.Ptr(S1),
                               ctypes.pointer(ac.contents.items[1]))
        assert aitem1.x == 101
        assert aitem1 == a1[1]
        lltype.free(a, flavor='raw')
        assert not ALLOCATED     # detects memory leaks in the test

    def test_get_errno(self):
        eci = ExternalCompilationInfo(includes=['string.h'])
        if sys.platform.startswith('win'):
            underscore_on_windows = '_'
        else:
            underscore_on_windows = ''
        strlen = rffi.llexternal('strlen', [rffi.CCHARP], rffi.SIZE_T,
                                 compilation_info=eci)
        os_write = rffi.llexternal(underscore_on_windows+'write',
                                   [rffi.INT, rffi.CCHARP, rffi.SIZE_T],
                                   rffi.SIZE_T)
        buffer = lltype.malloc(rffi.CCHARP.TO, 5, flavor='raw')
        written = os_write(12312312, buffer, 5)
        lltype.free(buffer, flavor='raw')
        assert rffi.cast(lltype.Signed, written) < 0
        # the next line is a random external function call,
        # to check that it doesn't reset errno
        strlen("hi!")
        err = rposix.get_errno()
        import errno
        assert err == errno.EBADF
        assert not ALLOCATED     # detects memory leaks in the test

    def test_call_with_struct_argument(self):
        # XXX is there such a function in the standard C headers?
        from pypy.rlib import _rsocket_rffi
        buf = rffi.make(_rsocket_rffi.in_addr)
        rffi.cast(rffi.CCHARP, buf)[0] = '\x01'
        rffi.cast(rffi.CCHARP, buf)[1] = '\x02'
        rffi.cast(rffi.CCHARP, buf)[2] = '\x03'
        rffi.cast(rffi.CCHARP, buf)[3] = '\x04'
        p = _rsocket_rffi.inet_ntoa(buf)
        assert rffi.charp2str(p) == '1.2.3.4'
        lltype.free(buf, flavor='raw')
        assert not ALLOCATED     # detects memory leaks in the test

    def test_storage_stays_around(self):
        data = "hello, world!" * 100
        A = lltype.Array(rffi.CHAR, hints={'nolength': True})
        S = lltype.Struct('S', ('a', lltype.Ptr(A)))
        s = lltype.malloc(S, flavor='raw')
        lltype2ctypes(s)     # force it to escape
        s.a = lltype.malloc(A, len(data), flavor='raw')
        # the storage for the array should not be freed by lltype even
        # though the _ptr object appears to go away here
        for i in xrange(len(data)):
            s.a[i] = data[i]
        for i in xrange(len(data)):
            assert s.a[i] == data[i]
        lltype.free(s.a, flavor='raw')
        lltype.free(s, flavor='raw')
        assert not ALLOCATED     # detects memory leaks in the test

    def test_arrayoffloat(self):
        a = lltype.malloc(rffi.FLOATP.TO, 3, flavor='raw')
        a[0] = rffi.r_singlefloat(0.0)
        a[1] = rffi.r_singlefloat(1.1)
        a[2] = rffi.r_singlefloat(2.2)
        ac = lltype2ctypes(a, normalize=False)
        assert ac.contents.items[0] == 0.0
        assert abs(ac.contents.items[1] - 1.1) < 1E-6
        assert abs(ac.contents.items[2] - 2.2) < 1E-6
        b = ctypes2lltype(rffi.FLOATP, ac)
        assert isinstance(b[0], rffi.r_singlefloat)
        assert float(b[0]) == 0.0
        assert isinstance(b[1], rffi.r_singlefloat)
        assert abs(float(b[1]) - 1.1) < 1E-6
        assert isinstance(b[2], rffi.r_singlefloat)
        assert abs(float(b[2]) - 2.2) < 1E-6

    def test_different_signatures(self):
        if sys.platform=='win32':
            py.test.skip("No fcntl on win32")
        fcntl_int = rffi.llexternal('fcntl', [rffi.INT, rffi.INT, rffi.INT],
                                    rffi.INT)
        fcntl_str = rffi.llexternal('fcntl', [rffi.INT, rffi.INT, rffi.CCHARP],
                                    rffi.INT)
        fcntl_int(12345, 1, 0)
        fcntl_str(12345, 3, "xxx")
        fcntl_int(12345, 1, 0)

    def test_llexternal_source(self):
        eci = ExternalCompilationInfo(
            separate_module_sources = ["int fn() { return 42; }"],
            export_symbols = ['fn'],
        )
        fn = rffi.llexternal('fn', [], rffi.INT, compilation_info=eci)
        res = fn()
        assert res == 42

    def test_prebuilt_constant(self):
        header = py.code.Source("""
        #ifndef _SOME_H
        #define _SOME_H
        
        #include <stdlib.h>
        
        static int x = 3;
        char **z = NULL;

        #endif  /* _SOME_H */
        """)
        h_file = udir.join("some_h.h")
        h_file.write(header)
        
        eci = ExternalCompilationInfo(includes=['stdio.h', str(h_file.basename)],
                                      include_dirs=[str(udir)])
        
        get_x, set_x = rffi.CExternVariable(rffi.LONG, 'x', eci)
        get_z, set_z = rffi.CExternVariable(rffi.CCHARPP, 'z', eci)

        def f():
            one = get_x()
            set_x(13)
            return one + get_x()

        def g():
            l = rffi.liststr2charpp(["a", "b", "c"])
            try:
                set_z(l)
                return rffi.charp2str(get_z()[2])
            finally:
                rffi.free_charpp(l)

        res = f()
        assert res == 16
        assert g() == "c"

    def test_c_callback(self):
        c_source = py.code.Source("""
        int eating_callback(int arg, int(*call)(int))
        {
            return call(arg);
        }
        """)

        eci = ExternalCompilationInfo(separate_module_sources=[c_source],
                                      export_symbols=['eating_callback'])

        args = [rffi.INT, rffi.CCallback([rffi.INT], rffi.INT)]
        eating_callback = rffi.llexternal('eating_callback', args, rffi.INT,
                                          compilation_info=eci)

        def g(i):
            return i + 3

        def f():
            return eating_callback(3, g)

        assert f() == 6

    def test_qsort(self):
        TP = rffi.CArrayPtr(rffi.INT)
        a = lltype.malloc(TP.TO, 5, flavor='raw')
        a[0] = 5
        a[1] = 3
        a[2] = 2
        a[3] = 1
        a[4] = 4

        def compare(a, b):
            if a[0] > b[0]:
                return 1
            else:
                return -1

        CALLBACK = rffi.CCallback([rffi.VOIDP, rffi.VOIDP], rffi.INT)
        qsort = rffi.llexternal('qsort', [rffi.VOIDP, rffi.INT,
                                          rffi.INT, CALLBACK], lltype.Void)

        qsort(rffi.cast(rffi.VOIDP, a), 5, rffi.sizeof(rffi.INT), compare)
        for i in range(5):
            assert a[i] == i + 1

    def test_array_type_bug(self):
        A = lltype.Array(lltype.Signed)
        a1 = lltype.malloc(A, 0, flavor='raw')
        a2 = lltype.malloc(A, 0, flavor='raw')
        c1 = lltype2ctypes(a1)
        c2 = lltype2ctypes(a2)
        assert type(c1) is type(c2)

    def test_varsized_struct(self): 
        STR = lltype.Struct('rpy_string', ('hash',  lltype.Signed),
                            ('chars', lltype.Array(lltype.Char, hints={'immutable': True})))
        s = lltype.malloc(STR, 3, flavor='raw')
        one = force_cast(rffi.VOIDP, s)
        # sanity check
        #assert lltype2ctypes(one).contents.items._length_ > 0
        two = force_cast(lltype.Ptr(STR), one)
        assert s == two

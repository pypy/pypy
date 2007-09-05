import py
import sys, struct
import ctypes
from pypy.rpython.lltypesystem import lltype, rffi, llmemory
from pypy.rpython.lltypesystem.ll2ctypes import lltype2ctypes, ctypes2lltype
from pypy.rpython.lltypesystem.ll2ctypes import standard_c_lib
from pypy.rpython.lltypesystem.ll2ctypes import uninitialized2ctypes
from pypy.rpython.annlowlevel import llhelper


class TestLL2Ctypes(object):

    def test_primitive(self):
        assert lltype2ctypes(5) == 5
        assert lltype2ctypes('?') == ord('?')
        assert lltype2ctypes('\xE0') == 0xE0
        assert ctypes2lltype(lltype.Signed, 5) == 5
        assert ctypes2lltype(lltype.Char, ord('a')) == 'a'
        assert ctypes2lltype(lltype.Char, 0xFF) == '\xFF'
        assert lltype2ctypes(5.25) == 5.25
        assert ctypes2lltype(lltype.Float, 5.25) == 5.25
        assert lltype2ctypes(rffi.r_uint(-1)) == sys.maxint * 2 + 1
        res = ctypes2lltype(lltype.Unsigned, sys.maxint * 2 + 1)
        assert (res, type(res)) == (rffi.r_uint(-1), rffi.r_uint)

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

    def test_strlen(self):
        strlen = rffi.llexternal('strlen', [rffi.CCHARP], rffi.SIZE_T,
                                 includes=['string.h'])
        s = rffi.str2charp("xxx")
        res = strlen(s)
        rffi.free_charp(s)
        assert res == 3     # actually r_size_t(3)
        s = rffi.str2charp("")
        res = strlen(s)
        rffi.free_charp(s)
        assert res == 0     # actually r_size_t(0)

    def test_func_not_in_clib(self):
        foobar = rffi.llexternal('I_really_dont_exist', [], lltype.Signed)
        py.test.raises(NotImplementedError, foobar)

        foobar = rffi.llexternal('I_really_dont_exist', [], lltype.Signed,
                                 libraries=['m'])    # math library
        py.test.raises(NotImplementedError, foobar)

        foobar = rffi.llexternal('I_really_dont_exist', [], lltype.Signed,
                                 libraries=['m', 'z'])  # math and zlib
        py.test.raises(NotImplementedError, foobar)

        foobar = rffi.llexternal('I_really_dont_exist', [], lltype.Signed,
                                 libraries=['I_really_dont_exist_either'])
        py.test.raises(NotImplementedError, foobar)

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

    def test_strchr(self):
        strchr = rffi.llexternal('strchr', [rffi.CCHARP, rffi.INT],
                                 rffi.CCHARP,
                                 includes=['string.h'])
        s = rffi.str2charp("hello world")
        res = strchr(s, ord('r'))
        assert res[0] == 'r'
        assert res[1] == 'l'
        assert res[2] == 'd'
        assert res[3] == '\x00'
        # XXX maybe we should also allow res[-1], res[-2]...
        rffi.free_charp(s)

    def test_frexp(self):
        A = lltype.FixedSizeArray(rffi.INT, 1)
        frexp = rffi.llexternal('frexp', [rffi.DOUBLE, lltype.Ptr(A)],
                                rffi.DOUBLE,
                                includes=['math.h'],
                                libraries=['m'])
        p = lltype.malloc(A, flavor='raw')
        res = frexp(2.5, p)
        assert res == 0.625
        assert p[0] == 2
        lltype.free(p, flavor='raw')

    def test_rand(self):
        rand = rffi.llexternal('rand', [], rffi.INT,
                               includes=['stdlib.h'])
        srand = rffi.llexternal('srand', [rffi.UINT], lltype.Void,
                                includes=['stdlib.h'])
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

    def test_opaque_obj(self):
        includes = ['sys/time.h', 'time.h']
        TIMEVALP = rffi.COpaquePtr('struct timeval', includes=includes)
        TIMEZONEP = rffi.COpaquePtr('struct timezone', includes=includes)
        gettimeofday = rffi.llexternal('gettimeofday', [TIMEVALP, TIMEZONEP],
                                       rffi.INT, includes=includes)
        ll_timevalp = lltype.malloc(TIMEVALP.TO, flavor='raw')
        ll_timezonep = lltype.malloc(TIMEZONEP.TO, flavor='raw')
        res = gettimeofday(ll_timevalp, ll_timezonep)
        assert res != -1

    def test_simple_cast(self):
        assert rffi.cast(rffi.SIGNEDCHAR, 0x123456) == 0x56
        assert rffi.cast(rffi.SIGNEDCHAR, 0x123481) == -127
        assert rffi.cast(rffi.CHAR, 0x123456) == '\x56'
        assert rffi.cast(rffi.CHAR, 0x123481) == '\x81'
        assert rffi.cast(rffi.UCHAR, 0x123481) == 0x81

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

        lltype.free(a, flavor='raw')

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
            return cmp(p1[0], p2[0])

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
        lltype.free(s, flavor='raw')

    def test_recursive_struct(self):
        py.test.skip("Not implemented")
        SX = lltype.ForwardReference()
        S1 = lltype.Struct('S1', ('x', lltype.Ptr(SX)))
        S1.x.TO.become(S1)
        s = lltype.malloc(S1, flavor='raw')
        sc = lltype2ctypes(s)

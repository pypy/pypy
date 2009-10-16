from pypy.rpython.lltypesystem.lltype import *
from pypy.translator.c.test import test_typed


class TestLowLevelType(test_typed.CompilationTestCase):

    def test_simple(self):
        S = GcStruct("s", ('v', Signed))
        def llf():
            s = malloc(S)
            return s.v
        fn = self.getcompiled(llf)
        assert fn() == 0

    def test_simple2(self):
        S = Struct("s", ('v', Signed))
        S2 = GcStruct("s2", ('a',S), ('b',S))
        def llf():
            s = malloc(S2)
            s.a.v = 6
            s.b.v = 12
            return s.a.v + s.b.v
        fn = self.getcompiled(llf)
        assert fn() == 18

    def test_fixedsizearray(self):
        S = Struct("s", ('v', Signed))
        A7 = FixedSizeArray(Signed, 7)
        A3 = FixedSizeArray(S, 3)
        A42 = FixedSizeArray(A7, 6)
        BIG = GcStruct("big", ("a7", A7), ("a3", A3), ("a42", A42))
        def llf():
            big = malloc(BIG)
            a7 = big.a7
            a3 = big.a3
            a42 = big.a42
            a7[0] = -1
            a7.item6 = -2
            a3[0].v = -3
            a3[2].v = -4
            a42[0][0] = -5
            a42[5][6] = -6
            assert a7[0] == -1
            assert a7[6] == -2
            assert a3[0].v == -3
            assert a3.item2.v == -4
            assert a42[0][0] == -5
            assert a42[5][6] == -6
            return len(a42)*100 + len(a42[4])
        fn = self.getcompiled(llf)
        res = fn()
        assert fn() == 607

    def test_recursivearray(self):
        A = ForwardReference()
        A.become(FixedSizeArray(Struct("S", ('a', Ptr(A))), 5))
        TREE = Struct("TREE", ("root", A), ("other", A))
        tree = malloc(TREE, immortal=True)
        def llf():
            tree.root[0].a = tree.root
            tree.root[1].a = tree.other
            assert tree.root[0].a[0].a[0].a[0].a[0].a[1].a == tree.other
        fn = self.getcompiled(llf)
        fn()

    def test_prebuilt_array(self):
        A = FixedSizeArray(Signed, 5)
        a = malloc(A, immortal=True)
        a[0] = 8
        a[1] = 5
        a[2] = 12
        a[3] = 12
        a[4] = 15
        def llf():
            s = ''
            for i in range(5):
                s += chr(64+a[i])
            assert s == "HELLO"
        fn = self.getcompiled(llf)
        fn()

    def test_call_with_fixedsizearray(self):
        A = FixedSizeArray(Struct('s1', ('x', Signed)), 5)
        S = GcStruct('s', ('a', Ptr(A)))
        a = malloc(A, immortal=True)
        a[1].x = 123
        def g(x):
            return x[1].x
        def llf():
            s = malloc(S)
            s.a = a
            return g(s.a)
        fn = self.getcompiled(llf)
        res = fn()
        assert res == 123

    def test_more_prebuilt_arrays(self):
        A = FixedSizeArray(Struct('s1', ('x', Signed)), 5)
        S = Struct('s', ('a1', Ptr(A)), ('a2', A))
        s = malloc(S, zero=True, immortal=True)
        s.a1 = malloc(A, immortal=True)
        s.a1[2].x = 50
        s.a2[2].x = 60
        def llf(n):
            if n == 1:
                a = s.a1
            else:
                a = s.a2
            return a[2].x
        fn = self.getcompiled(llf, [int])
        res = fn(1)
        assert res == 50
        res = fn(2)
        assert res == 60

    def test_fnptr_with_fixedsizearray(self):
        A = ForwardReference()
        F = FuncType([Ptr(A)], Signed)
        A.become(FixedSizeArray(Struct('s1', ('f', Ptr(F)), ('n', Signed)), 5))
        a = malloc(A, immortal=True)
        a[3].n = 42
        def llf(n):
            if a[n].f:
                return a[n].f(a)
            else:
                return -1
        fn = self.getcompiled(llf, [int])
        res = fn(4)
        assert res == -1

    def test_direct_arrayitems(self):
        for a in [malloc(GcArray(Signed), 5),
                  malloc(FixedSizeArray(Signed, 5), immortal=True),
                  malloc(Array(Signed, hints={'nolength': True}), 5,
                         immortal=True),
                  ]:
            a[0] = 0
            a[1] = 10
            a[2] = 20
            a[3] = 30
            a[4] = 40
            b0 = direct_arrayitems(a)
            b1 = direct_ptradd(b0, 1)
            b2 = direct_ptradd(b1, 1)
            def llf(n):
                b0 = direct_arrayitems(a)
                b3 = direct_ptradd(direct_ptradd(b0, 5), -2)
                saved = a[n]
                a[n] = 1000
                try:
                    return b0[0] + b3[-2] + b2[1] + b1[3]
                finally:
                    a[n] = saved
            fn = self.getcompiled(llf, [int])
            res = fn(0)
            assert res == 1000 + 10 + 30 + 40
            res = fn(1)
            assert res == 0 + 1000 + 30 + 40
            res = fn(2)
            assert res == 0 + 10 + 30 + 40
            res = fn(3)
            assert res == 0 + 10 + 1000 + 40
            res = fn(4)
            assert res == 0 + 10 + 30 + 1000

    def test_structarray_add(self):
        from pypy.rpython.lltypesystem import llmemory
        S = Struct("S", ("x", Signed))
        PS = Ptr(S)
        size = llmemory.sizeof(S)
        A = GcArray(S)
        itemoffset = llmemory.itemoffsetof(A, 0)
        def llf(n):
            a = malloc(A, 5)
            a[0].x = 1
            a[1].x = 2
            a[2].x = 3
            a[3].x = 42
            a[4].x = 4
            adr_s = llmemory.cast_ptr_to_adr(a)
            adr_s += itemoffset + size * n
            s = llmemory.cast_adr_to_ptr(adr_s, PS)
            return s.x
        fn = self.getcompiled(llf, [int])
        res = fn(3)
        assert res == 42

    def test_direct_fieldptr(self):
        S = GcStruct('S', ('x', Signed), ('y', Signed))
        def llf(n):
            s = malloc(S)
            a = direct_fieldptr(s, 'y')
            a[0] = n
            return s.y

        fn = self.getcompiled(llf, [int])
        res = fn(34)
        assert res == 34

    def test_prebuilt_subarrays(self):
        a1 = malloc(GcArray(Signed), 5, zero=True)
        a2 = malloc(FixedSizeArray(Signed, 5), immortal=True)
        s  = malloc(GcStruct('S', ('x', Signed), ('y', Signed)), zero=True)
        a1[3] = 7000
        a2[1] =  600
        s.x   =   50
        s.y   =    4
        p1 = direct_ptradd(direct_arrayitems(a1), 3)
        p2 = direct_ptradd(direct_arrayitems(a2), 1)
        p3 = direct_fieldptr(s, 'x')
        p4 = direct_fieldptr(s, 'y')
        def llf():
            a1[3] += 1000
            a2[1] +=  100
            s.x   +=   10
            s.y   +=    1
            return p1[0] + p2[0] + p3[0] + p4[0]

        fn = self.getcompiled(llf)
        res = fn()
        assert res == 8765

    def test_union(self):
        U = Struct('U', ('s', Signed), ('c', Char),
                   hints={'union': True})
        u = malloc(U, immortal=True)
        def llf(c):
            u.s = 0x10203040
            u.c = chr(c)
            return u.s

        fn = self.getcompiled(llf, [int])
        res = fn(0x33)
        assert res in [0x10203033, 0x33203040]

    def test_sizeof_void_array(self):
        from pypy.rpython.lltypesystem import llmemory
        A = Array(Void)
        size1 = llmemory.sizeof(A, 1)
        size2 = llmemory.sizeof(A, 14)
        def f(x):
            if x:
                return size1
            else:
                return size2
        fn = self.getcompiled(f, [int])
        res1 = fn(1)
        res2 = fn(0)
        assert res1 == res2

    def test_null_padding(self):
        py.test.skip("we no longer pad our RPython strings with a final NUL")
        from pypy.rpython.lltypesystem import llmemory
        from pypy.rpython.lltypesystem import rstr
        chars_offset = llmemory.FieldOffset(rstr.STR, 'chars') + \
                       llmemory.ArrayItemsOffset(rstr.STR.chars)
        # sadly, there's no way of forcing this to fail if the strings
        # are allocated in a region of memory such that they just
        # happen to get a NUL byte anyway :/ (a debug build will
        # always fail though)
        def trailing_byte(s):
            adr_s = llmemory.cast_ptr_to_adr(s)
            return (adr_s + chars_offset).char[len(s)]
        def f(x):
            r = 0
            for i in range(x):
                r += ord(trailing_byte(' '*(100-x*x)))
            return r
        fn = self.getcompiled(f, [int])
        res = fn(10)
        assert res == 0

    def test_cast_primitive(self):
        def f(x):
            x = cast_primitive(UnsignedLongLong, x)
            x <<= 60
            x /= 3
            x <<= 1
            x = cast_primitive(SignedLongLong, x)
            x >>= 32
            return cast_primitive(Signed, x)
        fn = self.getcompiled(f, [int])
        res = fn(14)
        assert res == -1789569707

    def test_prebuilt_integers(self):
        from pypy.rlib.unroll import unrolling_iterable
        from pypy.rpython.lltypesystem import rffi
        class Prebuilt:
            pass
        p = Prebuilt()
        NUMBER_TYPES = rffi.NUMBER_TYPES
        names = unrolling_iterable([TYPE.__name__ for TYPE in NUMBER_TYPES])
        for name, TYPE in zip(names, NUMBER_TYPES):
            value = cast_primitive(TYPE, 1)
            setattr(p, name, value)

        def f(x):
            total = x
            for name in names:
                total += rffi.cast(Signed, getattr(p, name))
            return total

        fn = self.getcompiled(f, [int])
        res = fn(100)
        assert res == 100 + len(list(names))

    def test_force_cast(self):
        from pypy.rpython.annlowlevel import llstr
        from pypy.rpython.lltypesystem.rstr import STR
        from pypy.rpython.lltypesystem import rffi, llmemory, lltype
        P = lltype.Ptr(lltype.FixedSizeArray(lltype.Char, 1))
        
        def f():
            a = llstr("xyz")
            b = (llmemory.cast_ptr_to_adr(a) + llmemory.offsetof(STR, 'chars')
                 + llmemory.itemoffsetof(STR.chars, 0))
            buf = rffi.cast(rffi.VOIDP, b)
            return buf[2]
        
        fn = self.getcompiled(f, [])
        res = fn()
        assert res == 'z'

    def test_array_nolength(self):
        A = Array(Signed, hints={'nolength': True})
        a1 = malloc(A, 3, immortal=True)
        a1[0] = 30
        a1[1] = 300
        a1[2] = 3000
        a1dummy = malloc(A, 2, immortal=True)

        def f(n):
            if n & 1:
                src = a1dummy
            else:
                src = a1
            a2 = malloc(A, n, flavor='raw')
            for i in range(n):
                a2[i] = src[i % 3] + i
            res = a2[n // 2]
            free(a2, flavor='raw')
            return res

        fn = self.getcompiled(f, [int])
        res = fn(100)
        assert res == 3050

    def test_gcarray_nolength(self):
        A = GcArray(Signed, hints={'nolength': True})
        a1 = malloc(A, 3, immortal=True)
        a1[0] = 30
        a1[1] = 300
        a1[2] = 3000
        a1dummy = malloc(A, 2, immortal=True)

        def f(n):
            if n & 1:
                src = a1dummy
            else:
                src = a1
            a2 = malloc(A, n)
            for i in range(n):
                a2[i] = src[i % 3] + i
            res = a2[n // 2]
            return res

        fn = self.getcompiled(f, [int])
        res = fn(100)
        assert res == 3050

    def test_structarray_nolength(self):
        S = Struct('S', ('x', Signed))
        A = Array(S, hints={'nolength': True})
        a1 = malloc(A, 3, immortal=True)
        a1[0].x = 30
        a1[1].x = 300
        a1[2].x = 3000
        a1dummy = malloc(A, 2, immortal=True)

        def f(n):
            if n & 1:
                src = a1dummy
            else:
                src = a1
            a2 = malloc(A, n, flavor='raw')
            for i in range(n):
                a2[i].x = src[i % 3].x + i
            res = a2[n // 2].x
            free(a2, flavor='raw')
            return res

        fn = self.getcompiled(f, [int])
        res = fn(100)
        assert res == 3050

    def test_zero_raw_malloc(self):
        S = Struct('S', ('x', Signed), ('y', Signed))
        def f(n):
            for i in range(n):
                p = malloc(S, flavor='raw', zero=True)
                if p.x != 0 or p.y != 0:
                    return -1
                p.x = i
                p.y = i
                free(p, flavor='raw')
            return 42

        fn = self.getcompiled(f, [int])
        res = fn(100)
        assert res == 42

    def test_zero_raw_malloc_varsize(self):
        # we don't support at the moment raw+zero mallocs with a length
        # field to initialize
        S = Struct('S', ('x', Signed), ('y', Array(Signed, hints={'nolength': True})))
        def f(n):
            for length in range(n-1, -1, -1):
                p = malloc(S, length, flavor='raw', zero=True)
                if p.x != 0:
                    return -1
                p.x = n
                for j in range(length):
                    if p.y[j] != 0:
                        return -3
                    p.y[j] = n^j
                free(p, flavor='raw')
            return 42

        fn = self.getcompiled(f, [int])
        res = fn(100)
        assert res == 42

    def test_arithmetic_cornercases(self):
        import operator, sys
        from pypy.rlib.unroll import unrolling_iterable
        from pypy.rlib.rarithmetic import r_longlong, r_ulonglong

        class Undefined:
            def __eq__(self, other):
                return True
        undefined = Undefined()

        def getmin(cls):
            if cls is int:
                return -sys.maxint-1
            elif cls.SIGNED:
                return cls(-(cls.MASK>>1)-1)
            else:
                return cls(0)
        getmin._annspecialcase_ = 'specialize:memo'

        def getmax(cls):
            if cls is int:
                return sys.maxint
            elif cls.SIGNED:
                return cls(cls.MASK>>1)
            else:
                return cls(cls.MASK)
        getmax._annspecialcase_ = 'specialize:memo'
        maxlonglong = long(getmax(r_longlong))

        classes = unrolling_iterable([int, r_uint, r_longlong, r_ulonglong])
        operators = unrolling_iterable([operator.add,
                                        operator.sub,
                                        operator.mul,
                                        operator.floordiv,
                                        operator.mod,
                                        operator.lshift,
                                        operator.rshift])
        def f(n):
            result = ()
            for cls in classes:
                for OP in operators:
                    x = getmin(cls)
                    res1 = OP(x, n)
                    result = result + (res1,)
                    x = getmax(cls)
                    res1 = OP(x, n)
                    result = result + (res1,)
            return result

        def assert_eq(a, b):
            # for better error messages when it fails
            assert len(a) == len(b)
            for i in range(len(a)):
                assert a[i] == b[i]

        fn = self.getcompiled(f, [int])
        res = fn(1)
        print res
        assert_eq(res, (
            # int
            -sys.maxint, undefined,               # add
            undefined, sys.maxint-1,              # sub
            -sys.maxint-1, sys.maxint,            # mul
            -sys.maxint-1, sys.maxint,            # floordiv
            0, 0,                                 # mod
            0, -2,                                # lshift
            (-sys.maxint-1)//2, sys.maxint//2,    # rshift
            # r_uint
            1, 0,                                 # add
            sys.maxint*2+1, sys.maxint*2,         # sub
            0, sys.maxint*2+1,                    # mul
            0, sys.maxint*2+1,                    # floordiv
            0, 0,                                 # mod
            0, sys.maxint*2,                      # lshift
            0, sys.maxint,                        # rshift
            # r_longlong
            -maxlonglong, undefined,              # add
            undefined, maxlonglong-1,             # sub
            -maxlonglong-1, maxlonglong,          # mul
            -maxlonglong-1, maxlonglong,          # floordiv
            0, 0,                                 # mod
            0, -2,                                # lshift
            (-maxlonglong-1)//2, maxlonglong//2,  # rshift
            # r_ulonglong
            1, 0,                                 # add
            maxlonglong*2+1, maxlonglong*2,       # sub
            0, maxlonglong*2+1,                   # mul
            0, maxlonglong*2+1,                   # floordiv
            0, 0,                                 # mod
            0, maxlonglong*2,                     # lshift
            0, maxlonglong,                       # rshift
            ))

        res = fn(5)
        print res
        assert_eq(res, (
            # int
            -sys.maxint+4, undefined,             # add
            undefined, sys.maxint-5,              # sub
            undefined, undefined,                 # mul
            (-sys.maxint-1)//5, sys.maxint//5,    # floordiv
            (-sys.maxint-1)%5, sys.maxint%5,      # mod
            0, -32,                               # lshift
            (-sys.maxint-1)//32, sys.maxint//32,  # rshift
            # r_uint
            5, 4,                                 # add
            sys.maxint*2-3, sys.maxint*2-4,       # sub
            0, sys.maxint*2-3,                    # mul
            0, (sys.maxint*2+1)//5,               # floordiv
            0, (sys.maxint*2+1)%5,                # mod
            0, sys.maxint*2-30,                   # lshift
            0, sys.maxint>>4,                     # rshift
            # r_longlong
            -maxlonglong+4, undefined,            # add
            undefined, maxlonglong-5,             # sub
            undefined, undefined,                 # mul
            (-maxlonglong-1)//5, maxlonglong//5,  # floordiv
            (-maxlonglong-1)%5, maxlonglong%5,    # mod
            0, -32,                               # lshift
            (-maxlonglong-1)//32, maxlonglong//32,# rshift
            # r_ulonglong
            5, 4,                                 # add
            maxlonglong*2-3, maxlonglong*2-4,     # sub
            0, maxlonglong*2-3,                   # mul
            0, (maxlonglong*2+1)//5,              # floordiv
            0, (maxlonglong*2+1)%5,               # mod
            0, maxlonglong*2-30,                  # lshift
            0, maxlonglong>>4,                    # rshift
            ))

    def test_direct_ptradd_barebone(self):
        from pypy.rpython.lltypesystem import rffi
        ARRAY_OF_CHAR = Array(Char, hints={'nolength': True})

        def llf():
            data = "hello, world!"
            a = malloc(ARRAY_OF_CHAR, len(data), flavor='raw')
            for i in xrange(len(data)):
                a[i] = data[i]
            a2 = rffi.ptradd(a, 2)
            assert typeOf(a2) == typeOf(a) == Ptr(ARRAY_OF_CHAR)
            for i in xrange(len(data) - 2):
                assert a2[i] == a[i + 2]
            free(a, flavor='raw')

        fn = self.getcompiled(llf)
        fn()

    def test_r_singlefloat(self):

        z = r_singlefloat(0.4)

        def g(n):
            if n > 0:
                return r_singlefloat(n * 0.1)
            else:
                return z

        def llf(n):
            return float(g(n))

        fn = self.getcompiled(llf, [int])
        res = fn(21)
        assert res != 2.1     # precision lost
        assert abs(res - 2.1) < 1E-6
        res = fn(-5)
        assert res != 0.4     # precision lost
        assert abs(res - 0.4) < 1E-6


    def test_array_of_array(self):
        C = FixedSizeArray(Signed, 7)
        B = Array(C)
        A = FixedSizeArray(C, 6)
        b = malloc(B, 5, immortal=True)
        b[3][4] = 999
        a = malloc(A, immortal=True)
        a[2][5] = 888000
        def llf():
            return b[3][4] + a[2][5]
        fn = self.getcompiled(llf)
        assert fn() == 888999

    def test_prebuilt_nolength_array(self):
        A = Array(Signed, hints={'nolength': True})
        a = malloc(A, 5, immortal=True)
        a[0] = 8
        a[1] = 5
        a[2] = 12
        a[3] = 12
        a[4] = 15
        def llf():
            s = ''
            for i in range(5):
                s += chr(64+a[i])
            assert s == "HELLO"
        fn = self.getcompiled(llf)
        fn()

    def test_prebuilt_nolength_char_array(self):
        for lastchar in ('\x00', 'X'):
            A = Array(Char, hints={'nolength': True})
            a = malloc(A, 6, immortal=True)
            a[0] = '8'
            a[1] = '5'
            a[2] = '?'
            a[3] = '!'
            a[4] = lastchar
            a[5] = '\x00'
            def llf():
                s = ''
                for i in range(5):
                    print i
                    print s
                    s += a[i]
                print s
                assert s == "85?!" + lastchar
            fn = self.getcompiled(llf)
            fn()

    def test_prebuilt_ll2ctypes_array(self):
        from pypy.rpython.lltypesystem import rffi, ll2ctypes
        A = rffi.CArray(Char)
        a = malloc(A, 6, flavor='raw')
        a[0] = 'a'
        a[1] = 'b'
        a[2] = 'c'
        a[3] = 'd'
        a[4] = '\x00'
        a[5] = '\x00'
        # side effects when converting to c structure
        ll2ctypes.lltype2ctypes(a)
        def llf():
            s = ''
            for i in range(4):
                s += a[i]
            return 'abcd' == s

        fn = self.getcompiled(llf)
        assert fn()

    def test_ll2ctypes_array_from_c(self):
        from pypy.rpython.lltypesystem import rffi, ll2ctypes
        A = rffi.CArray(Char)
        a = malloc(A, 6, flavor='raw')
        a[0] = 'a'
        a[1] = 'b'
        a[2] = 'c'
        a[3] = 'd'
        a[4] = '\x00'
        a[5] = '\x00'
        # side effects when converting to c structure
        c = ll2ctypes.lltype2ctypes(a)
        a = ll2ctypes.ctypes2lltype(Ptr(A), c)
        def llf():
            s = ''
            for i in range(4):
                s += a[i]
            print s
            return s == 'abcd'
        fn = self.getcompiled(llf)
        assert fn()

    def test_cast_to_void_array(self):
        from pypy.rpython.lltypesystem import rffi
        def llf():
            TYPE = Ptr(rffi.CArray(Void))
            y = rffi.cast(TYPE, 0)
        fn = self.getcompiled(llf)
        fn()

    def test_llgroup(self):
        from pypy.rpython.lltypesystem.test import test_llgroup
        f = test_llgroup.build_test()
        fn = self.getcompiled(f)
        res = fn()
        assert res == 42

    def test_llgroup_size_limit(self):
        yield self._test_size_limit, True
        yield self._test_size_limit, False

    def _test_size_limit(self, toobig):
        from pypy.rpython.lltypesystem import llgroup
        from pypy.rpython.lltypesystem.lloperation import llop
        from pypy.translator.platform import CompilationError
        grp = llgroup.group("big")
        S1 = Struct('S1', ('x', Signed), ('y', Signed),
                          ('z', Signed), ('u', Signed),
                          ('x2', Signed), ('y2', Signed),
                          ('z2', Signed), ('u2', Signed),
                          ('x3', Signed), ('y3', Signed),
                          ('z3', Signed), ('u3', Signed),
                          ('x4', Signed), ('y4', Signed),
                          ('z4', Signed), ('u4', Signed))
        goffsets = []
        for i in range(4096 + toobig):
            goffsets.append(grp.add_member(malloc(S1, immortal=True)))
        grpptr = grp._as_ptr()
        def f(n):
            p = llop.get_group_member(Ptr(S1), grpptr, goffsets[n])
            p.x = 5
            for i in range(len(goffsets)):
                if i != n:
                    q = llop.get_group_member(Ptr(S1), grpptr, goffsets[i])
                    q.x = 666
            return p.x
        if toobig:
            py.test.raises(CompilationError, self.getcompiled, f, [int])
        else:
            fn = self.getcompiled(f, [int])
            res = fn(len(goffsets)-1)
            assert res == 5

    def test_round_up_for_allocation(self):
        from pypy.rpython.lltypesystem import llmemory, llarena
        S = Struct('S', ('x', Char), ('y', Char))
        M = Struct('M', ('x', Char), ('y', Signed))
        #
        def g():
            ssize = llarena.round_up_for_allocation(llmemory.sizeof(S))
            msize = llarena.round_up_for_allocation(llmemory.sizeof(M))
            smsize = llarena.round_up_for_allocation(llmemory.sizeof(S),
                                                     llmemory.sizeof(M))
            mssize = llarena.round_up_for_allocation(llmemory.sizeof(M),
                                                     llmemory.sizeof(S))
            return ssize, msize, smsize, mssize
        #
        glob_sizes = g()
        #
        def check((ssize, msize, smsize, mssize)):
            assert ssize == llmemory.sizeof(Signed)
            assert msize == llmemory.sizeof(Signed) * 2
            assert smsize == msize
            assert mssize == msize
        #
        def f():
            check(glob_sizes)
            check(g())
            return 42
        #
        fn = self.getcompiled(f, [])
        res = fn()
        assert res == 42

import sys

import py
from pypy.rpython.lltypesystem.lltype import *
from pypy.translator.llvm import database, codewriter
from pypy.rlib import rarithmetic

from pypy.translator.llvm.test.runtest import *

def test_simple():
    S = GcStruct("s", ('v', Signed))
    def llf():
        s = malloc(S)
        return s.v
    fn = compile_function(llf, [])
    assert fn() == 0

def test_simple2():
    S = Struct("s", ('v', Signed))
    S2 = GcStruct("s2", ('a',S), ('b',S))
    def llf():
        s = malloc(S2)
        s.a.v = 6
        s.b.v = 12
        return s.a.v + s.b.v
    fn = compile_function(llf, [])
    assert fn() == 18

S = Struct("base", ('a', Signed), ('b', Signed))

def test_struct_constant1():
    P = GcStruct("s",
                        ('signed', Signed),
                        ('unsigned', Unsigned),
                        ('float', Float),
                        ('char', Char),
                        ('bool', Bool),
                        ('unichar', UniChar)
                        )

    s = malloc(P, zero=True)
    s.signed = 2
    s.unsigned = rarithmetic.r_uint(1)
    def struct_constant():
        x1 = s.signed + s.unsigned
        return x1
    f = compile_function(struct_constant, [])
    assert f() == struct_constant()

def test_struct_constant2():
    S2 = GcStruct("struct2", ('a', Signed), ('s1', S), ('s2', S))

    s = malloc(S2, zero=True)
    s.a = 5
    s.s1.a = 2
    s.s1.b = 4
    s.s2.b = 3
    def struct_constant():
        return s.a + s.s2.b + s.s1.a + s.s1.b
    f = compile_function(struct_constant, [])
    assert f() == struct_constant()

def test_struct_constant3():
    structs = []
    cur = S
    for n in range(20):
        cur = Struct("struct%s" % n,  ("s", cur))
        structs.append(cur)
    TOP = GcStruct("top", ("s", cur))
        
    top = malloc(TOP)
    cur = top.s
    for ii in range(20):
        cur = cur.s
    cur.a = 10
    cur.b = 5
    def struct_constant():
        return (top.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.a -
                top.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.b)
    
    f = compile_function(struct_constant, [])
    assert f() == struct_constant()

def test_struct_constant4():
    SPTR = GcStruct('sptr', ('a', Signed))
    STEST = GcStruct('test', ('sptr', Ptr(SPTR)))
    s = malloc(STEST)
    s.sptr = malloc(SPTR)
    s.sptr.a = 21
    def struct_constant():
        return s.sptr.a * 2
    f = compile_function(struct_constant, [])
    assert f() == struct_constant()

def test_struct_constant5():
    SPTR = GcStruct('sptr', ('a', Signed), ('b', S))
    STEST = GcStruct('test', ('sptr', Ptr(SPTR)))
    s = malloc(STEST)
    s.sptr = malloc(SPTR)
    s.sptr.a = 21
    s.sptr.b.a = 11
    s.sptr.b.b = 10
    def struct_constant():
        return s.sptr.a + s.sptr.b.a + s.sptr.b.b
    f = compile_function(struct_constant, [])
    assert f() == struct_constant()

def test_aliasing():
    B = Struct('B', ('x', Signed))
    A = Array(B)
    global_a = malloc(A, 5, immortal=True)
    global_b = global_a[3]
    def aliasing(i):
        global_b.x = 17
        return global_a[i].x
    f = compile_function(aliasing, [int])
    assert f(2) == 0
    assert f(3) == 17

def test_aliasing2():
    B = Struct('B', ('x', Signed))
    A = Array(B)
    C = Struct('C', ('x', Signed), ('bptr', Ptr(B)))
    global_a = malloc(A, 5, immortal=True)
    global_c = malloc(C, immortal=True)
    global_c.bptr = global_a[3]
    def aliasing(i):
        global_c.bptr.x = 17
        return global_a[i].x
    f = compile_function(aliasing, [int])
    assert f(2) == 0
    assert f(3) == 17    

def test_array_constant():
    A = GcArray(Signed)
    a = malloc(A, 3)
    a[0] = 100
    a[1] = 101
    a[2] = 102
    def array_constant():
        return a[0] + a[1] + a[2]    
    f = compile_function(array_constant, [])
    assert f() == array_constant()

def test_array_constant2():
    A = GcArray(Signed)
    a = malloc(A, 3)
    a[0] = 100
    a[1] = 101
    a[2] = 102
    def array_constant():
        a[0] = 0
        return a[0] + a[1] + a[2]    
    f = compile_function(array_constant, [])
    assert f() == array_constant()

def test_array_constant3():
    A = GcArray(('x', Signed))
    a = malloc(A, 3)
    a[0].x = 100
    a[1].x = 101
    a[2].x = 102
    def array_constant():
        return a[0].x + a[1].x + a[2].x    
    f = compile_function(array_constant, [])
    assert f() == array_constant()

def test_struct_array1():
    A = GcArray(Signed)
    STEST = GcStruct('test', ('aptr', Ptr(A)))
    s = malloc(STEST)
    s.aptr = a = malloc(A, 2)
    a[0] = 100
    a[1] = 101
    def array_constant():
        return s.aptr[1] - a[0]
    f = compile_function(array_constant, [])
    assert f() == array_constant()
    
def test_struct_array2():
    A = Array(Signed)
    STEST = GcStruct('test', ('a', Signed), ('b', A))
    s = malloc(STEST, 2)
    s.a = 41
    s.b[0] = 100
    s.b[1] = 101

    def array_constant():
        return s.b[1] - s.b[0] + s.a
    f = compile_function(array_constant, [])
    assert f() == array_constant()

def test_struct_array3():
    A = Array(Signed)
    STEST = GcStruct('test', ('a', Signed), ('b', A))
    SBASE = GcStruct('base', ('p', Ptr(STEST)))
    s = malloc(STEST, 2)
    s.a = 41
    s.b[0] = 100
    s.b[1] = 101
    b = malloc(SBASE)
    b.p = s
    def array_constant():
        s = b.p
        return s.b[1] - s.b[0] + s.a
    f = compile_function(array_constant, [])
    assert f() == array_constant()

def test_struct_opaque():
    PRTTI = Ptr(RuntimeTypeInfo)
    S = GcStruct('s', ('a', Signed), ('r', PRTTI))
    s = malloc(S, zero=True)
    s.a = 42
    def struct_opaque():
        return s.a
    f = compile_function(struct_opaque, [])
    assert f() == struct_opaque()

def test_floats():
    " test pbc of floats "
    from pypy.rlib.rarithmetic import INFINITY, NAN

    if sys.maxint != 2**31-1:
        py.test.skip("WIP on 64 bit architectures")
    F = GcStruct("f",
                        ('f1', Float),
                        ('f2', Float),
                        ('f3', Float),
                        ('f4', Float),
                        ('f5', Float),
                        ('f6', Float),
                        )
    floats = malloc(F)
    floats.f1 = 1.25
    floats.f2 = 10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000.252984
    floats.f3 = float(29050000000000000000000000000000000000000000000000000000000000000000)
    floats.f4 = INFINITY
    nan = floats.f5 = NAN
    floats.f6 = -INFINITY

    def floats_fn():
        res  = floats.f1 == 1.25
        res += floats.f2 > 1e100
        res += floats.f3 > 1e50        
        res += floats.f4 > 1e200
        res += floats.f5 == NAN
        res += floats.f4 < -1e200
        return res
    f = compile_function(floats_fn, [])
    assert f() == floats_fn()

def test_simple_fixedsizearray():
    A2 = FixedSizeArray(Signed, 2)
    S = GcStruct("s", ("a2", A2))
    def llf():
        s = malloc(S)
        a2 = s.a2
        a2[0] = -1
        a2.item1 = -2
        assert a2[0] == -1
        assert a2[1] == -2
        assert a2.item1 == -2
        return s.a2.item0 - s.a2[1]
    fn = compile_function(llf, [])
    res = fn()
    assert fn() == 1

def test_fixedsizearray():
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
        return len(a42) * 100 + len(a42[4])
    fn = compile_function(llf, [])
    res = fn()
    assert fn() == 607

def test_recursivearray():
    A = ForwardReference()
    A.become(FixedSizeArray(Struct("S", ('a', Ptr(A))), 5))
    TREE = Struct("TREE", ("root", A), ("other", A))
    tree = malloc(TREE, immortal=True)
    def llf():
        tree.root[0].a = tree.root
        tree.root[1].a = tree.other
        assert tree.root[0].a[0].a[0].a[0].a[0].a[1].a == tree.other
        return 0
    fn = compile_function(llf, [])
    fn()

def test_prebuilt_array():
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
        return 0
    fn = compile_function(llf, [])
    fn()

def test_call_with_fixedsizearray():
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
    fn = compile_function(llf, [])
    res = fn()
    assert res == 123

def test_more_prebuilt_arrays():
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
    fn = compile_function(llf, [int])
    res = fn(1)
    assert res == 50
    res = fn(2)
    assert res == 60

def test_fnptr_with_fixedsizearray():
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
    fn = compile_function(llf, [int])
    res = fn(4)
    assert res == -1

def test_direct_arrayitems():
    for a in [malloc(GcArray(Signed), 5),
              malloc(FixedSizeArray(Signed, 5), immortal=True),
              malloc(Array(Signed, hints={'nolength': True}), 5, immortal=True)]:
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

        fn = compile_function(llf, [int])
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

def test_structarray_add():
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
    fn = compile_function(llf, [int])
    res = fn(3)
    assert res == 42

def test_direct_fieldptr():
    S = GcStruct('S', ('x', Signed), ('y', Signed))
    def llf(n):
        s = malloc(S)
        a = direct_fieldptr(s, 'y')
        a[0] = n
        return s.y

    fn = compile_function(llf, [int])
    res = fn(34)
    assert res == 34

def test_union():
    py.test.skip("not unions!!")
    U = Struct('U', ('s', Signed), ('c', Char),
               hints={'union': True})
    u = malloc(U, immortal=True)
    def llf(c):
        u.s = 0x10203040
        u.c = chr(c)
        return u.s

    fn = compile_function(llf, [int])
    res = fn(0x33)
    assert res in [0x10203033, 0x33203040]

def test_prebuilt_simple_subarrays():
    a2 = malloc(FixedSizeArray(Signed, 5), immortal=True)
    a2[1] = 42
    p2 = direct_ptradd(direct_arrayitems(a2), 1)
    def llf():
        a2[1] += 100
        return p2[0]

    fn = compile_function(llf, [])
    res = fn()
    assert res == 142

def test_prebuilt_subarrays():
    a1 = malloc(GcArray(Signed), 5, zero=True)
    a2 = malloc(FixedSizeArray(Signed, 5), immortal=True)
    s  = malloc(GcStruct('S', ('x', Signed), ('y', Signed)))
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

    fn = compile_function(llf, [])
    res = fn()
    assert res == 8765

def test_malloc_array_void():
    A = GcArray(Void)
    def llf():
        a1 = malloc(A, 5, zero=True)
        return len(a1)
    fn = compile_function(llf, [])
    res = fn()
    assert res == 5

def test_sizeof_void_array():
    from pypy.rpython.lltypesystem import llmemory
    A = Array(Void)
    size1 = llmemory.sizeof(A, 1)
    size2 = llmemory.sizeof(A, 14)
    def f(x):
        if x:
            return size1
        else:
            return size2
    fn = compile_function(f, [int])
    res1 = fn(1)
    res2 = fn(0)
    assert res1 == res2

def test_null_padding():
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
    fn = compile_function(f, [int])
    res = fn(10)
    assert res == 0

def test_simplearray_nolength():
    A = GcArray(Signed, hints={'nolength': True})
    def llf():
        s = malloc(A, 5)
        s[0] = 1
        s[1] = 2
        return s[0] + s[1]
    fn = compile_function(llf, [])
    assert fn() == 3

def test_array_nolength():
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

    fn = compile_function(f, [int])
    res = fn(100)
    assert res == 3050

def test_prebuilt_integers():
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

    fn = compile_function(f, [int])
    res = fn(100)
    assert res == 100 + len(list(names))

def test_array_nolength():
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

    fn = compile_function(f, [int])
    res = fn(100)
    assert res == 3050

def test_gcarray_nolength():
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

    fn = compile_function(f, [int])
    res = fn(100)
    assert res == 3050

def test_structarray_nolength():
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

    fn = compile_function(f, [int])
    res = fn(100)
    assert res == 3050

def test_zero_raw_malloc():
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

    fn = compile_function(f, [int])
    res = fn(100)
    assert res == 42

def test_zero_raw_malloc_varsize():
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

    fn = compile_function(f, [int])
    res = fn(100)
    assert res == 42

def test_direct_ptradd_barebone():
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
        return 0

    fn = compile_function(llf, [])
    fn()

def test_prebuilt_nolength_array():
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
        return 0

    fn = compile_function(llf, [])
    fn()

def test_longlongs():
    def llf(n):
        return r_longlong(n) * r_longlong(2**32)
    fn = compile_function(llf, [int])
    assert fn(0) == 0
    assert fn(42) == 42 * 2**32
    assert fn(-42) == -42 * 2**32
    def llf(n):
        return r_ulonglong(n) * r_ulonglong(2**32)
    fn = compile_function(llf, [int])
    assert fn(0) == 0
    assert fn(42) == 42 * 2**32

def test_rettypes():
    ' test returning bool and void types '
    def llf():
        return
    fn = compile_function(llf, [])
    assert fn() is None
    def llf():
        return not(False)
    fn = compile_function(llf, [])
    assert fn() is True

def test_r_singlefloat():
    z = r_singlefloat(0.4)

    def llf():
        return z

    fn = compile_function(llf, [])
    res = fn()
    assert res != 0.4     # precision lost
    assert abs(res - 0.4) < 1E-6

    def g(n):
        if n > 0:
            return r_singlefloat(n * 0.1)
        else:
            return z

    def llf(n):
        return float(g(n))

    fn = compile_function(llf, [int])
    res = fn(21)
    assert res != 2.1     # precision lost
    assert abs(res - 2.1) < 1E-6
    res = fn(-5)
    assert res != 0.4     # precision lost
    assert abs(res - 0.4) < 1E-6

class TestLowLevelType(object):
    def getcompiled(self, f, args=[]):
        return compile_function(f, args)

    def test_arithmetic_cornercases(self):
        py.test.skip("pyobject in this test - but why ???")
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
                values = [getmin(cls), getmax(cls)]
                for OP in operators:
                    for x in values:
                        res1 = OP(x, n)
                        result += (res1,)
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

    def test_prebuilt_nolength_char_array(self):
        py.test.skip("fails on the trunk too")
        for lastchar in ('\x00', 'X'):
            A = Array(Char, hints={'nolength': True})
            a = malloc(A, 5, immortal=True)
            a[0] = '8'
            a[1] = '5'
            a[2] = '?'
            a[3] = '!'
            a[4] = lastchar
            def llf():
                s = ''
                for i in range(5):
                    print i
                    print s
                    s += a[i]
                print s
                assert s == "85?!" + lastchar
                return 0

            fn = self.getcompiled(llf)
            fn()

    # XXX what does this do?
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


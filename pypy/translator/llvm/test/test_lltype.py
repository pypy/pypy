import sys

import py
from pypy.rpython.lltypesystem.lltype import *
from pypy.translator.llvm import database, codewriter
from pypy.rlib import rarithmetic

from pypy.translator.llvm.test.runtest import *

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

def test_struct_constant6():
    U = Struct('inlined', ('z', Signed))
    T = GcStruct('subtest', ('y', Signed))
    S = GcStruct('test', ('x', Ptr(T)), ('u', U), ('p', Ptr(U)))

    s = malloc(S)
    s.x = malloc(T)
    s.x.y = 42
    s.u.z = -100
    s.p = s.u
    def struct_constant():
        return s.x.y + s.p.z
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

def test_floats():  #note: this is known to fail with llvm1.6 and llvm1.7cvs when not using gcc
    " test pbc of floats "
    if sys.maxint != 2**31-1:
        py.test.skip("WIP on 64 bit architectures")
    F = GcStruct("f",
                        ('f1', Float),
                        ('f2', Float),
                        ('f3', Float),
                        ('f4', Float),
                        ('f5', Float),
                        )
    floats = malloc(F)
    floats.f1 = 1.25
    floats.f2 = 10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000.252984
    floats.f3 = float(29050000000000000000000000000000000000000000000000000000000000000000)
    floats.f4 = 1e300 * 1e300
    nan = floats.f5 = floats.f4/floats.f4
    def floats_fn():
        res  = floats.f1 == 1.25
        res += floats.f2 > 1e100
        res += floats.f3 > 1e50        
        res += floats.f4 > 1e200
        res += floats.f5 == nan
        return res
    f = compile_function(floats_fn, [])
    assert f() == floats_fn()

def test_fixedsizearray():
    gcc3_test()
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
    gcc3_test()
    A = ForwardReference()
    A.become(FixedSizeArray(Struct("S", ('a', Ptr(A))), 5))
    TREE = GcStruct("TREE", ("root", A), ("other", A))
    def llf():
        tree = malloc(TREE)
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
        assert s == "HELLO0"
        return 0
    fn = compile_function(llf, [])
    fn()

def test_call_with_fixedsizearray():
    gcc3_test()
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
    gcc3_test()
    A = FixedSizeArray(Struct('s1', ('x', Signed)), 5)
    S = GcStruct('s', ('a1', Ptr(A)), ('a2', A))
    s = malloc(S, zero=True)
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
    gcc3_test()
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
              malloc(FixedSizeArray(Signed, 5), immortal=True)]:
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

def test_direct_fieldptr():
    gcc3_test()
    S = GcStruct('S', ('x', Signed), ('y', Signed))
    def llf(n):
        s = malloc(S)
        a = direct_fieldptr(s, 'y')
        a[0] = n
        return s.y

    fn = compile_function(llf, [int])
    res = fn(34)
    assert res == 34

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


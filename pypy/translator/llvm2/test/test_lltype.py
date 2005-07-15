
import py

from pypy.rpython import lltype

from pypy.translator.llvm2.genllvm import compile_function
from pypy.translator.llvm2 import database, codewriter
from pypy.rpython import rarithmetic 

py.log.setconsumer("genllvm", py.log.STDOUT)
py.log.setconsumer("genllvm database prepare", None)

S = lltype.Struct("base", ('a', lltype.Signed), ('b', lltype.Signed))

def test_struct_constant1():
    P = lltype.GcStruct("s",
                        ('signed', lltype.Signed),
                        ('unsigned', lltype.Unsigned),
                        ('float', lltype.Float),
                        ('char', lltype.Char),
                        ('bool', lltype.Bool),
                        ('unichar', lltype.UniChar)
                        )

    s = lltype.malloc(P)
    s.signed = 2
    s.unsigned = rarithmetic.r_uint(1)
    def struct_constant():
        x1 = s.signed + s.unsigned
        return x1
    fn = compile_function(struct_constant, [], embedexterns=False)
    assert fn() == 3

def test_struct_constant2():
    S2 = lltype.GcStruct("struct2", ('a', lltype.Signed), ('s1', S), ('s2', S))

    s = lltype.malloc(S2)
    s.a = 5
    s.s1.a = 2
    s.s1.b = 4
    s.s2.b = 3
    def struct_constant():
        return s.a + s.s2.b + s.s1.a + s.s1.b
    fn = compile_function(struct_constant, [], embedexterns=False)
    assert fn() == 14

def test_struct_constant3():
    structs = []
    cur = S
    for n in range(20):
        cur = lltype.Struct("struct%s" % n,  ("s", cur))
        structs.append(cur)
    TOP = lltype.GcStruct("top", ("s", cur))
        
    top = lltype.malloc(TOP)
    cur = top.s
    for ii in range(20):
        cur = cur.s
    cur.a = 10
    cur.b = 5
    def struct_constant():
        return (top.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.a -
                top.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.s.b)
    
    fn = compile_function(struct_constant, [], embedexterns=False)
    assert fn() == 5

def test_struct_constant4():
    SPTR = lltype.GcStruct('sptr', ('a', lltype.Signed))
    STEST = lltype.GcStruct('test', ('sptr', lltype.Ptr(SPTR)))
    s = lltype.malloc(STEST)
    s.sptr = lltype.malloc(SPTR)
    s.sptr.a = 21
    def struct_constant():
        return s.sptr.a * 2
    fn = compile_function(struct_constant, [], embedexterns=False)
    assert fn() == 42

def test_struct_constant5():
    SPTR = lltype.GcStruct('sptr', ('a', lltype.Signed), ('b', S))
    STEST = lltype.GcStruct('test', ('sptr', lltype.Ptr(SPTR)))
    s = lltype.malloc(STEST)
    s.sptr = lltype.malloc(SPTR)
    s.sptr.a = 21
    s.sptr.b.a = 11
    s.sptr.b.b = 10
    def struct_constant():
        return s.sptr.a + s.sptr.b.a + s.sptr.b.b
    fn = compile_function(struct_constant, [], embedexterns=False)
    assert fn() == 42

def test_struct_constant6():
    U = lltype.Struct('inlined', ('z', lltype.Signed))
    T = lltype.GcStruct('subtest', ('y', lltype.Signed))
    S = lltype.GcStruct('test', ('x', lltype.Ptr(T)), ('u', U), ('p', lltype.Ptr(U)))

    s = lltype.malloc(S)
    s.x = lltype.malloc(T)
    s.x.y = 42
    s.u.z = -100
    s.p = s.u
    def struct_constant():
        return s.x.y + s.p.z
    fn = compile_function(struct_constant, [], embedexterns=False)
    assert fn() == -58

def test_array_constant():
    A = lltype.GcArray(lltype.Signed)
    a = lltype.malloc(A, 3)
    a[0] = 100
    a[1] = 101
    a[2] = 102
    def array_constant():
        return a[0] + a[1] + a[2]    
    fn = compile_function(array_constant, [], embedexterns=False)
    assert fn() == 303

def test_array_constant2():
    A = lltype.GcArray(lltype.Signed)
    a = lltype.malloc(A, 3)
    a[0] = 100
    a[1] = 101
    a[2] = 102
    def array_constant():
        a[0] = 0
        return a[0] + a[1] + a[2]    
    fn = compile_function(array_constant, [], embedexterns=False)
    assert fn() == 203

def test_array_constant3():
    A = lltype.GcArray(('x', lltype.Signed))
    a = lltype.malloc(A, 3)
    a[0].x = 100
    a[1].x = 101
    a[2].x = 102
    def array_constant():
        return a[0].x + a[1].x + a[2].x    
    fn = compile_function(array_constant, [], embedexterns=False)
    assert fn() == 303

def test_struct_array1():
    A = lltype.GcArray(lltype.Signed)
    STEST = lltype.GcStruct('test', ('aptr', lltype.Ptr(A)))
    s = lltype.malloc(STEST)
    s.aptr = a = lltype.malloc(A, 2)
    a[0] = 100
    a[1] = 101
    def array_constant():
        return s.aptr[1] - a[0]
    fn = compile_function(array_constant, [], embedexterns=False)
    assert fn() == 1

def test_struct_array2():
    A = lltype.Array(lltype.Signed)
    STEST = lltype.GcStruct('test', ('a', lltype.Signed), ('b', A))
    s = lltype.malloc(STEST, 2)
    s.a = 41
    s.b[0] = 100
    s.b[1] = 101
    def array_constant():
        return s.b[1] - s.b[0] + s.a
    fn = compile_function(array_constant, [], embedexterns=False)
    assert fn() == 42

def test_struct_array3():
    A = lltype.Array(lltype.Signed)
    STEST = lltype.GcStruct('test', ('a', lltype.Signed), ('b', A))
    SBASE = lltype.GcStruct('base', ('p', lltype.Ptr(STEST)))
    s = lltype.malloc(STEST, 2)
    s.a = 41
    s.b[0] = 100
    s.b[1] = 101
    b = lltype.malloc(SBASE)
    b.p = s
    def array_constant():
        s = b.p
        return s.b[1] - s.b[0] + s.a
    fn = compile_function(array_constant, [], embedexterns=False)
    assert fn() == 42

def test_struct_opaque():
    PRTTI = lltype.Ptr(lltype.RuntimeTypeInfo)
    S = lltype.GcStruct('s', ('a', lltype.Signed), ('r', PRTTI))
    s = lltype.malloc(S)
    s.a = 42
    def array_constant():
        return s.a
    fn = compile_function(array_constant, [], embedexterns=False)
    assert fn() == 42
    

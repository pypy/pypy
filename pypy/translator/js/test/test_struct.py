import py
from pypy.rpython.lltypesystem import lltype
from pypy.translator.js.test.runtest import compile_function

S = lltype.Struct("S",
    ('myvar1', lltype.Unsigned),
    ('myvar2', lltype.Signed),
    ('myvar3', lltype.Float),
    ('myvar4', lltype.Char),
    ('myvar5', lltype.Void),
    ('myvar7', lltype.Bool),
    )

Sgc = lltype.GcStruct("Sgc",
    ('myvar1', lltype.Unsigned),
    ('myvar2', lltype.Signed),
    ('myvar3', lltype.Float),
    ('myvar4', lltype.Char),
    ('myvar5', lltype.Void),
    ('myvar7', lltype.Bool),
    )

T = lltype.Struct("T", ('myvar3', lltype.Signed), ('myvar4', lltype.Signed))
Q = lltype.Struct("Q", ('myvar5', lltype.Signed), ('myvar6', T), ('myvar7', lltype.Signed))

P = lltype.Struct("P",
    ("myvar1", T),
    ("myvar2", Q),
    )

Pgc = lltype.GcStruct("Pgc",
    ("myvar1", T),
    ("myvar2", Q),
    )

A = lltype.Array(P)
Agc = lltype.GcArray(P)

VA = lltype.Array(lltype.Signed)
VSgc = lltype.GcStruct("VSgc", ('myvar1', lltype.Signed), ('myvarsizearray', VA))


def test_struct1():
    s = lltype.malloc(S, immortal=True)
    def struct1():
        return s.myvar1
    f = compile_function(struct1, [])
    assert f() == struct1()

def test_struct2():
    def struct2():
        s = lltype.malloc(Sgc)
        return s.myvar1
    f = compile_function(struct2, [])
    assert f() == struct2()

def test_nested_struct1():
    p = lltype.malloc(P, immortal=True)
    def nested_struct1():
        return p.myvar2.myvar6.myvar3
    f = compile_function(nested_struct1, [])
    assert f() == nested_struct1()

def test_nested_struct2():
    def nested_struct2():
        p = lltype.malloc(Pgc)
        return p.myvar2.myvar6.myvar3
    f = compile_function(nested_struct2, [])
    assert f() == nested_struct2()

def test_array1():
    a = lltype.malloc(A, 5, immortal=True)
    def array1():
        return a[0].myvar2.myvar6.myvar3 + a[4].myvar2.myvar6.myvar3
    f = compile_function(array1, [])
    assert f() == array1()

def test_array2():
    def array2():
        a = lltype.malloc(Agc, 5)
        return a[0].myvar2.myvar6.myvar3 + a[4].myvar2.myvar6.myvar3
    f = compile_function(array2, [])
    assert f() == array2()

def test_array3():
    def array3(n):
        a = lltype.malloc(Agc, n)
        return a[0].myvar2.myvar6.myvar3 + a[n-1].myvar2.myvar6.myvar3
    f = compile_function(array3, [int])
    assert f(3) == array3(3)

def test_varsizestruct1():
    py.test.skip("issue with malloc_varsize structs")
    def varsizestruct1(n):
        vs = lltype.malloc(VSgc, n+5)
        vs.myvarsizearray[0] = 123
        return vs.myvar1 + vs.myvarsizearray[0] + len(vs.myvarsizearray)
    f = compile_function(varsizestruct1, [int])
    assert f(0) == varsizestruct1(0)

from pypy.rpython.memory.lltypesimulation import *
from pypy.rpython.memory.convertlltype import LLTypeConverter

def test_convert_primitives():
    cvter = LLTypeConverter(lladdress.NULL)
    addr = lladdress.raw_malloc(10)
    c1 = cvter.convert(1)
    c = cvter.convert("c")
    assert c1 == 1
    assert c == "c"
    cvter.convert(10, addr)
    assert addr.signed[0] == 10
    cvter.convert("c", addr)
    assert addr.char[0] == "c"

def test_convert_array_of_primitives():
    cvter = LLTypeConverter(lladdress.raw_malloc(1000))
    A = lltype.GcArray(lltype.Signed)
    lls = lltype.malloc(A, 3)
    lls[0] = 1
    lls[1] = 2
    a = cvter.convert(lls)
    assert a[0] == 1
    assert a[1] == 2

def test_convert_array_of_structs():
    cvter = LLTypeConverter(lladdress.raw_malloc(1000))
    S = lltype.Struct("test", ("v1", lltype.Signed), ("v2", lltype.Signed))
    Ar =  lltype.GcArray(S)
    llx = lltype.malloc(Ar, 3)
    llx[0].v1 = 1
    llx[1].v1 = 2
    llx[2].v1 = 3    
    x = cvter.convert(llx)
    assert [x[z].v1 for z in range(3)] == [1, 2, 3]
    assert [x[z].v2 for z in range(3)] == [0, 0, 0]

def test_convert_array_of_ptrs():
    cvter = LLTypeConverter(lladdress.raw_malloc(1000))
    S = lltype.GcStruct("name", ("v", lltype.Signed))
    A = lltype.GcArray(lltype.Ptr(S))
    lla = lltype.malloc(A, 3)
    lla[0] = lltype.malloc(S)
    lla[0].v = 1
    lla[1] = lltype.malloc(S)
    lla[1].v = 2
    lla[2] = lltype.malloc(S)
    lla[2].v = 3
    assert [lla[z].v for z in range(3)] == [1, 2, 3]
    print lla
    print [lla[z] for z in range(3)]
    x = cvter.convert(lla)
    print x
    print [x[z] for z in range(3)]
    print x._address._load("iiiiiii")
    assert [x[z].v for z in range(3)] == [1, 2, 3]
    

def test_circular_struct():
    cvter = LLTypeConverter(lladdress.raw_malloc(100))
    F = lltype.GcForwardReference()
    S = lltype.GcStruct('abc', ('x', lltype.Ptr(F)))
    F.become(S)
    lls = lltype.malloc(S)
    lls.x = lls
    s = cvter.convert(lls)
    assert s.x.x.x.x.x.x.x.x.x.x.x.x.x.x.x.x.x == s

def test_circular_array():
    cvter = LLTypeConverter(lladdress.raw_malloc(1000))
    F = lltype.GcForwardReference()
    A = lltype.GcArray(lltype.Ptr(F))
    S = lltype.GcStruct("name", ("a", lltype.Ptr(A)), ("b", lltype.Signed))
    F.become(S)
    lla = lltype.malloc(A, 3)
    lla[0] = lltype.malloc(S)
    lla[1] = lltype.malloc(S)
    lla[2] = lltype.malloc(S)
    lla[0].a = lla
    lla[1].a = lla
    lla[2].a = lla
    lla[0].b = 1
    lla[1].b = 2
    lla[2].b = 3
    assert lla[0].a[1].a[2].a == lla
    assert [lla[i].b for i in range(3)] == [1, 2, 3]
    a = cvter.convert(lla)
    assert a[0].a[1].a[2].a == a
    assert [a[i].b for i in range(3)] == [1, 2, 3]

def test_varsize_struct():
    cvter = LLTypeConverter(lladdress.raw_malloc(1000))
    A = lltype.Array(lltype.Signed)
    S = lltype.GcStruct("name", ("v", lltype.Signed), ("a", A))
    lls = lltype.malloc(S, 3)
    lls.a[0] = 1
    lls.a[1] = 2
    lls.a[2] = 3
    lls.v = 4
    s = cvter.convert(lls)
    assert [s.a[i] for i in range(3)] == [1, 2, 3]
    assert s.v == 4
    
def test_nullptr():
    cvter = LLTypeConverter(lladdress.raw_malloc(10))
    S = lltype.GcStruct("name", ("v", lltype.Signed))
    llptr = lltype.nullptr(S)
    s = cvter.convert(llptr)
    assert not s

def test_funcptr():
    def f(x, y):
        return x + y
    F = lltype.FuncType((lltype.Signed, lltype.Signed), lltype.Signed)
    llfuncptr = lltype.functionptr(F, "add", _callable=f)
    assert llfuncptr(1, 2) == 3
    cvter = LLTypeConverter(lladdress.raw_malloc(10))
    fpter = cvter.convert(llfuncptr)
    assert fpter(1, 2) == 3

def test_convertsubstructure():
    cvter = LLTypeConverter(lladdress.raw_malloc(100))
    S1 = lltype.GcStruct("s1", ("v1", lltype.Signed))
    S2 = lltype.GcStruct("s2", ("s", S1), ("v2", lltype.Signed))
    lls2 = lltype.malloc(S2)
    lls1 = lltype.cast_pointer(lltype.Ptr(S1), lls2)
    s1 = cvter.convert(lls1)
    s2 = cast_pointer(lltype.Ptr(S2), s1)
    assert s2.v2 == 0

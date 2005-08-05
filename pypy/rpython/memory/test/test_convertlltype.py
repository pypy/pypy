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
    lla[2].v = 2
    x = cvter.convert(lla)
    assert [x[z].v for z in range(3)] == [1, 2, 3]


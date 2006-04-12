from pypy.rpython.lltypesystem.llmemory import *
from pypy.rpython.lltypesystem import lltype
import py

def test_simple():
    S = lltype.GcStruct("S", ("x", lltype.Signed), ("y", lltype.Signed))
    s = lltype.malloc(S)
    s.x = 123
    s.y = 456
    a = fakeaddress(s)
    assert a.get() == s
    b = a + FieldOffset(S, 'x')
    assert b.get() == 123
    b.set(234)
    assert s.x == 234

def test_composite():
    S1 = lltype.GcStruct("S1", ("x", lltype.Signed), ("y", lltype.Signed))
    S2 = lltype.GcStruct("S2", ("s", S1))
    s2 = lltype.malloc(S2)
    s2.s.x = 123
    s2.s.y = 456
    a = fakeaddress(s2)
    assert a.get() == s2
    b = a + FieldOffset(S2, 's') + FieldOffset(S1, 'x')
    assert b.get() == 123
    b.set(234)
    assert s2.s.x == 234
    
def test_array():
    A = lltype.GcArray(lltype.Signed)
    x = lltype.malloc(A, 5)
    x[3] = 123
    a = fakeaddress(x)
    b = a + ArrayItemsOffset(A)
    b += ItemOffset(lltype.Signed)*2
    b += ItemOffset(lltype.Signed)
    assert b.get() == 123
    b.set(14)
    assert x[3] == 14
    
def test_dont_mix_offsets_and_ints():
    o = AddressOffset()
    py.test.raises(TypeError, "1 + o")
    py.test.raises(TypeError, "o + 1")
    
def test_sizeof():
    # this is mostly an "assert not raises" sort of test
    array = lltype.Array(lltype.Signed)
    struct = lltype.Struct("S", ('x', lltype.Signed))
    varstruct = lltype.Struct("S", ('x', lltype.Signed), ('y', array))
    sizeof(struct)
    sizeof(lltype.Signed)
    py.test.raises(AssertionError, "sizeof(array)")
    py.test.raises(AssertionError, "sizeof(varstruct)")
    sizeof(array, 1)
    sizeof(varstruct, 2)

def test_cast_ptr_to_adr():
    from pypy.rpython.memory.test.test_llinterpsim import interpret
    class A(object):
        pass
    def f(x):
        if x:
            a = A()
        else:
            a = None
        adr_a = cast_ptr_to_adr(a)
        return bool(adr_a)
    res = interpret(f, [1])
    assert res
    res = interpret(f, [0])
    assert not res

def test_cast_adr_to_ptr():
    from pypy.rpython.memory.test.test_llinterpsim import interpret
    S = lltype.GcStruct("S", ("x", lltype.Signed))
    Sptr = lltype.Ptr(S)
    def f():
        s1 = lltype.malloc(S)
        adr = cast_ptr_to_adr(s1)
        s2 = cast_adr_to_ptr(adr, Sptr)
        return s1 == s2
    res = interpret(f, [])
    assert res

def test_cast_adr_to_int():
    from pypy.rpython.memory.test.test_llinterpsim import interpret
    S = lltype.GcStruct("S", ("x", lltype.Signed))
    Sptr = lltype.Ptr(S)
    def f():
        s1 = lltype.malloc(S)
        adr = cast_ptr_to_adr(s1)
        i = cast_adr_to_int(adr)
        i2 = lltype.cast_ptr_to_int(s1)
        return i == i2
    assert f()
    res = interpret(f, [])
    assert res

def test_fakeaccessor():
    S = lltype.GcStruct("S", ("x", lltype.Signed), ("y", lltype.Signed))
    s = lltype.malloc(S)
    s.x = 123
    s.y = 456
    adr = cast_ptr_to_adr(s)
    adr += FieldOffset(S, "y")
    assert adr.signed[0] == 456
    adr.signed[0] = 789
    assert s.y == 789

    A = lltype.GcArray(lltype.Signed)
    a = lltype.malloc(A, 5)
    a[3] = 123
    adr = cast_ptr_to_adr(a)
    assert (adr + ArrayLengthOffset(A)).signed[0] == 5
    assert (adr + ArrayItemsOffset(A)).signed[3] == 123
    (adr + ArrayItemsOffset(A)).signed[3] = 456
    assert a[3] == 456
    adr1000 = (adr + ArrayItemsOffset(A) + ItemOffset(lltype.Signed, 1000))
    assert adr1000.signed[-997] == 456

    A = lltype.GcArray(lltype.Char)
    a = lltype.malloc(A, 5)
    a[3] = '*'
    adr = cast_ptr_to_adr(a)
    assert (adr + ArrayLengthOffset(A)).signed[0] == 5
    assert (adr + ArrayItemsOffset(A)).char[3] == '*'
    (adr + ArrayItemsOffset(A)).char[3] = '+'
    assert a[3] == '+'
    adr1000 = (adr + ArrayItemsOffset(A) + ItemOffset(lltype.Char, 1000))
    assert adr1000.char[-997] == '+'

def test_fakeadr_eq():
    S = lltype.GcStruct("S", ("x", lltype.Signed), ("y", lltype.Signed))
    s = lltype.malloc(S)

    assert cast_ptr_to_adr(s) == cast_ptr_to_adr(s)

    adr1 = cast_ptr_to_adr(s) + FieldOffset(S, "x")
    adr2 = cast_ptr_to_adr(s) + FieldOffset(S, "y")
    adr3 = cast_ptr_to_adr(s) + FieldOffset(S, "y")
    assert adr1 != adr2
    assert adr2 == adr3

    A = lltype.GcArray(lltype.Char)
    a = lltype.malloc(A, 5)
    adr1 = cast_ptr_to_adr(a) + ArrayLengthOffset(A)
    adr2 = cast_ptr_to_adr(a) + ArrayLengthOffset(A)
    assert adr1 == adr2

    adr1 = cast_ptr_to_adr(a) + ArrayItemsOffset(A)
    adr2 = cast_ptr_to_adr(a) + ArrayItemsOffset(A)
    assert adr1 == adr2
    adr2 += ItemOffset(lltype.Char, 0)
    assert adr1 == adr2

    adr1 += ItemOffset(lltype.Char, 2)
    adr2 += ItemOffset(lltype.Char, 3)
    assert adr1 != adr2
    adr2 += ItemOffset(lltype.Char, -1)
    assert adr1 == adr2

def test_cast_subarray_pointer():
    for a in [lltype.malloc(lltype.GcArray(lltype.Signed), 5),
              lltype.malloc(lltype.FixedSizeArray(lltype.Signed, 5),
                            immortal=True)]:
        A = lltype.typeOf(a).TO
        SUBARRAY = lltype.FixedSizeArray(lltype.Signed, 1)
        a[3] = 132
        adr = cast_ptr_to_adr(a) + itemoffsetof(A, 3)
        subarray = cast_adr_to_ptr(adr, lltype.Ptr(SUBARRAY))
        assert subarray[0] == 132
        subarray[0] += 2
        assert a[3] == 134

from pypy.rpython.lltypesystem.llmemory import *
from pypy.rpython.lltypesystem import lltype
import py

def test_simple():
    class C:
        def __init__(self, x):
            self.x = x
    c = C(1)
    a = fakeaddress(c)
    assert a.get() is c
    b = a + FieldOffset('dummy', 'x')
    assert b.get() == 1
    b.set(2)
    assert c.x == 2

def test_composite():
    class C:
        def __init__(self, x):
            self.x = x
    c = C(C(3))
    a = fakeaddress(c)
    assert a.get() is c
    b = a + FieldOffset('dummy', 'x') + FieldOffset('dummy', 'x')
    assert b.get() == 3
    b.set(2)
    assert c.x.x == 2
    
def test_array():
    x = [2, 3, 5, 7, 11]
    a = fakeaddress(x)
    # is there a way to ensure that we add the ArrayItemsOffset ?
    b = a + ArrayItemsOffset('dummy') + ItemOffset('dummy')*3
    assert b.get() == x[3]
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
    from pypy.rpython.lltypesystem import lltype
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
    from pypy.rpython.lltypesystem import lltype
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

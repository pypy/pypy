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
    

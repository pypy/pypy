from pypy.rpython.lltypesystem.llmemory import *

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
    

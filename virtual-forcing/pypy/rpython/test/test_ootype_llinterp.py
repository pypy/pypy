from pypy.rpython.ootypesystem.ootype import *
from pypy.rpython.test.test_llinterp import interpret

def test_simple_field():
    C = Instance("test", ROOT, {'a': (Signed, 3)})
    
    def f():
        c = new(C)
        c.a = 5
        return c.a

    result = interpret(f, [], type_system="ootype")
    assert result == 5

def test_simple_method():
    C = Instance("test", ROOT, {'a': (Signed, 3)})
    M = Meth([], Signed)
    def m_(self):
       return self.a
    m = meth(M, _name="m", _callable=m_)
    addMethods(C, {"m": m})
    
    def f():
        c = new(C)
        return c.m()

    result = interpret(f, [], type_system="ootype")
    assert result == 3

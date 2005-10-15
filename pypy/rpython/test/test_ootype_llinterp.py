from pypy.rpython.ootypesystem.ootype import *
from pypy.rpython.test.test_llinterp import interpret

def test_simple_field():
    C = Instance("test", None, {'a': (Signed, 3)})
    
    def f():
        c = new(C)
        c.a = 5
        return c.a

    result = interpret(f, [], type_system="ootype")
    assert result == 5
 

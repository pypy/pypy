from pypy.rpython.ootype.ootype import *
import py

def test_simple():
    assert typeOf(1) is Signed

def test_simple_class():
    C = Class("test", None, {"a": Signed})

    c = new(C)
    assert typeOf(c) == C
    
    py.test.raises(TypeError, "c.z")
    py.test.raises(TypeError, "c.a = 3.0")

    c.a = 3
    assert c.a == 3

def test_simple_default_class():
    C = Class("test", None, {"a": (Signed, 3)})

    c = new(C)
    assert c.a == 3

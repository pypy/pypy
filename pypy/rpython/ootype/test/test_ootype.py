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

    py.test.raises(TypeError, "Class('test', None, {'a': (Signed, 3.0)})")

def test_simple_null():
    C = Class("test", None, {"a": Signed})

    c = null(C)
    assert typeOf(c) == C

    py.test.raises(RuntimeError, "c.a")

def test_simple_class_field():
    C = Class("test", None, {})

    D = Class("test2", None, {"a": C})
    d = new(D)

    assert typeOf(d.a) == C

    assert d.a == null(C)

def test_simple_recursive_class():
    C = Class("test", None, {})

    addFields(C, {"inst": C})

    c = new(C)
    assert c.inst == null(C)

def test_simple_super():
    C = Class("test", None, {"a": (Signed, 3)})
    D = Class("test2", C, {})

    d = new(D)
    assert d.a == 3

def test_simple_field_shadowing():
    C = Class("test", None, {"a": (Signed, 3)})
    
    py.test.raises(TypeError, """D = Class("test2", C, {"a": (Signed, 3)})""")

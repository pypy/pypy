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

def test_simple_function():
   F = Func([Signed, Signed], Signed)
   def f_(a, b):
       return a+b
   f = func(F, _name="f", _callable=f_)
   assert typeOf(f) == F

   result = f(2, 3)
   assert typeOf(result) == Signed
   assert result == 5

def test_function_args():
   F = Func([Signed, Signed], Signed)
   def f_(a, b):
       return a+b
   f = func(F, _name="f", _callable=f_)

   py.test.raises(TypeError, "f(2.0, 3.0)")
   py.test.raises(TypeError, "f()")
   py.test.raises(TypeError, "f(1, 2, 3)")

def test_class_method():
   M = Meth([Signed], Signed)
   def m_(self, b):
       return self.a + b
   m = meth(M, _name="m", _callable=m_)
   
   C = Class("test", None, {"a": (Signed, 2)}, {"m": m})
   c = new(C)

   assert c.m(3) == 5

   py.test.raises(TypeError, "c.m(3.0)")
   py.test.raises(TypeError, "c.m()")
   py.test.raises(TypeError, "c.m(1, 2, 3)")

def test_class_method_field_clash():
   M = Meth([Signed], Signed)
   def m_(self, b):
       return self.a + b
   m = meth(M, _name="m", _callable=m_)
   
   py.test.raises(TypeError, """Class("test", None, {"a": M})""")

   py.test.raises(TypeError, """Class("test", None, {"m": Signed}, {"m":m})""")

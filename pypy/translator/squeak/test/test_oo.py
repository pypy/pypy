from pypy.tool.udir import udir
from pypy.translator.squeak.gensqueak import GenSqueak
from pypy.translator.translator import TranslationContext
from pypy.rpython.ootypesystem.ootype import *
from pypy import conftest


def build_sqfunc(func, args=[], view=False):
   try: func = func.im_func
   except AttributeError: pass
   t = TranslationContext()
   t.buildannotator().build_types(func, args)
   t.buildrtyper(type_system="ootype").specialize()
   if view or conftest.option.view:
      t.viewcg()
   GenSqueak(udir, t)


C = Instance("test", ROOT, {'a': (Signed, 3)})
M = Meth([Signed], Signed)
def m_(self, b):
   return self.a+b
m = meth(M, _name="m", _callable=m_)
addMethods(C, {"m": m})

def test_simple_new():
   def f_new():
      return new(C)
   build_sqfunc(f_new)

def test_simple_meth():
   def f_meth():
      c = new(C)
      return c.m(5)
   build_sqfunc(f_meth)

def test_simple_fields():
   def f_fields():
      c = new(C)
      x = c.a + 1
      c.a = x
      return x
   build_sqfunc(f_fields, view=False)

def test_simple_classof():
   def f_classof():
      c = new(C)
      return classof(c)
   build_sqfunc(f_classof)

def test_simple_runtimenew():
   def f_runtimenew():
      c = new(C)
      m = classof(c)
      i = runtimenew(m)
      return i.a
   build_sqfunc(f_runtimenew)

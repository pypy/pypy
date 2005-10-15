from pypy.tool.udir import udir
from pypy.translator.squeak.gensqueak import GenSqueak
from pypy.translator.translator import Translator
from pypy.rpython.ootypesystem.ootype import *


def build_sqfunc(func, args=[], view=False):
   try: func = func.im_func
   except AttributeError: pass
   t = Translator(func)
   t.annotate(args)
   t.specialize(type_system="ootype")
   t.simplify()
   if view:
      t.viewcg()
   GenSqueak(udir, t)


C = Instance("test", None, {'a': (Signed, 3)})
M = Meth([Signed], Signed)
def m_(self, b):
   return self.a+b
m = meth(M, _name="m", _callable=m_)
addMethods(C, {"m": m})

def f_new():
   return new(C)

def f_meth():
   c = new(C)
   return c.m(5)

def f_fields():
   c = new(C)
   x = c.a + 1
   c.a = x
   return x

def test_simple_new():
   build_sqfunc(f_new)

def test_simple_meth():
   build_sqfunc(f_meth)

def test_simple_fields():
   build_sqfunc(f_fields, view=False)

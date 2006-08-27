
""" BasicExternal testers
"""

import py

from pypy.rpython.ootypesystem.bltregistry import MethodDesc, BasicExternal, described
from pypy.translator.js.test.runtest import compile_function, check_source_contains

class A(BasicExternal):
    @described(retval=3)
    def some_code(self, var="aa"):
        pass

a = A()

class B(object):
    pass

def test_decorator():
    def dec_fun():
        a.some_code("aa")
    
    fun = compile_function(dec_fun, [])
    check_source_contains(fun, "\.some_code")

def test_basicexternal_element():
    def be_fun():
        b = B()
        b.a = a
        b.a.some_code("aa")
    
    fun = compile_function(be_fun, [])
    check_source_contains(fun, "\.some_code")

def test_basicexternal_raise():
    py.test.skip("Raises")
    def raising_fun():
        try:
            b = B()
        except:
            pass
        else:
            return 3

    fun = compile_function(raising_fun, [])
    assert fun() == 3

class C(object):
    @described(retval=3)
    def f(self):
        pass

c = C()

def test_basicexternal_raise_method_call():
    def raising_method_call():
        try:
            c.f()
        except:
            pass

    fun = compile_function(raising_method_call, [])

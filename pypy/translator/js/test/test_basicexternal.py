
""" BasicExternal testers
"""

import py

from pypy.rpython.ootypesystem.bltregistry import MethodDesc, BasicExternal, described
from pypy.translator.js.test.runtest import compile_function, check_source_contains
from pypy.translator.js.tester import schedule_callbacks

class A(BasicExternal):
    @described(retval=int)
    def some_code(self, var="aa"):
        pass

a = A()
a._render_name = 'a'

class B(object):
    pass

def test_decorator():
    def dec_fun():
        a.some_code("aa")
    
    fun = compile_function(dec_fun, [])
    assert check_source_contains(fun, "\.some_code")

def test_basicexternal_element():
    def be_fun():
        b = B()
        b.a = a
        b.a.some_code("aa")
    
    fun = compile_function(be_fun, [])
    assert check_source_contains(fun, "\.some_code")

##def test_basicexternal_raise():
##    #py.test.skip("Constant BasicExternals not implemented")
##    def raising_fun():
##        try:
##            b = B()
##        except:
##            pass
##        else:
##            return 3
##
##    fun = compile_function(raising_fun, [])
##    assert fun() == 3

class EE(BasicExternal):
    @described(retval=int)
    def bb(self):
        pass

ee = EE()
ee._render_name = 'ee'

def test_prebuilt_basicexternal():
    def tt_fun():
        ee.bb()
    
    fun = compile_function(tt_fun, [])
    assert check_source_contains(fun, "EE = ee")

class C(BasicExternal):
    @described(retval=int)
    def f(self):
        pass

c = C()
c._render_name = 'c'

def test_basicexternal_raise_method_call():
    def raising_method_call():
        try:
            c.f()
        except:
            pass

    fun = compile_function(raising_method_call, [])
    assert len(C._methods) == 1
    assert 'f' in C._methods

class D(BasicExternal):
    _fields = {
        'a': {str:str},
        'b': [str],
    }

D._fields['c'] = [D]

d = D()
d._render_name = 'd'

def test_basicexternal_list():
    def getaa(item):
        return d.c[item]
    
    def return_list(i):
        one = getaa(i)
        if one:
            two = getaa(i + 3)
            return two
        return one

    fun2 = compile_function(return_list, [int])

def test_basicextenal_dict():
    def return_dict():
        return d.a

    fun1 = compile_function(return_dict, [])

def test_method_call():
    class Meth(BasicExternal):
        @described(retval=int)
        def meth(self):
            return 8
            
    l = []
    
    def callback(i):
        l.append(i)
    
    meth = Meth()
    meth.meth(callback)
    schedule_callbacks(meth)
    assert l[0] == 8

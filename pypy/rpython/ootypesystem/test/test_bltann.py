
""" Builtin annotation test
"""

import py
from pypy.annotation import model as annmodel
from pypy.objspace.flow.objspace import FlowObjSpace
from pypy.annotation.annrpython import RPythonAnnotator
import exceptions
from pypy.rpython.ootypesystem.bltregistry import BasicExternal, ExternalType, MethodDesc, described
from pypy.rpython.ootypesystem.ootype import Signed, _static_meth, StaticMethod, Void
from pypy.rpython.test.test_llinterp import interpret
from pypy.annotation.signature import annotation
from pypy.translator.translator import TranslationContext

class C(BasicExternal):
    pass

def test_new_bltn():
    def new():
        return C()
    
    a = RPythonAnnotator()
    s = a.build_types(new, [])
    assert s.knowntype is C

class A(BasicExternal):
    _fields = {
        'b' : int,
    }

def test_bltn_attrs():
    def access_attr():
        a = A()
        return a.b
    
    a = RPythonAnnotator()
    s = a.build_types(access_attr, [])
    assert s.knowntype is int

class AA(BasicExternal):
    _fields = {
        'b':int
        }

def test_bltn_set_attr():
    def add_attr():
        a = AA()
        a.b = 3
        return a.b
    
    a = RPythonAnnotator()
    s = a.build_types(add_attr, [])
    assert s.knowntype is int

class B(BasicExternal):
    _fields = {
        'a' : int,
    }
    
    _methods = {
        'm' : MethodDesc([int], int),
    }

def test_bltn_method():
    def access_meth():
        a = B()
        return a.m(3)
    
    a = RPythonAnnotator()
    s = a.build_types(access_meth, [])
    assert s.knowntype is int

glob_b = B()

def test_global():
    def access_global():
        return glob_b.a
    
    a = RPythonAnnotator()
    s = a.build_types(access_global, [])
    assert s.knowntype is int

class CB(BasicExternal):
    _fields = {
        'm': annmodel.SomeGenericCallable(
           args=[], result=annmodel.SomeInteger()),
        }

def some_int():
    return 3
    
def test_flowin():
    def set_callback():
        a = CB()
        a.m = some_int
        return a.m()
    
    a = RPythonAnnotator()
    s = a.build_types(set_callback, [])
    assert s.knowntype is int

class CC(BasicExternal):
    _methods = {
        'some_method' : MethodDesc(
        [annmodel.SomeGenericCallable(args=[
        annmodel.SomeInteger()], result=annmodel.SomeFloat())],
             int)
    }

def test_callback_flowin():
    def some_f(i):
        return 3.2
    
    def set_defined_callback():
        a = CC()
        return a.some_method(some_f)
    
    a = RPythonAnnotator()
    s = a.build_types(set_defined_callback, [])
    assert s.knowntype is int

class CD(BasicExternal):
    _fields = {
        'callback_field' :
        annmodel.SomeGenericCallable([annmodel.SomeInteger()],
                                     annmodel.SomeFloat())
    }

def test_callback_field():
    def callback(x):
        return 8.3 + x
    
    def callback_field():
        a = CD()
        a.callback_field = callback
        return a.callback_field
    
    a = RPythonAnnotator()
    s = a.build_types(callback_field, [])
    assert isinstance(s, annmodel.SomeGenericCallable)
    assert a.translator._graphof(callback)

def test_callback_field_bound_method():
    py.test.skip("needs an rtyping hack to help the js backend "
                 "or generalized bound methods support in many places")
    class A:
        def x(self, i):
            return float(i)

    aa = A()

    def callback(x):
        return 8.3 + x

    def callback_field(i):
        a = CD()
        if i:
            a.callback_field = aa.x
        else:
            a.callback_field = callback
        return a.callback_field(i+1)
    
    res = interpret(callback_field, [1], type_system="ootype")
    assert res == 2.0
    assert isinstance(res, float)
    res = interpret(callback_field, [0], type_system="ootype")
    assert res == 8.3

def test_mixed_classes():
    from pypy.rpython.extfunc import register_external
    class One(BasicExternal):
        pass

    class Two(One):
        pass

    def g(one):
        return 3
    register_external(g, args=[One], result=int)
    
    def f(x):
        if x:
            return g(One())
        return g(Two())

    t = TranslationContext()
    a = t.buildannotator()
    s = a.build_types(f, [bool])
    a.simplify()
    typer = t.buildrtyper(type_system="ootype")
    typer.specialize()
    #res = interpret(f, [True], type_system="ootype")

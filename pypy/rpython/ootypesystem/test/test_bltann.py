
""" Builtin annotation test
"""

from pypy.annotation import model as annmodel
from pypy.objspace.flow import FlowObjSpace
from pypy.annotation.annrpython import RPythonAnnotator
import exceptions
from pypy.rpython.ootypesystem.bltregistry import BasicExternal, ExternalType
from pypy.rpython.ootypesystem.ootype import Signed, _static_meth, StaticMethod, Void
from pypy.rpython.test.test_llinterp import interpret

class C(BasicExternal):
    pass

def test_new_bltn():
    def new():
        return C()
    
    a = RPythonAnnotator()
    s = a.build_types(new, [])
    assert isinstance(s.knowntype, ExternalType)
    assert s.knowntype._class_ is C

class A(BasicExternal):
    _fields = {
        'b' : 3,
    }

def test_bltn_attrs():
    def access_attr():
        a = A()
        return a.b
    
    a = RPythonAnnotator()
    s = a.build_types(access_attr, [])
    assert s.knowntype is int

class AA(BasicExternal):
    pass

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
        'a' : 32,
    }
    
    _methods = {
        'm' : ([1],2),
    }

def test_bltn_method():
    def access_meth():
        a = B()
        return a.m()
    
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
    pass

def some_int():
    return 3
    
def test_flowin():
    #py.test.skip("Can we assume that it might work?")
    def set_callback():
        a = CB()
        a.m = some_int
        return a.m()
    
    a = RPythonAnnotator()
    s = a.build_types(set_callback, [])
    assert s.knowntype is int


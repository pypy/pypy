
""" Builtin annotation test
"""

from pypy.annotation import model as annmodel
from pypy.objspace.flow import FlowObjSpace
from pypy.annotation.annrpython import RPythonAnnotator
import exceptions
from pypy.rpython.ootypesystem.bltregistry import BasicExternal, ExternalType
from pypy.rpython.ootypesystem.ootype import Signed

class C(BasicExternal):
    pass

def test_new_bltn():
    def new():
        return C()
    
    a = RPythonAnnotator()
    s = a.build_types(new, [])
    assert isinstance(s.ootype, ExternalType)
    assert s.ootype._class_ is C

class A(BasicExternal):
    _fields = {
        'b' : Signed,
    }

def test_bltn_attrs():
    def access_attr():
        a = A()
        a.b = 3
        return a.b
    
    a = RPythonAnnotator()
    s = a.build_types(access_attr, [])
    assert s.knowntype is int

class B(BasicExternal):
    _fields = {
        'a' : Signed,
    }
    
    _methods = {
        'm' : ([Signed],Signed),
    }

def test_bltn_method():
    def access_meth():
        a = B()
        return a.m()
    
    a = RPythonAnnotator()
    s = a.build_types(access_meth, [])
    assert s.knowntype is int


""" Test of non-constant constant.
"""

from pypy.rlib.nonconst import NonConstant

from pypy.objspace.flow.objspace import FlowObjSpace
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.conftest import option
from pypy.annotation.model import SomeInstance

def test_nonconst():
    def nonconst_f():
        a = NonConstant(3)
        return a
    
    a = RPythonAnnotator()
    s = a.build_types(nonconst_f, [])
    assert s.knowntype is int
    assert not hasattr(s, 'const')
    #rtyper = a.translator.buildrtyper(type_system="ootype")
    #rtyper.specialize()
    

def test_nonconst_list():
    def nonconst_l():
        a = NonConstant([1, 2, 3])
        return a[0]
    
    a = RPythonAnnotator()
    s = a.build_types(nonconst_l, [])
    assert s.knowntype is int
    assert not hasattr(s, 'const')

def test_nonconst_instance():
    class A:
        pass
    a = A()
    
    def nonconst_i():
        return NonConstant(a)

    a = RPythonAnnotator()
    s = a.build_types(nonconst_i, [])
    rtyper = a.translator.buildrtyper(type_system="ootype")
    rtyper.specialize()
    if option.view:
        a.translator.view()
    assert isinstance(s, SomeInstance)

def test_bool_nonconst():
    def fn():
        return bool(NonConstant(False))
    
    assert not fn()
    
    a = RPythonAnnotator()
    s = a.build_types(fn, [])
    assert s.knowntype is bool
    assert not hasattr(s, 'const')

    rtyper = a.translator.buildrtyper(type_system="ootype")
    rtyper.specialize()
    if option.view:
        a.translator.view()

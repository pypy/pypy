import py

##py.test.skip('In progress at PyCon')

from pypy.rpython.extregistry import EXT_REGISTRY_BY_VALUE, EXT_REGISTRY_BY_TYPE
from pypy.rpython.extregistry import register_func, register_type
from pypy.rpython.extregistry import register_metatype
from pypy.annotation import model as annmodel
from pypy.annotation.annrpython import RPythonAnnotator

def dummy(): 
    raiseNameError

register_func(dummy, annmodel.SomeInteger())

def test_call_dummy():
    def func():
        x = dummy()
        return x
    
    a = RPythonAnnotator()
    s = a.build_types(func, [])
    assert isinstance(s, annmodel.SomeInteger)

def test_callable_annotation():
    def dummy2():
        raiseNameError
    
    def return_annotation():
        return annmodel.SomeInteger()
    
    register_func(dummy2, return_annotation)
    
    def func():
        x = dummy2()
        return x
    
    a = RPythonAnnotator()
    s = a.build_types(func, [])
    assert isinstance(s, annmodel.SomeInteger)

def test_register_type():
    class DummyType(object):
        pass
    
    dummy_type = DummyType()
    
    def func():
        return dummy_type
    
    register_type(DummyType, annmodel.SomeInteger())
    
    a = RPythonAnnotator()
    s = a.build_types(func, [])
    assert isinstance(s, annmodel.SomeInteger)

def test_register_metatype():
    class MetaType(type):
        pass
    
    class RealClass(object):
        __metaclass__ = MetaType
    
    real_class = RealClass()
    
    def func():
        return real_class
    
    def get_annotation(t):
        assert t is RealClass
        return annmodel.SomeInteger()
    
    register_metatype(MetaType, get_annotation)
    
    a = RPythonAnnotator()
    s = a.build_types(func, [])
    assert isinstance(s, annmodel.SomeInteger)

def test_register_metatype_2():
    class MetaType(type):
        pass
    
    class RealClass(object):
        __metaclass__ = MetaType
    
    def func(real_class):
        return real_class
    
    def get_annotation(t):
        assert t is RealClass
        return annmodel.SomeInteger()
    
    register_metatype(MetaType, get_annotation)
    
    a = RPythonAnnotator()
    s = a.build_types(func, [RealClass])
    assert isinstance(s, annmodel.SomeInteger)
    
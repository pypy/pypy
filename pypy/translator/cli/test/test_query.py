import py
from pypy.translator.cli import query
from pypy.translator.cli.dotnet import CLR, CliNamespace

def setup_module(module):
    from pypy.translator.cli.query import load_assembly, mscorlib
    load_assembly(mscorlib)

def test_load_assembly():
    query.load_assembly(query.mscorlib)
    assert 'System.Math' in query.Types
    assert 'System.Collections.ArrayList' in query.Types

def test_namespaces():
    assert CLR.System._name == 'System'
    assert CLR.System.Collections._name == 'System.Collections'
    py.test.raises(AttributeError, getattr, CLR, 'Foo')
    py.test.raises(AttributeError, getattr, CLR.System, 'Foo')

def test_CLR_getattr():
    System = CLR.System
    assert isinstance(System, CliNamespace)
    assert System._name == 'System'
    assert hasattr(CLR, 'System')

def test_static_fields():
    desc = query.get_class_desc('System.Reflection.Emit.OpCodes')
    assert ('Add', 'System.Reflection.Emit.OpCode') in desc.StaticFields

def test_System_Object():
    Object = CLR.System.Object
    assert Object._name == '[mscorlib]System.Object'
    assert 'Equals' in Object._static_methods
    assert 'ToString' in Object._INSTANCE._methods

def test_array():
    cls = query.get_cli_class('System.Object[]')
    assert cls._INSTANCE._isArray
    assert cls._INSTANCE._ELEMENT is CLR.System.Object._INSTANCE

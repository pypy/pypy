from pypy.translator.cli import query
from pypy.translator.cli.dotnet import CLR, CliNamespace

def test_load_namespace_simple():
    query.load_class_or_namespace('System')
    assert isinstance(CLR.System, CliNamespace)
    assert CLR.System._name == 'System'

def test_load_namespace_complex():
    query.load_class_or_namespace('System.Collections')
    assert isinstance(CLR.System, CliNamespace)
    assert isinstance(CLR.System.Collections, CliNamespace)
    assert CLR.System.Collections._name == 'System.Collections'

def test_CLR_getattr():
    System = CLR.System
    assert isinstance(System, CliNamespace)
    assert System._name == 'System'
    assert hasattr(CLR, 'System')

def test_System_Object():
    Object = CLR.System.Object
    assert Object._name == '[mscorlib]System.Object'
    assert 'Equals' in Object._static_methods
    assert 'ToString' in Object._INSTANCE._methods

def test_array():
    query.load_class_or_namespace('System.Object[]')
    cls = query.ClassCache['System.Object[]']
    assert cls._INSTANCE._isArray
    assert cls._INSTANCE._ELEMENT is CLR.System.Object._INSTANCE

def test_savedesc():
    from pypy.tool.udir import udir
    CLR.System.Object # force System.Object to be loaded
    olddesc = query.Descriptions.copy()
    tmpfile = str(udir.join('descriptions'))
    query.savedesc(tmpfile)
    query.Descriptions.clear()
    query.loaddesc(tmpfile)
    assert query.Descriptions == olddesc

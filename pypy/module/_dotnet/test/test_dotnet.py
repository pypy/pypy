from pypy.conftest import gettestobjspace
import os

class AppTestDotnet:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_dotnet',))
        cls.space = space

    def test_cliobject(self):
        import _dotnet
        obj = _dotnet._CliObject_internal('System.Collections.ArrayList')
        max_index = obj.call_method('Add', [42])
        assert max_index == 0

    def test_ArrayList(self):
        import _dotnet
        obj = _dotnet.ArrayList()
        obj.Add(42)
        obj.Add(43)
        total = obj.get_Item(0) + obj.get_Item(1)
        assert total == 42+43

    def test_ArrayList_error(self):
        import _dotnet
        obj = _dotnet.ArrayList()
        raises(StandardError, obj.get_Item, 0)

    def test_float_conversion(self):
        import _dotnet
        obj = _dotnet.ArrayList()
        obj.Add(42.0)
        item = obj.get_Item(0)
        assert isinstance(item, float)

    def test_getitem(self):
        import _dotnet
        obj = _dotnet.ArrayList()
        obj.Add(42)
        assert obj[0] == 42

    def test_unboundmethod(self):
        import _dotnet
        obj = _dotnet.ArrayList()
        _dotnet.ArrayList.Add(obj, 42)
        assert obj.get_Item(0) == 42

    def test_unboundmethod_typeerror(self):
        import _dotnet
        raises(TypeError, _dotnet.ArrayList.Add)
        raises(TypeError, _dotnet.ArrayList.Add, 0)

    def test_overload(self):
        import _dotnet
        obj = _dotnet.ArrayList()
        for i in range(10):
            obj.Add(i)
        assert obj.IndexOf(7) == 7
        assert obj.IndexOf(7, 0, 5) == -1

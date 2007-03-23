from pypy.conftest import gettestobjspace

class AppTestDotnet:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('clr',))
        cls.space = space

    def test_cliobject(self):
        import clr
        obj = clr._CliObject_internal('System.Collections.ArrayList', [])
        max_index = obj.call_method('Add', [42])
        assert max_index == 0

    def test_cache(self):
        import clr
        ArrayList = clr.load_cli_class('System.Collections', 'ArrayList')
        ArrayList2 = clr.load_cli_class('System.Collections', 'ArrayList')
        assert ArrayList is ArrayList2

    def test_ArrayList(self):
        import clr
        ArrayList = clr.load_cli_class('System.Collections', 'ArrayList')
        obj = ArrayList()
        obj.Add(42)
        obj.Add(43)
        total = obj.get_Item(0) + obj.get_Item(1)
        assert total == 42+43

    def test_ArrayList_error(self):
        import clr
        ArrayList = clr.load_cli_class('System.Collections', 'ArrayList')
        obj = ArrayList()
        raises(StandardError, obj.get_Item, 0)

    def test_float_conversion(self):
        import clr
        ArrayList = clr.load_cli_class('System.Collections', 'ArrayList')
        obj = ArrayList()
        obj.Add(42.0)
        item = obj.get_Item(0)
        assert isinstance(item, float)

    def test_getitem(self):
        import clr
        ArrayList = clr.load_cli_class('System.Collections', 'ArrayList')
        obj = ArrayList()
        obj.Add(42)
        assert obj[0] == 42

    def test_property(self):
        import clr
        ArrayList = clr.load_cli_class('System.Collections', 'ArrayList')
        obj = ArrayList()
        obj.Add(42)
        assert obj.Count == 1
        obj.Capacity = 10
        assert obj.Capacity == 10

    def test_unboundmethod(self):
        import clr
        ArrayList = clr.load_cli_class('System.Collections', 'ArrayList')
        obj = ArrayList()
        ArrayList.Add(obj, 42)
        assert obj.get_Item(0) == 42

    def test_unboundmethod_typeerror(self):
        import clr
        ArrayList = clr.load_cli_class('System.Collections', 'ArrayList')
        raises(TypeError, ArrayList.Add)
        raises(TypeError, ArrayList.Add, 0)

    def test_overload(self):
        import clr
        ArrayList = clr.load_cli_class('System.Collections', 'ArrayList')
        obj = ArrayList()
        for i in range(10):
            obj.Add(i)
        assert obj.IndexOf(7) == 7
        assert obj.IndexOf(7, 0, 5) == -1

    def test_wrong_overload(self):
        import clr
        Math = clr.load_cli_class('System', 'Math')
        raises(TypeError, Math.Abs, "foo")

    def test_staticmethod(self):
        import clr
        Math = clr.load_cli_class('System', 'Math')
        res = Math.Abs(-42)
        assert res == 42
        assert type(res) is int
        res = Math.Abs(-42.0)
        assert res == 42.0
        assert type(res) is float

    def test_constructor_args(self):
        import clr
        ArrayList = clr.load_cli_class('System.Collections', 'ArrayList')
        obj = ArrayList(42)
        assert obj.Capacity == 42

    def test_None_as_null(self):
        import clr
        ArrayList = clr.load_cli_class('System.Collections', 'ArrayList')
        Hashtable = clr.load_cli_class('System.Collections', 'Hashtable')
        x = ArrayList()
        x.Add(None)
        assert x[0] is None
        y = Hashtable()
        assert y["foo"] is None

    def test_pass_opaque_arguments(self):
        import clr
        ArrayList = clr.load_cli_class('System.Collections', 'ArrayList')
        class Foo:
            pass
        obj = Foo()
        x = ArrayList()
        x.Add(obj)
        obj2 = x[0]
        assert obj is obj2

    def test_string_wrapping(self):
        import clr
        ArrayList = clr.load_cli_class('System.Collections', 'ArrayList')
        x = ArrayList()
        x.Add("bar")
        s = x[0]
        assert s == "bar"

    def test_static_property(self):
        import clr
        import os
        Environment = clr.load_cli_class('System', 'Environment')
        assert Environment.CurrentDirectory == os.getcwd()
        Environment.CurrentDirectory == '/'
        assert Environment.CurrentDirectory == os.getcwd()

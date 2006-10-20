from pypy.annotation.annrpython import RPythonAnnotator
from pypy.annotation import model as annmodel
from pypy.translator.cli.test.runtest import CliTest
from pypy.translator.cli.dotnet import SomeCliClass, SomeCliStaticMethod,\
     NativeInstance, Math, ArrayList, StringBuilder

class TestDotnet(CliTest):

    def test_class_ann(self):
        def fn():
            return Math
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, SomeCliClass)
        assert s.const is Math

    def test_staticmeth_ann(self):
        def fn():
            return Math.Abs
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, SomeCliStaticMethod)
        assert s.cli_class is Math
        assert s.meth_name == 'Abs'

    def test_staticmeth_call_ann(self):
        def fn1():
            return Math.Abs(42)
        def fn2():
            return Math.Abs(42.5)
        a = RPythonAnnotator()
        assert type(a.build_types(fn1, [])) is annmodel.SomeInteger
        assert type(a.build_types(fn2, [])) is annmodel.SomeFloat

    def test_new_instance_ann(self):
        def fn():
            return ArrayList()
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeOOInstance)
        assert isinstance(s.ootype, NativeInstance)
        assert s.ootype._name == '[mscorlib]System.Collections.ArrayList'

    def test_staticmeth_call(self):
        def fn(x):
            return Math.Abs(x)
        assert self.interpret(fn, [-42]) == 42

    def test_staticmeth_overload(self):
        def fn(x, y):
            return Math.Abs(x), Math.Abs(y)
        res = self.interpret(fn, [-42, -42.5])
        assert res.item0 == 42
        assert res.item1 == 42.5

    def test_method_call(self):
        def fn():
            x = ArrayList()
            x.Add("foo")
            x.Add("bar")
            return x.get_Count()
        assert self.interpret(fn, []) == 2

    def test_tostring(self):
        def fn():
            x = StringBuilder()
            x.Append("foo").Append("bar")
            return x.ToString()
        res = self.ll_to_string(self.interpret(fn, []))
        assert res == 'foobar'

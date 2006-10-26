import py
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.annotation import model as annmodel
from pypy.rpython.ootypesystem import ootype
from pypy.translator.cli.test.runtest import CliTest
from pypy.translator.cli.dotnet import SomeCliClass, SomeCliStaticMethod,\
     NativeInstance, CLR, box, unbox

Math = CLR.System.Math
ArrayList = CLR.System.Collections.ArrayList
StringBuilder = CLR.System.Text.StringBuilder

class TestDotnetAnnotation(object):

    def test_class(self):
        def fn():
            return Math
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, SomeCliClass)
        assert s.const is Math

    def test_staticmeth(self):
        def fn():
            return Math.Abs
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, SomeCliStaticMethod)
        assert s.cli_class is Math
        assert s.meth_name == 'Abs'

    def test_staticmeth_call(self):
        def fn1():
            return Math.Abs(42)
        def fn2():
            return Math.Abs(42.5)
        a = RPythonAnnotator()
        assert type(a.build_types(fn1, [])) is annmodel.SomeInteger
        assert type(a.build_types(fn2, [])) is annmodel.SomeFloat

    def test_new_instance(self):
        def fn():
            return ArrayList()
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeOOInstance)
        assert isinstance(s.ootype, NativeInstance)
        assert s.ootype._name == '[mscorlib]System.Collections.ArrayList'

    def test_box(self):
        def fn():
            return box(42)
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeOOInstance)
        assert s.ootype._name == '[mscorlib]System.Object'

    def test_unbox(self):
        def fn():
            x = box(42)
            return unbox(x, ootype.Signed)
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeInteger)

class TestDotnetRtyping(CliTest):
    def _skip_pythonnet(self):
        pass

    def test_staticmeth_call(self):
        def fn(x):
            return Math.Abs(x)
        assert self.interpret(fn, [-42]) == 42

    def test_staticmeth_overload(self):
        self._skip_pythonnet()
        def fn(x, y):
            return Math.Abs(x), Math.Abs(y)
        res = self.interpret(fn, [-42, -42.5])
        item0, item1 = self.ll_to_tuple(res)
        assert item0 == 42
        assert item1 == 42.5

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
    
    def test_box(self):
        def fn():
            x = ArrayList()
            x.Add(box(42))
            x.Add(box('Foo'))
            return x.get_Count()
        assert self.interpret(fn, []) == 2

    def test_unbox(self):
        def fn():
            x = ArrayList()
            x.Add(box(42))
            return unbox(x.get_Item(0), ootype.Signed)
        assert self.interpret(fn, []) == 42

    def test_unbox_string(self):
        def fn():
            x = ArrayList()
            x.Add(box('foo'))
            return unbox(x.get_Item(0), ootype.String)
        assert self.interpret(fn, []) == 'foo'


class TestPythonnet(TestDotnetRtyping):
    # don't interpreter functions but execute them directly through pythonnet
    def interpret(self, f, args):
        return f(*args)

    def _skip_pythonnet(self):
        py.test.skip('Pythonnet bug!')


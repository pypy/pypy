import py
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.annotation import model as annmodel
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.ootype import meth, Meth, Char, Signed, Float, String,\
     ROOT, overload, Instance, new
from pypy.translator.cli.test.runtest import CliTest
from pypy.translator.cli.dotnet import SomeCliClass, SomeCliStaticMethod,\
     NativeInstance, CLR, box, unbox, OverloadingResolver, Null, NullType

System = CLR.System
Math = CLR.System.Math
ArrayList = CLR.System.Collections.ArrayList

class TestDotnetAnnotation(object):

    def test_overloaded_meth_string(self):
        C = Instance("test", ROOT, {},
                     {'foo': overload(meth(Meth([Char], Signed)),
                                      meth(Meth([String], Float)),
                                      resolver=OverloadingResolver),
                      'bar': overload(meth(Meth([Signed], Char)),
                                      meth(Meth([Float], String)),
                                      resolver=OverloadingResolver)})
        def fn1():
            return new(C).foo('a')
        def fn2():
            return new(C).foo('aa')
        def fn3(x):
            return new(C).bar(x)
        a = RPythonAnnotator()
        assert isinstance(a.build_types(fn1, []), annmodel.SomeInteger)
        assert isinstance(a.build_types(fn2, []), annmodel.SomeFloat)
        assert isinstance(a.build_types(fn3, [int]), annmodel.SomeChar)
        assert isinstance(a.build_types(fn3, [float]), annmodel.SomeString)

    def test_class(self):
        def fn():
            return Math
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, SomeCliClass)
        assert s.const is Math

    def test_fullname(self):
        def fn():
            return CLR.System.Math
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

    def test_array(self):
        def fn():
            x = ArrayList()
            return x.ToArray()
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeOOInstance)
        assert s.ootype._isArray
        assert s.ootype._ELEMENT._name == '[mscorlib]System.Object'

    def test_array_getitem(self):
        def fn():
            x = ArrayList().ToArray()
            return x[0]
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeOOInstance)
        assert s.ootype._name == '[mscorlib]System.Object'

    def test_Null(self):
        def fn():
            return Null
        a = RPythonAnnotator()
        s = a.build_types(fn, [])
        assert s.ootype is NullType

class TestDotnetRtyping(CliTest):
    def _skip_pythonnet(self, msg):
        pass

    def test_staticmeth_call(self):
        def fn(x):
            return Math.Abs(x)
        assert self.interpret(fn, [-42]) == 42

    def test_staticmeth_overload(self):
        self._skip_pythonnet('Pythonnet bug!')
        def fn(x, y):
            return Math.Abs(x), Math.Abs(y)
        res = self.interpret(fn, [-42, -42.5])
        item0, item1 = self.ll_to_tuple(res)
        assert item0 == 42
        assert item1 == 42.5

    def test_tostring(self):
        StringBuilder = CLR.System.Text.StringBuilder
        def fn():
            x = StringBuilder()
            x.Append(box("foo")).Append(box("bar"))
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

    def test_whitout_box(self):
        def fn():
            x = ArrayList()
            x.Add(42) # note we have forgot box()
        py.test.raises(TypeError, self.interpret, fn, [])

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

    def test_exception(self):
        py.test.skip("It doesn't work so far")
        def fn():
            x = ArrayList()
            try:
                x.get_Item(0)
            except System.ArgumentOutOfRangeException:
                return 42
            else:
                return 43
        assert self.interpret(fn, []) == 42

    def test_array(self):
        def fn():
            x = ArrayList()
            x.Add(box(42))
            array = x.ToArray()
            return unbox(array[0], ootype.Signed)
        assert self.interpret(fn, []) == 42

    def test_Null(self):
        self._skip_pythonnet("Null support not yet completed'")
        def fn():
            return System.Object.Equals(Null, Null)
        assert self.interpret(fn, []) == True

    def test_Null_bound_method(self):
        self._skip_pythonnet("Null support not yet completed'")
        def fn():
            x = ArrayList()
            x.Add(Null)
            return x.get_Item(0)
        # a bit of explanation for the result: after IL has been
        # generated there is no distinction between dotnet.Null and
        # None, because both are rendered as the CLI 'null' value. So
        # interpret returns 'None', as it has always done.
        assert self.interpret(fn, []) is None

class TestPythonnet(TestDotnetRtyping):
    # don't interpreter functions but execute them directly through pythonnet
    def interpret(self, f, args):
        return f(*args)

    def _skip_pythonnet(self, msg):
        py.test.skip(msg)

    def test_whitout_box(self):
        pass # it makes sense only during translation
    


import autopath
from pypy.tool import test 
import unittest
from pypy.interpreter.function import Function, Method
from pypy.interpreter.pycode import PyCode


class AppTestFunctionIntrospection(test.AppTestCase):
    def test_attributes(self):
        def f(): pass
        self.assert_(hasattr(f, 'func_code'))
        self.assertEquals(f.func_defaults, None)
        self.assertEquals(f.func_dict, {})
        self.assertEquals(type(f.func_globals), dict)
        self.assertEquals(f.func_closure, None)
        self.assertEquals(f.func_doc, None)
        self.assertEquals(f.func_name, 'f')

    def test_underunder_attributes(self):
        def f(): pass
        self.assertEquals(f.__name__, 'f')
        self.assertEquals(f.__doc__, None)
        self.assert_(f.__name__ is f.func_name)
        self.assert_(f.__doc__ is f.func_doc)
        self.assert_(f.__dict__ is f.func_dict)
        #XXX self.assert_(hasattr(f, '__class__'))

class AppTestFunction(test.AppTestCase):
    def test_simple_call(self):
        def func(arg1, arg2):
            return arg1, arg2
        res = func(23,42)
        self.assertEquals(res[0], 23)
        self.assertEquals(res[1], 42)

    def test_simple_varargs(self):
        def func(arg1, *args):
            return arg1, args
        res = func(23,42)
        self.assertEquals(res[0], 23)
        self.assertEquals(res[1], (42,))

    def test_simple_kwargs(self):
        def func(arg1, **kwargs):
            return arg1, kwargs
        res = func(23, value=42)
        self.assertEquals(res[0], 23)
        self.assertEquals(res[1], {'value': 42})

    def test_kwargs_sets_wrong_positional_raises(self):
        def func(arg1):
            pass
        self.assertRaises(TypeError, func, arg2=23)

    def test_kwargs_sets_positional(self):
        def func(arg1):
            return arg1
        res = func(arg1=42)
        self.assertEquals(res, 42)

    def test_kwargs_sets_positional_mixed(self):
        def func(arg1, **kw):
            return arg1, kw
        res = func(arg1=42, something=23)
        self.assertEquals(res[0], 42)
        self.assertEquals(res[1], {'something': 23})

    def test_kwargs_sets_positional_mixed(self):
        def func(arg1, **kw):
            return arg1, kw
        res = func(arg1=42, something=23)
        self.assertEquals(res[0], 42)
        self.assertEquals(res[1], {'something': 23})

    def test_kwargs_sets_positional_twice(self):
        def func(arg1, **kw):
            return arg1, kw
        self.assertRaises(
            TypeError, func, 42, {'arg1': 23})

    def test_default_arg(self):
        def func(arg1,arg2=42):
            return arg1, arg2
        res = func(arg1=23)
        self.assertEquals(res[0], 23)
        self.assertEquals(res[1], 42)

    def test_defaults_keyword_overrides(self):
        def func(arg1=42, arg2=23):
            return arg1, arg2
        res = func(arg1=23)
        self.assertEquals(res[0], 23)
        self.assertEquals(res[1], 23)

    def test_defaults_keyword_override_but_leaves_empty_positional(self):
        def func(arg1,arg2=42):
            return arg1, arg2
        self.assertRaises(TypeError, func, arg2=23)

    def test_kwargs_disallows_same_name_twice(self):
        def func(arg1, **kw):
            return arg1, kw
        self.assertRaises(TypeError, func, 42, **{'arg1': 23})


class TestMethod(test.IntTestCase):
    def setUp(self):
        self.space = test.objspace()
        def c(self, bar):
            return bar
        code = PyCode()._from_code(c.func_code)
        self.fn = Function(self.space, code)
        
    def test_get(self):
        class X(object):
            fn = self.fn
        x = X()
        meth = x.fn
        self.failUnless(isinstance(meth, Method))

    def test_call(self):
        class X(object):
            fn = self.fn
        x = X()
        self.assertEquals(x.fn(42), 42)

    def test_fail_call(self):
        class X(object):
            fn = self.fn
        x = X()
        self.assertRaises_w(self.space.w_TypeError, x.fn, "spam", "egg")


if __name__ == '__main__':
    test.main()

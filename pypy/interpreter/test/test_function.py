
import autopath
from pypy.tool import testit 
import unittest
from pypy.interpreter.function import Function, Method
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.argument import Arguments


class AppTestFunctionIntrospection(testit.AppTestCase):
    def test_attributes(self):
        def f(): pass
        self.assert_(hasattr(f, 'func_code'))
        self.assertEquals(f.func_defaults, None)
        self.assertEquals(f.func_dict, {})
        self.assertEquals(type(f.func_globals), dict)
        #self.assertEquals(f.func_closure, None)  XXX
        self.assertEquals(f.func_doc, None)
        self.assertEquals(f.func_name, 'f')

    def test_code_is_ok(self):
        def f(): pass
        self.assert_(not hasattr(f.func_code, '__dict__'))

    def test_underunder_attributes(self):
        def f(): pass
        self.assertEquals(f.__name__, 'f')
        self.assertEquals(f.__doc__, None)
        self.assert_(f.__name__ == f.func_name)
        self.assert_(f.__doc__ == f.func_doc)
        self.assert_(f.__dict__ is f.func_dict)
        self.assert_(hasattr(f, '__class__'))

    def test_write_doc(self):
        def f(): "hello"
        self.assertEquals(f.__doc__, 'hello')
        f.__doc__ = 'good bye'
        self.assertEquals(f.__doc__, 'good bye')
        del f.__doc__
        self.assertEquals(f.__doc__, None)

    def test_write_func_doc(self):
        def f(): "hello"
        self.assertEquals(f.func_doc, 'hello')
        f.func_doc = 'good bye'
        self.assertEquals(f.func_doc, 'good bye')
        del f.func_doc
        self.assertEquals(f.func_doc, None)

class AppTestFunction(testit.AppTestCase):
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

    def test_kwargs_confusing_name(self):
        def func(self):    # 'self' conflicts with the interp-level
            return self*7  # argument to call_function()
        res = func(self=6)
        self.assertEquals(res, 42)

    def test_get(self):
        def func(self): return self
        obj = object()
        meth = func.__get__(obj, object)
        self.assertEquals(meth(), obj)

    def test_call_builtin(self):
        s = 'hello'
        self.assertRaises(TypeError, len)
        self.assertEquals(len(s), 5)
        self.assertRaises(TypeError, len, s, s)
        self.assertRaises(TypeError, len, s, s, s)
        self.assertEquals(len(*[s]), 5)
        self.assertEquals(len(s, *[]), 5)
        self.assertRaises(TypeError, len, some_unknown_keyword=s)
        self.assertRaises(TypeError, len, s, some_unknown_keyword=s)
        self.assertRaises(TypeError, len, s, s, some_unknown_keyword=s)

class AppTestMethod(testit.AppTestCase):

    def test_get(self):
        def func(self): return self
        class Object(object): pass
        obj = Object()
        # Create bound method from function
        obj.meth = func.__get__(obj, Object)
        self.assertEquals(obj.meth(), obj)
        # Create bound method from method
        meth2 = obj.meth.__get__(obj, Object)
        self.assertEquals(meth2(), obj)

    def test_get_get(self):
        # sanxiyn's test from email
        def m(self): return self
        class C: pass
        class D(C): pass
        C.m = m
        D.m = C.m
        c = C()
        self.assertEquals(c.m(), c)
        d = D()
        self.assertEquals(d.m(), d)

class TestMethod(testit.IntTestCase):
    def setUp(self):
        self.space = testit.objspace()
        def c(self, bar):
            return bar
        code = PyCode()._from_code(c.func_code)
        self.fn = Function(self.space, code)
        
    def test_get(self):
        space = self.space
        w_meth = self.fn.descr_function_get(space.wrap(5), space.type(space.wrap(5)))
        meth = space.unwrap(w_meth)
        self.failUnless(isinstance(meth, Method))

    def test_call(self):
        space = self.space
        w_meth = self.fn.descr_function_get(space.wrap(5), space.type(space.wrap(5)))
        meth = space.unwrap(w_meth)
        w_result = meth.call_args(Arguments(space, [space.wrap(42)]))
        self.assertEquals(space.unwrap(w_result), 42)

    def test_fail_call(self):
        space = self.space
        w_meth = self.fn.descr_function_get(space.wrap(5), space.type(space.wrap(5)))
        meth = space.unwrap(w_meth)
        args = Arguments(space, [space.wrap("spam"), space.wrap("egg")])
        self.assertRaises_w(self.space.w_TypeError, meth.call_args, args)

    def test_method_get(self):
        space = self.space
        # Create some function for this test only
        def m(self): return self
        func = Function(space, PyCode()._from_code(m.func_code))
        # Some shorthands
        obj1 = space.wrap(23)
        obj2 = space.wrap(42)
        args = Arguments(space, [])
        # Check method returned from func.__get__()
        w_meth1 = func.descr_function_get(obj1, space.type(obj1))
        meth1 = space.unwrap(w_meth1)
        self.failUnless(isinstance(meth1, Method))
        self.assertEquals(meth1.call_args(args), obj1)
        # Check method returned from method.__get__()
        # --- meth1 is already bound so meth1.__get__(*) is meth1.
        w_meth2 = meth1.descr_method_get(obj2, space.type(obj2))
        meth2 = space.unwrap(w_meth2)
        self.failUnless(isinstance(meth2, Method))
        self.assertEquals(meth2.call_args(args), obj1)
        # Check method returned from unbound_method.__get__()
        w_meth3 = func.descr_function_get(None, space.type(obj2))
        meth3 = space.unwrap(w_meth3)
        w_meth4 = meth3.descr_method_get(obj2, space.w_None)
        meth4 = space.unwrap(w_meth4)
        self.failUnless(isinstance(meth4, Method))
        self.assertEquals(meth4.call_args(args), obj2)
        # Check method returned from unbound_method.__get__()
        # --- with an incompatible class
        w_meth5 = meth3.descr_method_get(space.wrap('hello'), space.w_None)
        self.assert_(space.is_true(space.is_(w_meth5, w_meth3)))

if __name__ == '__main__':
    testit.main()

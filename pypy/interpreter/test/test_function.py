
import autopath
from pypy.tool import test 
import unittest

class ArgParseTest(test.AppTestCase):
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

class ModuleMinimalTest(test.IntTestCase):
    def setUp(self):
        self.space = test.objspace()

    def test_sys_exists(self):
        w_sys = self.space.get_builtin_module('sys')
        self.assert_(self.space.is_true(w_sys))

    def test_import_exists(self):
        space = self.space
        w_builtin = space.get_builtin_module('__builtin__')
        self.assert_(space.is_true(w_builtin))
        w_name = space.wrap('__import__')
        w_import = self.space.getattr(w_builtin, w_name)
        self.assert_(space.is_true(w_import))

    def test_sys_import(self):
        from pypy.interpreter.main import run_string
        run_string('import sys', space=self.space)

if __name__ == '__main__':
    test.main()

        

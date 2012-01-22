
import unittest
from pypy.interpreter import eval
from pypy.interpreter.function import Function, Method, descr_function_get
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.argument import Arguments


class AppTestFunctionIntrospection:
    def test_attributes(self):
        globals()['__name__'] = 'mymodulename'
        def f(): pass
        assert hasattr(f, 'func_code')
        assert f.func_defaults == None
        f.func_defaults = None
        assert f.func_defaults == None
        assert f.func_dict == {}
        assert type(f.func_globals) == dict
        assert f.func_closure is None
        assert f.func_doc == None
        assert f.func_name == 'f'
        assert f.__module__ == 'mymodulename'

    def test_code_is_ok(self):
        def f(): pass
        assert not hasattr(f.func_code, '__dict__')

    def test_underunder_attributes(self):
        def f(): pass
        assert f.__name__ == 'f'
        assert f.__doc__ == None
        assert f.__name__ == f.func_name
        assert f.__doc__ == f.func_doc
        assert f.__dict__ is f.func_dict
        assert f.__code__ is f.func_code
        assert f.__defaults__ is f.func_defaults
        assert hasattr(f, '__class__')

    def test_classmethod(self):
        def f():
            pass
        assert classmethod(f).__func__ is f
        assert staticmethod(f).__func__ is f

    def test_write_doc(self):
        def f(): "hello"
        assert f.__doc__ == 'hello'
        f.__doc__ = 'good bye'
        assert f.__doc__ == 'good bye'
        del f.__doc__
        assert f.__doc__ == None

    def test_write_func_doc(self):
        def f(): "hello"
        assert f.func_doc == 'hello'
        f.func_doc = 'good bye'
        assert f.func_doc == 'good bye'
        del f.func_doc
        assert f.func_doc == None

    def test_write_module(self):
        def f(): "hello"
        f.__module__ = 'ab.c'
        assert f.__module__ == 'ab.c'
        del f.__module__
        assert f.__module__ is None

    def test_new(self):
        def f(): return 42
        FuncType = type(f)
        f2 = FuncType(f.func_code, f.func_globals, 'f2', None, None)
        assert f2() == 42

        def g(x):
            def f():
                return x
            return f
        f = g(42)
        raises(TypeError, FuncType, f.func_code, f.func_globals, 'f2', None, None)

    def test_write_code(self):
        def f():
            return 42
        def g():
            return 41
        assert f() == 42
        assert g() == 41
        raises(TypeError, "f.func_code = 1")
        f.func_code = g.func_code
        assert f() == 41
        def h():
            return f() # a closure
        raises(ValueError, "f.func_code = h.func_code")

    def test_write_code_builtin_forbidden(self):
        def f(*args):
            return 42
            raises(TypeError, "dir.func_code = f.func_code")
            raises(TypeError, "list.append.im_func.func_code = f.func_code")

    def test_set_module_to_name_eagerly(self):
        skip("fails on PyPy but works on CPython.  Unsure we want to care")
        exec '''if 1:
            __name__ = "foo"
            def f(): pass
            __name__ = "bar"
            assert f.__module__ == "foo"''' in {}


class AppTestFunction:
    def test_simple_call(self):
        def func(arg1, arg2):
            return arg1, arg2
        res = func(23,42)
        assert res[0] == 23
        assert res[1] == 42

    def test_simple_call_default(self):
        def func(arg1, arg2=11, arg3=111):
            return arg1, arg2, arg3
        res = func(1)
        assert res[0] == 1
        assert res[1] == 11
        assert res[2] == 111
        res = func(1, 22)
        assert res[0] == 1
        assert res[1] == 22
        assert res[2] == 111
        res = func(1, 22, 333)
        assert res[0] == 1
        assert res[1] == 22
        assert res[2] == 333

        raises(TypeError, func)
        raises(TypeError, func, 1, 2, 3, 4)

    def test_simple_varargs(self):
        def func(arg1, *args):
            return arg1, args
        res = func(23,42)
        assert res[0] == 23
        assert res[1] == (42,)

        res = func(23, *(42,))
        assert res[0] == 23
        assert res[1] == (42,)

    def test_simple_kwargs(self):
        def func(arg1, **kwargs):
            return arg1, kwargs
        res = func(23, value=42)
        assert res[0] == 23
        assert res[1] == {'value': 42}

        res = func(23, **{'value': 42})
        assert res[0] == 23
        assert res[1] == {'value': 42}

    def test_kwargs_sets_wrong_positional_raises(self):
        def func(arg1):
            pass
        raises(TypeError, func, arg2=23)

    def test_kwargs_sets_positional(self):
        def func(arg1):
            return arg1
        res = func(arg1=42)
        assert res == 42

    def test_kwargs_sets_positional_mixed(self):
        def func(arg1, **kw):
            return arg1, kw
        res = func(arg1=42, something=23)
        assert res[0] == 42
        assert res[1] == {'something': 23}

    def test_kwargs_sets_positional_twice(self):
        def func(arg1, **kw):
            return arg1, kw
        raises(
            TypeError, func, 42, {'arg1': 23})

    def test_kwargs_nondict_mapping(self):
        class Mapping:
            def keys(self):
                return ('a', 'b')
            def __getitem__(self, key):
                return key
        def func(arg1, **kw):
            return arg1, kw
        res = func(23, **Mapping())
        assert res[0] == 23
        assert res[1] == {'a': 'a', 'b': 'b'}
        error = raises(TypeError, lambda: func(42, **[]))
        assert error.value.message == ('argument after ** must be a mapping, '
                                       'not list')

    def test_default_arg(self):
        def func(arg1,arg2=42):
            return arg1, arg2
        res = func(arg1=23)
        assert res[0] == 23
        assert res[1] == 42

    def test_defaults_keyword_overrides(self):
        def func(arg1=42, arg2=23):
            return arg1, arg2
        res = func(arg1=23)
        assert res[0] == 23
        assert res[1] == 23

    def test_defaults_keyword_override_but_leaves_empty_positional(self):
        def func(arg1,arg2=42):
            return arg1, arg2
        raises(TypeError, func, arg2=23)

    def test_kwargs_disallows_same_name_twice(self):
        def func(arg1, **kw):
            return arg1, kw
        raises(TypeError, func, 42, **{'arg1': 23})

    def test_kwargs_bound_blind(self):
        class A(object):
            def func(self, **kw):
                return self, kw
        func = A().func

        # don't want the extra argument passing of raises
        try:
            func(self=23)
            assert False
        except TypeError:
            pass

        try:
            func(**{'self': 23})
            assert False
        except TypeError:
            pass

    def test_kwargs_confusing_name(self):
        def func(self):    # 'self' conflicts with the interp-level
            return self*7  # argument to call_function()
        res = func(self=6)
        assert res == 42

    def test_get(self):
        def func(self): return self
        obj = object()
        meth = func.__get__(obj, object)
        assert meth() == obj

    def test_no_get_builtin(self):
        assert not hasattr(dir, '__get__')
        class A(object):
            ord = ord
        a = A()
        assert a.ord('a') == 97

    def test_builtin_as_special_method_is_not_bound(self):
        class A(object):
            __getattr__ = len
        a = A()
        assert a.a == 1
        assert a.ab == 2
        assert a.abcdefghij == 10

    def test_call_builtin(self):
        s = 'hello'
        raises(TypeError, len)
        assert len(s) == 5
        raises(TypeError, len, s, s)
        raises(TypeError, len, s, s, s)
        assert len(*[s]) == 5
        assert len(s, *[]) == 5
        raises(TypeError, len, some_unknown_keyword=s)
        raises(TypeError, len, s, some_unknown_keyword=s)
        raises(TypeError, len, s, s, some_unknown_keyword=s)

    def test_call_error_message(self):
        try:
            len()
        except TypeError, e:
            assert "len() takes exactly 1 argument (0 given)" in e.message
        else:
            assert 0, "did not raise"

        try:
            len(1, 2)
        except TypeError, e:
            assert "len() takes exactly 1 argument (2 given)" in e.message
        else:
            assert 0, "did not raise"

    def test_unicode_docstring(self):
        def f():
            u"hi"
        assert f.__doc__ == u"hi"
        assert type(f.__doc__) is unicode

    def test_subclassing(self):
        # cannot subclass 'function' or 'builtin_function'
        def f():
            pass
        raises(TypeError, type, 'Foo', (type(f),), {})
        raises(TypeError, type, 'Foo', (type(len),), {})

    def test_lambda_docstring(self):
        # Like CPython, (lambda:"foo") has a docstring of "foo".
        # But let's not test that.  Just test that (lambda:42) does not
        # have 42 as docstring.
        f = lambda: 42
        assert f.func_doc is None

    def test_setstate_called_with_wrong_args(self):
        f = lambda: 42
        # not sure what it should raise, since CPython doesn't have setstate
        # on function types
        raises(ValueError, type(f).__setstate__, f, (1, 2, 3))

class AppTestMethod:
    def test_simple_call(self):
        class A(object):
            def func(self, arg2):
                return self, arg2
        a = A()
        res = a.func(42)
        assert res[0] is a
        assert res[1] == 42

    def test_simple_varargs(self):
        class A(object):
            def func(self, *args):
                return self, args
        a = A()
        res = a.func(42)
        assert res[0] is a
        assert res[1] == (42,)

        res = a.func(*(42,))
        assert res[0] is a
        assert res[1] == (42,)

    def test_obscure_varargs(self):
        class A(object):
            def func(*args):
                return args
        a = A()
        res = a.func(42)
        assert res[0] is a
        assert res[1] == 42

        res = a.func(*(42,))
        assert res[0] is a
        assert res[1] == 42

    def test_simple_kwargs(self):
        class A(object):
            def func(self, **kwargs):
                return self, kwargs
        a = A()

        res = a.func(value=42)
        assert res[0] is a
        assert res[1] == {'value': 42}

        res = a.func(**{'value': 42})
        assert res[0] is a
        assert res[1] == {'value': 42}

    def test_get(self):
        def func(self): return self
        class Object(object): pass
        obj = Object()
        # Create bound method from function
        obj.meth = func.__get__(obj, Object)
        assert obj.meth() == obj
        # Create bound method from method
        meth2 = obj.meth.__get__(obj, Object)
        assert meth2() == obj

    def test_get_get(self):
        # sanxiyn's test from email
        def m(self): return self
        class C(object): pass
        class D(C): pass
        C.m = m
        D.m = C.m
        c = C()
        assert c.m() == c
        d = D()
        assert d.m() == d

    def test_method_eq(self):
        class C(object):
            def m(): pass
        c = C()
        assert C.m == C.m
        assert c.m == c.m
        assert not (C.m == c.m)
        assert not (c.m == C.m)
        c2 = C()
        assert (c.m == c2.m) is False
        assert (c.m != c2.m) is True
        assert (c.m != c.m) is False

    def test_method_hash(self):
        class C(object):
            def m(): pass
        class D(C):
            pass
        c = C()
        assert hash(C.m) == hash(D.m)
        assert hash(c.m) == hash(c.m)

    def test_method_repr(self):
        class A(object):
            def f(self):
                pass
        assert repr(A.f) == "<unbound method A.f>"
        assert repr(A().f).startswith("<bound method A.f of <")
        assert repr(A().f).endswith(">>")
        class B:
            def f(self):
                pass
        assert repr(B.f) == "<unbound method B.f>"
        assert repr(B().f).startswith("<bound method B.f of <")
        assert repr(A().f).endswith(">>")


    def test_method_call(self):
        class C(object):
            def __init__(self, **kw):
                pass
        c = C(type='test')

    def test_method_w_callable(self):
        class A(object):
            def __call__(self, x):
                return x
        import new
        im = new.instancemethod(A(), 3)
        assert im() == 3

    def test_method_w_callable_call_function(self):
        class A(object):
            def __call__(self, x, y):
                return x+y
        import new
        im = new.instancemethod(A(), 3)
        assert map(im, [4]) == [7]

    def test_unbound_typecheck(self):
        class A(object):
            def foo(self, *args):
                return args
        class B(A):
            pass
        class C(A):
            pass

        assert A.foo(A(), 42) == (42,)
        assert A.foo(B(), 42) == (42,)
        raises(TypeError, A.foo, 5)
        raises(TypeError, B.foo, C())
        try:
            class Fun:
                __metaclass__ = A.foo
            assert 0  # should have raised
        except TypeError:
            pass
        class Fun:
            __metaclass__ = A().foo
        assert Fun[:2] == ('Fun', ())

    def test_unbound_abstract_typecheck(self):
        import new
        def f(*args):
            return args
        m = new.instancemethod(f, None, "foobar")
        raises(TypeError, m)
        raises(TypeError, m, None)
        raises(TypeError, m, "egg")

        m = new.instancemethod(f, None, (str, int))     # really obscure...
        assert m(4) == (4,)
        assert m("uh") == ("uh",)
        raises(TypeError, m, [])

        class MyBaseInst(object):
            pass
        class MyInst(MyBaseInst):
            def __init__(self, myclass):
                self.myclass = myclass
            def __class__(self):
                if self.myclass is None:
                    raise AttributeError
                return self.myclass
            __class__ = property(__class__)
        class MyClass(object):
            pass
        BBase = MyClass()
        BSub1 = MyClass()
        BSub2 = MyClass()
        BBase.__bases__ = ()
        BSub1.__bases__ = (BBase,)
        BSub2.__bases__ = (BBase,)
        x = MyInst(BSub1)
        m = new.instancemethod(f, None, BSub1)
        assert m(x) == (x,)
        raises(TypeError, m, MyInst(BBase))
        raises(TypeError, m, MyInst(BSub2))
        raises(TypeError, m, MyInst(None))
        raises(TypeError, m, MyInst(42))

    def test_invalid_creation(self):
        import new
        def f(): pass
        raises(TypeError, new.instancemethod, f, None)

    def test_empty_arg_kwarg_call(self):
        def f():
            pass

        raises(TypeError, lambda: f(*0))
        raises(TypeError, lambda: f(**0))

    def test_method_equal(self):
        class A(object):
            def m(self):
                pass

        class X(object):
            def __eq__(self, other):
                return True

        assert A().m == X()
        assert X() == A().m


class TestMethod:
    def setup_method(self, method):
        def c(self, bar):
            return bar
        code = PyCode._from_code(self.space, c.func_code)
        self.fn = Function(self.space, code, self.space.newdict())

    def test_get(self):
        space = self.space
        w_meth = descr_function_get(space, self.fn, space.wrap(5), space.type(space.wrap(5)))
        meth = space.unwrap(w_meth)
        assert isinstance(meth, Method)

    def test_call(self):
        space = self.space
        w_meth = descr_function_get(space, self.fn, space.wrap(5), space.type(space.wrap(5)))
        meth = space.unwrap(w_meth)
        w_result = meth.call_args(Arguments(space, [space.wrap(42)]))
        assert space.unwrap(w_result) == 42

    def test_fail_call(self):
        space = self.space
        w_meth = descr_function_get(space, self.fn, space.wrap(5), space.type(space.wrap(5)))
        meth = space.unwrap(w_meth)
        args = Arguments(space, [space.wrap("spam"), space.wrap("egg")])
        self.space.raises_w(self.space.w_TypeError, meth.call_args, args)

    def test_method_get(self):
        space = self.space
        # Create some function for this test only
        def m(self): return self
        func = Function(space, PyCode._from_code(self.space, m.func_code),
                        space.newdict())
        # Some shorthands
        obj1 = space.wrap(23)
        obj2 = space.wrap(42)
        args = Arguments(space, [])
        # Check method returned from func.__get__()
        w_meth1 = descr_function_get(space, func, obj1, space.type(obj1))
        meth1 = space.unwrap(w_meth1)
        assert isinstance(meth1, Method)
        assert meth1.call_args(args) == obj1
        # Check method returned from method.__get__()
        # --- meth1 is already bound so meth1.__get__(*) is meth1.
        w_meth2 = meth1.descr_method_get(obj2, space.type(obj2))
        meth2 = space.unwrap(w_meth2)
        assert isinstance(meth2, Method)
        assert meth2.call_args(args) == obj1
        # Check method returned from unbound_method.__get__()
        w_meth3 = descr_function_get(space, func, space.w_None, space.type(obj2))
        meth3 = space.unwrap(w_meth3)
        w_meth4 = meth3.descr_method_get(obj2, space.w_None)
        meth4 = space.unwrap(w_meth4)
        assert isinstance(meth4, Method)
        assert meth4.call_args(args) == obj2
        # Check method returned from unbound_method.__get__()
        # --- with an incompatible class
        w_meth5 = meth3.descr_method_get(space.wrap('hello'), space.w_str)
        assert space.is_w(w_meth5, w_meth3)

class TestShortcuts(object):

    def test_call_function(self):
        space = self.space

        d = {}
        for i in range(10):
            args = "(" + ''.join(["a%d," % a for a in range(i)]) + ")"
            exec """
def f%s:
    return %s
""" % (args, args) in d
            f = d['f']
            res = f(*range(i))
            code = PyCode._from_code(self.space, f.func_code)
            fn = Function(self.space, code, self.space.newdict())

            assert fn.code.fast_natural_arity == i|PyCode.FLATPYCALL
            if i < 5:

                 def bomb(*args):
                     assert False, "shortcutting should have avoided this"

                 code.funcrun = bomb
                 code.funcrun_obj = bomb

            args_w = map(space.wrap, range(i))
            w_res = space.call_function(fn, *args_w)
            check = space.is_true(space.eq(w_res, space.wrap(res)))
            assert check

    def test_flatcall(self):
        space = self.space

        def f(a):
            return a
        code = PyCode._from_code(self.space, f.func_code)
        fn = Function(self.space, code, self.space.newdict())

        assert fn.code.fast_natural_arity == 1|PyCode.FLATPYCALL

        def bomb(*args):
            assert False, "shortcutting should have avoided this"

        code.funcrun = bomb
        code.funcrun_obj = bomb

        w_3 = space.newint(3)
        w_res = space.call_function(fn, w_3)

        assert w_res is w_3

        w_res = space.appexec([fn, w_3], """(f, x):
        return f(x)
        """)

        assert w_res is w_3

    def test_flatcall_method(self):
        space = self.space

        def f(self, a):
            return a
        code = PyCode._from_code(self.space, f.func_code)
        fn = Function(self.space, code, self.space.newdict())

        assert fn.code.fast_natural_arity == 2|PyCode.FLATPYCALL

        def bomb(*args):
            assert False, "shortcutting should have avoided this"

        code.funcrun = bomb
        code.funcrun_obj = bomb

        w_3 = space.newint(3)
        w_res = space.appexec([fn, w_3], """(f, x):
        class A(object):
           m = f
        y = A().m(x)
        b = A().m
        z = b(x)
        return y is x and z is x
        """)

        assert space.is_true(w_res)

    def test_flatcall_default_arg(self):
        space = self.space

        def f(a, b):
            return a+b
        code = PyCode._from_code(self.space, f.func_code)
        fn = Function(self.space, code, self.space.newdict(),
                      defs_w=[space.newint(1)])

        assert fn.code.fast_natural_arity == 2|eval.Code.FLATPYCALL

        def bomb(*args):
            assert False, "shortcutting should have avoided this"

        code.funcrun = bomb
        code.funcrun_obj = bomb

        w_3 = space.newint(3)
        w_4 = space.newint(4)
        # ignore this for now
        #w_res = space.call_function(fn, w_3)
        # assert space.eq_w(w_res, w_4)

        w_res = space.appexec([fn, w_3], """(f, x):
        return f(x)
        """)

        assert space.eq_w(w_res, w_4)

    def test_flatcall_default_arg_method(self):
        space = self.space

        def f(self, a, b):
            return a+b
        code = PyCode._from_code(self.space, f.func_code)
        fn = Function(self.space, code, self.space.newdict(),
                      defs_w=[space.newint(1)])

        assert fn.code.fast_natural_arity == 3|eval.Code.FLATPYCALL

        def bomb(*args):
            assert False, "shortcutting should have avoided this"

        code.funcrun = bomb
        code.funcrun_obj = bomb

        w_3 = space.newint(3)

        w_res = space.appexec([fn, w_3], """(f, x):
        class A(object):
           m = f
        y = A().m(x)
        b = A().m
        z = b(x)
        return y+10*z
        """)

        assert space.eq_w(w_res, space.wrap(44))


class TestFunction:

    def test_func_defaults(self):
        from pypy.interpreter import gateway
        def g(w_a=gateway.NoneNotWrapped):
            pass
        app_g = gateway.interp2app_temp(g)
        space = self.space
        w_g = space.wrap(app_g)
        w_defs = space.getattr(w_g, space.wrap("func_defaults"))
        assert space.is_w(w_defs, space.w_None)

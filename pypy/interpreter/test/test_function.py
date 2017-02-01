# encoding: utf-8
import pytest
from pypy.interpreter import eval
from pypy.interpreter.function import Function, Method, descr_function_get
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.argument import Arguments


class AppTestFunctionIntrospection:
    def test_attributes(self):
        globals()['__name__'] = 'mymodulename'
        def f(): pass
        assert hasattr(f, '__code__')
        assert f.__defaults__ == None
        f.__defaults__ = None
        assert f.__defaults__ == None
        assert f.__dict__ == {}
        assert type(f.__globals__) == dict
        assert f.__closure__ is None
        assert f.__doc__ == None
        assert f.__name__ == 'f'
        assert f.__module__ == 'mymodulename'

    def test_qualname(self):
        def f():
            def g():
                pass
            return g
        assert f.__qualname__ == 'test_qualname.<locals>.f'
        assert f().__qualname__ == 'test_qualname.<locals>.f.<locals>.g'
        f.__qualname__ = 'qualname'
        assert f.__qualname__ == 'qualname'
        raises(TypeError, "f.__qualname__ = b'name'")

    def test_qualname_method(self):
        class A:
            def f(self):
                pass
        assert A.f.__qualname__ == 'test_qualname_method.<locals>.A.f'

    def test_qualname_global(self):
        def f():
            global inner_global
            def inner_global():
                def inner_function2():
                    pass
                return inner_function2
            return inner_global
        assert f().__qualname__ == 'inner_global'
        assert f()().__qualname__ == 'inner_global.<locals>.inner_function2'

    def test_annotations(self):
        def f(): pass
        ann = f.__annotations__
        assert ann == {}
        assert f.__annotations__ is ann
        raises(TypeError, setattr, f, "__annotations__", 42)
        del f.__annotations__
        assert f.__annotations__ is not ann
        f.__annotations__ = ann
        assert f.__annotations__ is ann

    def test_annotations_mangle(self): """
        class X:
            def foo(self, __a:5, b:6):
                pass
        assert X.foo.__annotations__ == {'_X__a': 5, 'b': 6}
        """

    def test_kwdefaults(self):
        """
        def f(*, kw=3): return kw
        assert f.__kwdefaults__ == {"kw" : 3}
        f.__kwdefaults__["kw"] = 4
        assert f() == 4
        f.__kwdefaults__ = {"kw" : 5}
        assert f() == 5
        del f.__kwdefaults__
        assert f.__kwdefaults__ is None
        raises(TypeError, f)
        assert f(kw=42) == 42
        def f(*, 日本=3): return kw
        assert f.__kwdefaults__ == {"日本" : 3}
        """

    def test_kw_nonascii(self):
        """
        def f(日本: str=1):
            return 日本
        assert f.__annotations__ == {'日本': str}
        assert f() == 1
        assert f(日本='bar') == 'bar'
        """

    def test_code_is_ok(self):
        def f(): pass
        assert not hasattr(f.__code__, '__dict__')

    def test_underunder_attributes(self):
        def f(): pass
        assert f.__name__ == 'f'
        assert f.__doc__ == None
        assert f.__dict__ == {}
        assert f.__code__.co_name == 'f'
        assert f.__defaults__ is None
        assert f.__globals__ is globals()
        assert hasattr(f, '__class__')

    def test_classmethod(self):
        def f():
            pass
        assert classmethod(f).__func__ is f
        assert staticmethod(f).__func__ is f

    def test_write___doc__(self):
        def f(): "hello"
        assert f.__doc__ == 'hello'
        f.__doc__ = 'good bye'
        assert f.__doc__ == 'good bye'
        del f.__doc__
        assert f.__doc__ == None

    def test_write_module(self):
        def f(): "hello"
        f.__module__ = 'ab.c'
        assert f.__module__ == 'ab.c'
        del f.__module__
        assert f.__module__ is None

    def test_new(self):
        def f(): return 42
        FuncType = type(f)
        f2 = FuncType(f.__code__, f.__globals__, 'f2', None, None)
        assert f2() == 42

        def g(x):
            def f():
                return x
            return f
        f = g(42)
        raises(TypeError, FuncType, f.__code__, f.__globals__, 'f2', None, None)

    def test_write_code(self):
        def f():
            return 42
        def g():
            return 41
        assert f() == 42
        assert g() == 41
        raises(TypeError, "f.__code__ = 1")
        f.__code__ = g.__code__
        assert f() == 41
        def get_h(f=f):
            def h():
                return f() # a closure
            return h
        h = get_h()
        raises(ValueError, "f.__code__ = h.__code__")

    def test_write_code_builtin_forbidden(self):
        def f(*args):
            return 42
        raises(TypeError, "dir.__code__ = f.__code__")
        raises(TypeError, "list.append.__code__ = f.__code__")

    def test_write_extra_attributes_builtin_forbidden(self):
        raises(AttributeError, "dir.abcd = 5")
        raises(AttributeError, "list.append.im_func.efgh = 6")
        raises(AttributeError, "dir.__dict__")
        raises(AttributeError, "dir.__dict__ = {}")

    def test_set_module_to_name_eagerly(self):
        skip("fails on PyPy but works on CPython.  Unsure we want to care")
        exec('''if 1:
            __name__ = "foo"
            def f(): pass
            __name__ = "bar"
            assert f.__module__ == "foo"''')

    def test_func_nonascii(self):
        """
        def 日本():
            pass
        assert repr(日本).startswith(
            '<function test_func_nonascii.<locals>.日本 at ')
        assert 日本.__name__ == '日本'
        """


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

    @pytest.mark.skipif("config.option.runappdirect")
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
        assert ('argument after ** must be a mapping, not list' in
                str(error.value))

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

    def test_none_get_interaction(self):
        skip("XXX issue #2083")
        assert type(None).__repr__(None) == 'None'

    def test_none_get_interaction_2(self):
        f = None.__repr__
        assert f() == 'None'

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

    @pytest.mark.skipif("config.option.runappdirect")
    def test_call_error_message(self):
        try:
            len()
        except TypeError as e:
            msg = str(e)
            msg = msg.replace('one', '1') # CPython puts 'one', PyPy '1'
            assert "len() missing 1 required positional argument: 'obj'" in msg
        else:
            assert 0, "did not raise"

        try:
            len(1, 2)
        except TypeError as e:
            msg = str(e)
            msg = msg.replace('one', '1') # CPython puts 'one', PyPy '1'
            assert "len() takes 1 positional argument but 2 were given" in msg
        else:
            assert 0, "did not raise"

    def test_unicode_docstring(self):
        def f():
            "hi"
        assert f.__doc__ == "hi"
        assert type(f.__doc__) is str

    def test_issue1293(self):
        def f1(): "doc f1"
        def f2(): "doc f2"
        f1.__code__ = f2.__code__
        assert f1.__doc__ == "doc f1"

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
        assert f.__doc__ is None

    @pytest.mark.skipif("config.option.runappdirect")
    def test_setstate_called_with_wrong_args(self):
        f = lambda: 42
        # not sure what it should raise, since CPython doesn't have setstate
        # on function types
        FunctionType=  type(f)
        if hasattr(FunctionType, '__setstate__'):
            raises(ValueError, FunctionType.__setstate__, f, (1, 2, 3))

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
        assert repr(A().f).startswith("<bound method %s.f of <" %
                                      A.__qualname__)
        assert repr(A().f).endswith(">>")

    def test_method_repr_2(self):
        class ClsA(object):
            def f(self):
                pass
        class ClsB(ClsA):
            pass
        r = repr(ClsB().f)
        assert "ClsA.f of <" in r
        assert "ClsB object at " in r

    def test_method_call(self):
        class C(object):
            def __init__(self, **kw):
                pass
        c = C(type='test')

    def test_method_w_callable(self):
        class A(object):
            def __call__(self, x):
                return x
        import types
        im = types.MethodType(A(), 3)
        assert im() == 3

    def test_method_w_callable_call_function(self):
        class A(object):
            def __call__(self, x, y):
                return x+y
        import types
        im = types.MethodType(A(), 3)
        assert list(map(im, [4])) == [7]

    def test_invalid_creation(self):
        import types
        def f(): pass
        raises(TypeError, types.MethodType, f, None)

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

    @pytest.mark.skipif("config.option.runappdirect")
    def test_method_identity(self):
        class A(object):
            def m(self):
                pass
            def n(self):
                pass

        class B(A):
            pass

        class X(object):
            def __eq__(self, other):
                return True

        a = A()
        a2 = A()
        assert a.m is a.m
        assert id(a.m) == id(a.m)
        assert a.m is not a.n
        assert id(a.m) != id(a.n)
        assert a.m is not a2.m
        assert id(a.m) != id(a2.m)

        assert A.m is A.m
        assert id(A.m) == id(A.m)
        assert A.m is not A.n
        assert id(A.m) != id(A.n)
        assert A.m is B.m
        assert id(A.m) == id(B.m)


class TestMethod:
    def setup_method(self, method):
        def c(self, bar):
            return bar
        code = PyCode._from_code(self.space, c.__code__)
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
        func = Function(space, PyCode._from_code(self.space, m.__code__),
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
        assert meth3 is func

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
            code = PyCode._from_code(self.space, f.__code__)
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
        code = PyCode._from_code(self.space, f.__code__)
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
        code = PyCode._from_code(self.space, f.__code__)
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
        code = PyCode._from_code(self.space, f.__code__)
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
        code = PyCode._from_code(self.space, f.__code__)
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
        def g(w_a=None):
            pass
        app_g = gateway.interp2app_temp(g)
        space = self.space
        w_g = space.wrap(app_g)
        w_defs = space.getattr(w_g, space.wrap("__defaults__"))
        assert space.is_w(w_defs, space.w_None)

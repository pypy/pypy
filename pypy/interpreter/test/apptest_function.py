import pytest
from pytest import raises, skip

def test_attributes():
    globals()['__name__'] = 'mymodulename'
    def f(): pass
    assert hasattr(f, 'func_code')
    assert f.func_defaults == None
    f.func_defaults = None
    assert f.func_defaults == None
    assert f.func_dict == {}
    assert type(f.func_globals) == dict
    assert f.func_globals is f.__globals__
    assert f.func_closure is None
    assert f.func_doc == None
    assert f.func_name == 'f'
    assert f.__module__ == 'mymodulename'

def test_code_is_ok():
    def f(): pass
    assert not hasattr(f.func_code, '__dict__')

def test_underunder_attributes():
    def f(): pass
    assert f.__name__ == 'f'
    assert f.__doc__ == None
    assert f.__name__ == f.func_name
    assert f.__doc__ == f.func_doc
    assert f.__dict__ is f.func_dict
    assert f.__code__ is f.func_code
    assert f.__defaults__ is f.func_defaults
    assert hasattr(f, '__class__')

def test_classmethod():
    def f():
        pass
    assert classmethod(f).__func__ is f
    assert staticmethod(f).__func__ is f

def test_write_doc():
    def f(): "hello"
    assert f.__doc__ == 'hello'
    f.__doc__ = 'good bye'
    assert f.__doc__ == 'good bye'
    del f.__doc__
    assert f.__doc__ == None

def test_write_func_doc():
    def f(): "hello"
    assert f.func_doc == 'hello'
    f.func_doc = 'good bye'
    assert f.func_doc == 'good bye'
    del f.func_doc
    assert f.func_doc == None

def test_write_module():
    def f(): "hello"
    f.__module__ = 'ab.c'
    assert f.__module__ == 'ab.c'
    del f.__module__
    assert f.__module__ is None

def test_new():
    def f(): return 42
    FuncType = type(f)
    f2 = FuncType(f.func_code, f.func_globals, 'f2', None, None)
    assert f2() == 42

    def g(x):
        def f():
            return x
        return f
    f = g(42)
    with raises(TypeError):
        FuncType(f.func_code, f.func_globals, 'f2', None, None)

def test_write_code():
    def f():
        return 42
    def g():
        return 41
    assert f() == 42
    assert g() == 41
    with raises(TypeError):
        f.func_code = 1
    f.func_code = g.func_code
    assert f() == 41
    def h():
        return f() # a closure
    with raises(ValueError):
        f.func_code = h.func_code

def test_write_code_builtin_forbidden():
    def f(*args):
        return 42
    with raises(TypeError):
        dir.func_code = f.func_code
    with raises(TypeError):
        list.append.im_func.func_code = f.func_code

def test_write_attributes_builtin_forbidden():
    for func in [dir, dict.get.im_func]:
        with raises(TypeError):
            func.func_defaults = (1, )
        with raises(TypeError):
            del func.func_defaults
        with raises(TypeError):
            func.func_doc = ""
        with raises(TypeError):
            del func.func_doc
        with raises(TypeError):
            func.func_name = ""
        with raises(TypeError):
            func.__module__ = ""
        with raises(TypeError):
            del func.__module__

def test_set_name():
    def f(): pass
    f.__name__ = 'g'
    assert f.func_name == 'g'
    with raises(TypeError):
        f.__name__ = u'g'


def test_simple_call():
    def func(arg1, arg2):
        return arg1, arg2
    res = func(23,42)
    assert res[0] == 23
    assert res[1] == 42

def test_simple_call_default():
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

    with raises(TypeError):
        func()
    with raises(TypeError):
        func(1, 2, 3, 4)

def test_simple_varargs():
    def func(arg1, *args):
        return arg1, args
    res = func(23,42)
    assert res[0] == 23
    assert res[1] == (42,)

    res = func(23, *(42,))
    assert res[0] == 23
    assert res[1] == (42,)

def test_simple_kwargs():
    def func(arg1, **kwargs):
        return arg1, kwargs
    res = func(23, value=42)
    assert res[0] == 23
    assert res[1] == {'value': 42}

    res = func(23, **{'value': 42})
    assert res[0] == 23
    assert res[1] == {'value': 42}

def test_kwargs_sets_wrong_positional_raises():
    def func(arg1):
        pass
    with raises(TypeError):
        func(arg2=23)

def test_kwargs_sets_positional():
    def func(arg1):
        return arg1
    res = func(arg1=42)
    assert res == 42

def test_kwargs_sets_positional_mixed():
    def func(arg1, **kw):
        return arg1, kw
    res = func(arg1=42, something=23)
    assert res[0] == 42
    assert res[1] == {'something': 23}

def test_kwargs_sets_positional_twice():
    def func(arg1, **kw):
        return arg1, kw
    with raises(TypeError):
        func(42, {'arg1': 23})

def test_kwargs_nondict_mapping():
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
    with raises(TypeError) as excinfo:
        func(42, **[])
    assert excinfo.value.message == (
        'argument after ** must be a mapping, not list')

def test_default_arg():
    def func(arg1,arg2=42):
        return arg1, arg2
    res = func(arg1=23)
    assert res[0] == 23
    assert res[1] == 42

def test_defaults_keyword_overrides():
    def func(arg1=42, arg2=23):
        return arg1, arg2
    res = func(arg1=23)
    assert res[0] == 23
    assert res[1] == 23

def test_defaults_keyword_override_but_leaves_empty_positional():
    def func(arg1,arg2=42):
        return arg1, arg2
    with raises(TypeError):
        func(arg2=23)

def test_kwargs_disallows_same_name_twice():
    def func(arg1, **kw):
        return arg1, kw
    with raises(TypeError):
        func(42, **{'arg1': 23})

def test_kwargs_bound_blind():
    class A(object):
        def func(self, **kw):
            return self, kw
    func = A().func
    with raises(TypeError):
        func(self=23)
    with raises(TypeError):
        func(**{'self': 23})

def test_kwargs_confusing_name():
    def func(self):    # 'self' conflicts with the interp-level
        return self*7  # argument to call_function()
    res = func(self=6)
    assert res == 42

def test_get():
    def func(self): return self
    obj = object()
    meth = func.__get__(obj, object)
    assert meth() == obj

@pytest.mark.skipif(True, reason="XXX issue #2083")
def test_none_get_interaction():
    assert type(None).__repr__(None) == 'None'

def test_none_get_interaction_2():
    f = None.__repr__
    assert f() == 'None'

def test_no_get_builtin():
    assert not hasattr(dir, '__get__')
    class A(object):
        ord = ord
    a = A()
    assert a.ord('a') == 97

def test_builtin_as_special_method_is_not_bound():
    class A(object):
        __getattr__ = len
    a = A()
    assert a.a == 1
    assert a.ab == 2
    assert a.abcdefghij == 10

def test_call_builtin():
    s = 'hello'
    with raises(TypeError):
        len()
    assert len(s) == 5
    with raises(TypeError):
        len(s, s)
    with raises(TypeError):
        len(s, s, s)
    assert len(*[s]) == 5
    assert len(s, *[]) == 5
    with raises(TypeError):
        len(some_unknown_keyword=s)
    with raises(TypeError):
        len(s, some_unknown_keyword=s)
    with raises(TypeError):
        len(s, s, some_unknown_keyword=s)

def test_call_error_message():
    try:
        len()
    except TypeError as e:
        assert "len() takes exactly 1 argument (0 given)" in e.message
    else:
        assert 0, "did not raise"

    try:
        len(1, 2)
    except TypeError as e:
        assert "len() takes exactly 1 argument (2 given)" in e.message
    else:
        assert 0, "did not raise"

def test_unicode_docstring():
    def f():
        u"hi"
    assert f.__doc__ == u"hi"
    assert type(f.__doc__) is unicode

def test_issue1293():
    def f1(): "doc f1"
    def f2(): "doc f2"
    f1.func_code = f2.func_code
    assert f1.__doc__ == "doc f1"

def test_subclassing():
    # cannot subclass 'function' or 'builtin_function'
    def f():
        pass
    with raises(TypeError):
        type('Foo', (type(f),), {})
    with raises(TypeError):
        type('Foo', (type(len),), {})

def test_lambda_docstring():
    # Like CPython, (lambda:"foo") has a docstring of "foo".
    # But let's not test that.  Just test that (lambda:42) does not
    # have 42 as docstring.
    f = lambda: 42
    assert f.func_doc is None

def test_setstate_called_with_wrong_args():
    f = lambda: 42
    # not sure what it should raise, since CPython doesn't have setstate
    # on function types
    with raises(ValueError):
        type(f).__setstate__(f, (1, 2, 3))

def test_simple_call():
    class A(object):
        def func(self, arg2):
            return self, arg2
    a = A()
    res = a.func(42)
    assert res[0] is a
    assert res[1] == 42

def test_simple_varargs():
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

def test_obscure_varargs():
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

def test_simple_kwargs():
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

def test_get():
    def func(self): return self
    class Object(object): pass
    obj = Object()
    # Create bound method from function
    obj.meth = func.__get__(obj, Object)
    assert obj.meth() == obj
    # Create bound method from method
    meth2 = obj.meth.__get__(obj, Object)
    assert meth2() == obj

def test_get_get():
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

def test_method_eq():
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

def test_method_hash():
    class C(object):
        def m(): pass
    class D(C):
        pass
    c = C()
    assert hash(C.m) == hash(D.m)
    assert hash(c.m) == hash(c.m)

def test_method_repr():
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

    assert repr(type(A.f)) == repr(type(A().f)) == "<type 'instancemethod'>"


def test_method_call():
    class C(object):
        def __init__(self, **kw):
            pass
    c = C(type='test')

def test_method_w_callable():
    class A(object):
        def __call__(self, x):
            return x
    import new
    im = new.instancemethod(A(), 3)
    assert im() == 3

def test_method_w_callable_call_function():
    class A(object):
        def __call__(self, x, y):
            return x+y
    import new
    im = new.instancemethod(A(), 3)
    assert map(im, [4]) == [7]

def test_unbound_typecheck():
    class A(object):
        def foo(self, *args):
            return args
    class B(A):
        pass
    class C(A):
        pass

    assert A.foo(A(), 42) == (42,)
    assert A.foo(B(), 42) == (42,)
    with raises(TypeError):
        A.foo(5)
    with raises(TypeError):
        B.foo(C())
    with raises(TypeError):
        class Fun:
            __metaclass__ = A.foo
    class Fun:
        __metaclass__ = A().foo
    assert Fun[:2] == ('Fun', ())

def test_unbound_abstract_typecheck():
    import new
    def f(*args):
        return args
    m = new.instancemethod(f, None, "foobar")
    with raises(TypeError):
        m()
    with raises(TypeError):
        m(None)
    with raises(TypeError):
        m("egg")

    m = new.instancemethod(f, None, (str, int))     # really obscure...
    assert m(4) == (4,)
    assert m("uh") == ("uh",)
    with raises(TypeError):
        m([])

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
    with raises(TypeError):
        m(MyInst(BBase))
    with raises(TypeError):
        m(MyInst(BSub2))
    with raises(TypeError):
        m(MyInst(None))
    with raises(TypeError):
        m(MyInst(42))

def test_invalid_creation():
    import new
    def f():
        pass
    with raises(TypeError):
        new.instancemethod(f, None)

def test_empty_arg_kwarg_call():
    def f():
        pass

    with raises(TypeError):
        f(*0)
    with raises(TypeError):
        f(**0)

def test_method_equal():
    class A(object):
        def m(self):
            pass

    class X(object):
        def __eq__(self, other):
            return True

    assert A().m == X()
    assert X() == A().m

def test_method_equals_with_identity():
    from types import MethodType
    class CallableBadEq(object):
        def __call__(self):
            pass
        def __eq__(self, other):
            raise ZeroDivisionError
    func = CallableBadEq()
    meth = MethodType(func, object)
    assert meth == meth
    assert meth == MethodType(func, object)

def test_method_identity():
    import sys
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
    x = a.m; y = a.m
    assert x is not y
    assert id(x) != id(y)
    assert x == y
    assert x is not a.n
    assert id(x) != id(a.n)
    assert x is not a2.m
    assert id(x) != id(a2.m)

    if '__pypy__' in sys.builtin_module_names:
        assert A.m is A.m
        assert id(A.m) == id(A.m)
    assert A.m == A.m
    x = A.m
    assert x is not A.n
    assert id(x) != id(A.n)
    assert x is not B.m
    assert id(x) != id(B.m)

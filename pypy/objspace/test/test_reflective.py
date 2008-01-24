from pypy.conftest import gettestobjspace

class AppTest_Reflective:

    def setup_class(cls):
        cls.space = gettestobjspace('reflective')

    def test_add(self):
        from __pypy__ import set_reflectivespace
        class Space:
            def add(self, space, x, y):
                return 40+2

        set_reflectivespace(Space())
        x = 1
        y = 2
        assert x + y == 42

        set_reflectivespace(None)
        x = 1
        y = 2
        assert x + y == 3

    def test_fallback(self):
        from __pypy__ import set_reflectivespace
        class Space:
            def mul(self, space, x, y):
                return space.add(x, y)

        class Add(object):
            def __init__(self, val):
                self.val = val
            def __add__(self, other):
                return self.val * other.val
        a2 = Add(2)
        a5 = Add(5)
        set_reflectivespace(Space())
        assert a2 * a5 == 7
        set_reflectivespace(None)
        
    def test_default_behaviour(self):
        from __pypy__ import set_reflectivespace
        class Space:
            pass

        set_reflectivespace(Space())
        x = 1
        y = 2
        assert x + y == 3

    def test_newdict(self):
        from __pypy__ import set_reflectivespace
        class Space:
            def newdict(self, space, d):
                d['surprise'] = 42
                return d

        set_reflectivespace(Space())
        d = {"b": 1}
        assert d["surprise"] == 42
        set_reflectivespace(None)


    def test_newlist(self):
        from __pypy__ import set_reflectivespace
        class Space:
            def newlist(self, space, l):
                l.append(len(l))
                return l

        set_reflectivespace(Space())
        l = [1, 2, 3, 4, 5]
        assert len(l) == 6
        set_reflectivespace(None)

    def test_type_must_return_type(self):
        from __pypy__ import set_reflectivespace
        class Space:
            def type(self, space, o):
                if o is l:
                    return 1
                return type(o)
        l = []
        set_reflectivespace(Space())
        raises(TypeError, type, l)
        set_reflectivespace(None)

    def test_type(self):
        from __pypy__ import set_reflectivespace
        class Space:
            def type(self, space, o):
                if o is a:
                    return B
                return type(o)
        type(1)
        class A(object):
            f = lambda self: 1
        class B(object):
            f = lambda self: 2
        a = A()
        set_reflectivespace(Space())
        assert a.f() == 2

    def test_typed_unwrap(self):
        from __pypy__ import set_reflectivespace
        class Space:
            def int_w(self, space, i):
                if isinstance(i, basestring):
                    return int(i)
                return i
        set_reflectivespace(Space())
        assert chr("123") == chr(123)

    def test_is(self):
        from __pypy__ import set_reflectivespace
        IAmNone = object()
        class Space:
            def replace(self, obj):
                if obj is IAmNone:
                    return None
                return obj
            def is_(self, space, a, b):
                return self.replace(a) is self.replace(b)
            def type(self, space, a):
                return type(self.replace(a))
        set_reflectivespace(Space())
        assert IAmNone is None
        assert type(IAmNone) is type(None)
        # check that space.is_w is not using a fast path
        class A(object):
            x = property(lambda self: 1, IAmNone)
        a = A()
        assert a.x == 1
        raises(AttributeError, "a.x = 2")
        set_reflectivespace(None)

    def test_is_true(self):
        from __pypy__ import set_reflectivespace
        class Space:
            def is_true(self, space, obj):
                print "is_true", obj
                if type(obj) == int:
                    # confusity
                    return bool(obj % 13)
                return space.is_true(bool)
        set_reflectivespace(Space())
        bool(13)
        if 13:
            assert False, "should not get here"
        if "abc":
            pass
        else:
            assert False, "should not get here"
        set_reflectivespace(None)
        

    def test_autocurry(self):
        # rather simplified for now
        from __pypy__ import set_reflectivespace
        class partial(object):
            def __init__(self, func, callable, *args, **kwargs):
                self.func = func
                self.callable = callable
                self.args = args
                self.kwargs = kwargs
            def combine_args(self, args, kwargs):
                args = self.args + args
                for key, value in self.kwargs.iteritems():
                    if key in kwargs:
                        raise TypeError("got multiple values for keyword argument %r" % (key, ))
                    kwargs[key] = value
                return args, kwargs
            def __call__(self, *args, **kwargs):
                args, kwargs = self.combine_args(args, kwargs)
                return self.callable(*args, **kwargs)
        def enough_args(func, args, kwargs):
            code = func.func_code
            needed = code.co_varnames[:code.co_argcount]
            needed_set = set(needed)
            argnames = set(needed)
            defaults = func.func_defaults
            for i in range(min(len(args), len(needed))):
                name = needed[i]
                needed_set.remove(name)
            for key, value in kwargs.iteritems():
                if key not in needed_set:
                    if key in argnames:
                        raise TypeError(
                            "%s() got multiple values for keyword argument %r" % (
                                func.func_name, key))
                needed_set.discard(key)
            if defaults is not None:
                for i in range(len(defaults)):
                    default_name = needed[-1 - i]
                    needed_set.discard(default_name)
            return len(needed_set) == 0

        import types
        class Space:
            def call_args(self, space, callable, *args, **kwargs):
                print callable, args, kwargs
                if isinstance(callable, partial):
                    args, kwargs = callable.combine_args(args, kwargs)
                    func = callable.func
                    callable = callable.callable
                if isinstance(callable, types.MethodType):
                    if callable.im_self is not None:
                        args = (callable.im_self, ) + args
                        func = callable.im_func
                        callable = func
                    else:
                        func = callable.im_func
                elif not isinstance(callable, types.FunctionType):
                    return space.call_args(callable, *args, **kwargs)
                else:
                    func = callable
                if enough_args(func, args, kwargs):
                    return space.call_args(callable, *args, **kwargs)
                return partial(func, callable, *args, **kwargs)
        def f(x, y, z):
            return x + y * z
        set_reflectivespace(Space())
        g = f(1, 2)
        assert g(3) == f(1, 2, 3)
        assert f(4)(6)(7) == f(4, 6, 7)
        def g(x):
            return f(x)
        assert g(4)(5, 6) == f(4, 5, 6)
        class A(object):
            def __init__(self, val):
                self.val = val
            def func(self, b, c):
                return self.val + b * c
        a = A(3)
        assert a.func()(5, 6) == f(3, 5, 6)
        assert A.func()(a)(5)(6) == f(3, 5, 6)
        def f(x, y=1):
            return x + y * 2
        f(y=2)(3) == 7
        def f(x, **kwds):
            return x + kwds['y'] * 2
        f(y=2)(3) == 7

    def test_logicspace(self):
        from __pypy__ import set_reflectivespace
        NotBound = object()
        class Var(object):
            def __init__(self):
                self.boundto = NotBound
        def bind(var, obj):
            XXX # never called? :-)
        forcing_args = {
            'setattr': 2,
            'setitem': 2,
            'get': 2,
        }
        class UnboundVariable(Exception):
            pass
        class Space(object):
            def convert(self, obj):
                if isinstance(obj, Var):
                    if obj.boundto is not NotBound:
                        return obj
                    raise UnboundVariable
            def __getattr__(self, name):
                if name.startswith("new"):
                    raise AttributeError
                def f(self, space, *args):
                    pass
                

from pypy.conftest import gettestobjspace

class AppTest_Reflective:

    def setup_class(cls):
        cls.space = gettestobjspace('reflective')

    def test_add(self):
        from __pypy__ import set_reflectivespace
        class Space:
            def add(self, x, y):
                return 40+2

        set_reflectivespace(Space())
        x = 1
        y = 2
        assert x + y == 42

        set_reflectivespace(None)
        x = 1
        y = 2
        assert x + y == 3
        
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
            def newdict(self, d):
                d['surprise'] = 42
                return d

        set_reflectivespace(Space())
        d = {"b": 1}
        assert d["surprise"] == 42
        set_reflectivespace(None)


    def test_newlist(self):
        from __pypy__ import set_reflectivespace
        class Space:
            def newlist(self, l):
                l.append(len(l))
                return l

        set_reflectivespace(Space())
        l = [1, 2, 3, 4, 5]
        assert len(l) == 6
        set_reflectivespace(None)

    def test_type_must_return_type(self):
        from __pypy__ import set_reflectivespace
        class Space:
            def type(self, o):
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
            def type(self, o):
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

    def test_autocurry(self):
        # rather simplified for now
        from __pypy__ import set_reflectivespace
        class partial(object):
            def __init__(self, func, *args, **kwargs):
                self.func = func
                self.args = args
                self.kwargs = kwargs
            def __call__(self, *args, **kwargs):
                args = self.args + args
                for key, value in self.kwargs.iteritems():
                    if key in kwargs:
                        raise TypeError("got multiple values for keyword argument %r" % (key, ))
                    kwargs[key] = value
                return self.func(*args, **kwargs)
        import types
        class Space:
            def call_args(self, func, *args, **kwargs):
                print func, args, kwargs
                if (len(kwargs) != 0 or not 
                    isinstance(func, types.FunctionType)):
                    return func(*args, **kwargs)
                defaults = func.func_defaults
                if defaults is None:
                    defaults = ()
                argcount = func.func_code.co_argcount
                minargs = argcount - len(defaults)
                if len(args) >= minargs:
                    return func(*args, **kwargs)
                return partial(func, *args, **kwargs)
        def f(x, y, z):
            return x + y * z
        set_reflectivespace(Space())
        g = f(1, 2)
        assert g(3) == f(1, 2, 3)
        # XXX the following does not work, of course:
        # assert f(4)(6)(7) == f(4, 6, 7)

import py

class AppTest(object):
    spaceconfig = {"objspace.usemodules.select": False,
                   "objspace.std.withrangelist": True}

    def setup_class(cls):
        if cls.runappdirect:
            py.test.skip("does not make sense on pypy-c")

    def test_cpumodel(self):
        import __pypy__
        assert hasattr(__pypy__, 'cpumodel')

    def test_builtinify(self):
        import __pypy__
        class A(object):
            a = lambda *args: args
            b = __pypy__.builtinify(a)
        my = A()
        assert my.a() == (my,)
        assert my.b() == ()
        assert A.a(my) == (my,)
        assert A.b(my) == (my,)
        assert A.a.im_func(my) == (my,)
        assert not hasattr(A.b, 'im_func')
        assert A.a is not A.__dict__['a']
        assert A.b is A.__dict__['b']

    def test_lookup_special(self):
        from __pypy__ import lookup_special
        class X(object):
            def foo(self): return 42
        x = X()
        x.foo = 23
        x.bar = 80
        assert lookup_special(x, "foo")() == 42
        assert lookup_special(x, "bar") is None
        class X:
            pass
        raises(TypeError, lookup_special, X(), "foo")

    def test_do_what_I_mean(self):
        from __pypy__ import do_what_I_mean
        x = do_what_I_mean()
        assert x == 42

    def test_list_strategy(self):
        from __pypy__ import list_strategy

        l = [1, 2, 3]
        assert list_strategy(l) == "int"
        l = ["a", "b", "c"]
        assert list_strategy(l) == "bytes"
        l = [u"a", u"b", u"c"]
        assert list_strategy(l) == "unicode"
        l = [1.1, 2.2, 3.3]
        assert list_strategy(l) == "float"
        l = range(3)
        assert list_strategy(l) == "range"
        l = [1, "b", 3]
        assert list_strategy(l) == "object"
        l = []
        assert list_strategy(l) == "empty"
        o = 5
        raises(TypeError, list_strategy, 5)


class AppTestJitFeatures(object):
    spaceconfig = {"translation.jit": True}

    def test_jit_backend_features(self):
        from __pypy__ import jit_backend_features
        supported_types = jit_backend_features
        assert isinstance(supported_types, list)
        for x in supported_types:
            assert x in ['floats', 'singlefloats', 'longlong']

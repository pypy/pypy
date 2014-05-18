import py

class AppTest(object):
    spaceconfig = {"objspace.usemodules.select": False}

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
        assert not hasattr(A.a, 'im_func')
        assert not hasattr(A.b, 'im_func')
        assert A.a is A.__dict__['a']
        assert A.b is A.__dict__['b']

    def test_hidden_applevel(self):
        import __pypy__
        import sys

        @__pypy__.hidden_applevel
        def sneak(): (lambda: 1/0)()
        try:
            sneak()
        except ZeroDivisionError as e:
            tb = e.__traceback__
            assert tb.tb_frame == sys._getframe()
            assert tb.tb_next.tb_frame.f_code.co_name == '<lambda>'
        else:
            assert False, 'Expected ZeroDivisionError'

    def test_hidden_applevel_frames(self):
        import __pypy__
        import sys

        @__pypy__.hidden_applevel
        def test_hidden():
            assert sys._getframe().f_code.co_name != 'test_hidden'
            def e(): 1/0
            try: e()
            except ZeroDivisionError as e:
                assert sys.exc_info() == (None, None, None)
                frame = e.__traceback__.tb_frame
                assert frame != sys._getframe()
                assert frame.f_code.co_name == 'e'
            else: assert False
            return 2
        assert test_hidden() == 2

    def test_lookup_special(self):
        from __pypy__ import lookup_special
        class X(object):
            def foo(self): return 42
        x = X()
        x.foo = 23
        x.bar = 80
        assert lookup_special(x, "foo")() == 42
        assert lookup_special(x, "bar") is None

    def test_do_what_I_mean(self):
        from __pypy__ import do_what_I_mean
        x = do_what_I_mean()
        assert x == 42

    def test_list_strategy(self):
        from __pypy__ import list_strategy

        l = [1, 2, 3]
        assert list_strategy(l) == "int"
        l = list(range(1, 2))
        assert list_strategy(l) == "int"
        l = [b"a", b"b", b"c"]
        assert list_strategy(l) == "bytes"
        l = ["a", "b", "c"]
        assert list_strategy(l) == "unicode"
        l = [1.1, 2.2, 3.3]
        assert list_strategy(l) == "float"
        l = [1, "b", 3]
        assert list_strategy(l) == "object"
        l = []
        assert list_strategy(l) == "empty"
        o = 5
        raises(TypeError, list_strategy, 5)

    def test_normalize_exc(self):
        from __pypy__ import normalize_exc
        e = normalize_exc(TypeError)
        assert isinstance(e, TypeError)
        e = normalize_exc(TypeError, 'foo')
        assert isinstance(e, TypeError)
        assert str(e) == 'foo'
        e = normalize_exc(TypeError('doh'))
        assert isinstance(e, TypeError)
        assert str(e) == 'doh'

        try:
            1 / 0
        except ZeroDivisionError as e:
            tb = e.__traceback__
        e = normalize_exc(TypeError, None, tb)
        assert isinstance(e, TypeError)
        assert e.__traceback__ == tb


class AppTestJitFeatures(object):
    spaceconfig = {"translation.jit": True}

    def test_jit_backend_features(self):
        from __pypy__ import jit_backend_features
        supported_types = jit_backend_features
        assert isinstance(supported_types, list)
        for x in supported_types:
            assert x in ['floats', 'singlefloats', 'longlong']

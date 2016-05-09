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
        assert A.a.im_func(my) == (my,)
        assert not hasattr(A.b, 'im_func')
        assert A.a is not A.__dict__['a']
        assert A.b is A.__dict__['b']

    def test_hidden_applevel(self):
        import __pypy__
        import sys

        @__pypy__.hidden_applevel
        def sneak(): (lambda: 1/0)()
        try:
            sneak()
        except ZeroDivisionError as e:
            tb = sys.exc_info()[2]
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
            else: assert False
            return 2
        assert test_hidden() == 2

    def test_get_hidden_tb(self):
        import __pypy__
        import sys

        result = [False]
        @__pypy__.hidden_applevel
        def test_hidden_with_tb():
            def not_hidden(): 1/0
            try: not_hidden()
            except ZeroDivisionError as e:
                assert sys.exc_info() == (None, None, None)
                tb = __pypy__.get_hidden_tb()
                assert tb.tb_frame.f_code.co_name == 'not_hidden'
                result[0] = True
                raise
            else: return False
        raises(ZeroDivisionError, test_hidden_with_tb)
        assert result[0]

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
        from __pypy__ import strategy

        l = [1, 2, 3]
        assert strategy(l) == "IntegerListStrategy"
        l = ["a", "b", "c"]
        assert strategy(l) == "BytesListStrategy"
        l = [u"a", u"b", u"c"]
        assert strategy(l) == "UnicodeListStrategy"
        l = [1.1, 2.2, 3.3]
        assert strategy(l) == "FloatListStrategy"
        l = range(3)
        assert strategy(l) == "SimpleRangeListStrategy"
        l = range(1, 2)
        assert strategy(l) == "RangeListStrategy"
        l = [1, "b", 3]
        assert strategy(l) == "ObjectListStrategy"
        l = []
        assert strategy(l) == "EmptyListStrategy"
        o = 5
        raises(TypeError, strategy, 5)

    def test_dict_strategy(self):
        from __pypy__ import strategy

        d = {}
        assert strategy(d) == "EmptyDictStrategy"
        d = {1: None, 5: None}
        assert strategy(d) == "IntDictStrategy"

    def test_set_strategy(self):
        from __pypy__ import strategy

        s = set()
        assert strategy(s) == "EmptySetStrategy"
        s = set([2, 3, 4])
        assert strategy(s) == "IntegerSetStrategy"


class AppTestJitFeatures(object):
    spaceconfig = {"translation.jit": True}

    def test_jit_backend_features(self):
        from __pypy__ import jit_backend_features
        supported_types = jit_backend_features
        assert isinstance(supported_types, list)
        for x in supported_types:
            assert x in ['floats', 'singlefloats', 'longlong']

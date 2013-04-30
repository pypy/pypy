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
        py3k_skip("XXX: strategies are currently broken")
        from __pypy__ import list_strategy

        l = [1, 2, 3]
        assert list_strategy(l) == "int"
        l = ["a", "b", "c"]
        assert list_strategy(l) == "str"
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

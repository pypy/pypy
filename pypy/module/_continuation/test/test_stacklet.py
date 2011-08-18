import os
from pypy.conftest import gettestobjspace


class AppTestStacklet:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_continuation'])
        cls.w_translated = cls.space.wrap(
            os.path.join(os.path.dirname(__file__),
                         'test_translated.py'))

    def test_new_empty(self):
        from _continuation import continulet
        #
        def empty_callback(c):
            pass
        #
        c = continulet(empty_callback)
        assert type(c) is continulet

    def test_call_empty(self):
        from _continuation import continulet
        #
        def empty_callback(c1):
            assert c1 is c
            seen.append(1)
            return 42
        #
        seen = []
        c = continulet(empty_callback)
        res = c.switch()
        assert res == 42
        assert seen == [1]

    def test_no_double_init(self):
        from _continuation import continulet, error
        #
        def empty_callback(c1):
            pass
        #
        c = continulet(empty_callback)
        raises(error, c.__init__, empty_callback)

    def test_no_init_after_started(self):
        from _continuation import continulet, error
        #
        def empty_callback(c1):
            raises(error, c1.__init__, empty_callback)
            return 42
        #
        c = continulet(empty_callback)
        res = c.switch()
        assert res == 42

    def test_no_init_after_finished(self):
        from _continuation import continulet, error
        #
        def empty_callback(c1):
            return 42
        #
        c = continulet(empty_callback)
        res = c.switch()
        assert res == 42
        raises(error, c.__init__, empty_callback)

    def test_propagate_exception(self):
        from _continuation import continulet
        #
        def empty_callback(c1):
            assert c1 is c
            seen.append(42)
            raise ValueError
        #
        seen = []
        c = continulet(empty_callback)
        raises(ValueError, c.switch)
        assert seen == [42]

    def test_callback_with_arguments(self):
        from _continuation import continulet
        #
        def empty_callback(c1, *args, **kwds):
            seen.append(c1)
            seen.append(args)
            seen.append(kwds)
            return 42
        #
        seen = []
        c = continulet(empty_callback, 42, 43, foo=44, bar=45)
        res = c.switch()
        assert res == 42
        assert seen == [c, (42, 43), {'foo': 44, 'bar': 45}]

    def test_switch(self):
        from _continuation import continulet
        #
        def switchbackonce_callback(c):
            seen.append(1)
            res = c.switch('a')
            assert res == 'b'
            seen.append(3)
            return 'c'
        #
        seen = []
        c = continulet(switchbackonce_callback)
        seen.append(0)
        res = c.switch()
        assert res == 'a'
        seen.append(2)
        res = c.switch('b')
        assert res == 'c'
        assert seen == [0, 1, 2, 3]

    def test_initial_switch_must_give_None(self):
        from _continuation import continulet
        #
        def empty_callback(c):
            return 'ok'
        #
        c = continulet(empty_callback)
        res = c.switch(None)
        assert res == 'ok'
        #
        c = continulet(empty_callback)
        raises(TypeError, c.switch, 'foo')  # "can't send non-None value"

    def test_continuation_error(self):
        from _continuation import continulet, error
        #
        def empty_callback(c):
            return 42
        #
        c = continulet(empty_callback)
        c.switch()
        e = raises(error, c.switch)
        assert str(e.value) == "continulet already finished"

    def test_not_initialized_yet(self):
        from _continuation import continulet, error
        c = continulet.__new__(continulet)
        e = raises(error, c.switch)
        assert str(e.value) == "continulet not initialized yet"

    def test_go_depth2(self):
        from _continuation import continulet
        #
        def depth2(c):
            seen.append(3)
            return 4
        #
        def depth1(c):
            seen.append(1)
            c2 = continulet(depth2)
            seen.append(2)
            res = c2.switch()
            seen.append(res)
            return 5
        #
        seen = []
        c = continulet(depth1)
        seen.append(0)
        res = c.switch()
        seen.append(res)
        assert seen == [0, 1, 2, 3, 4, 5]

    def test_exception_depth2(self):
        from _continuation import continulet
        #
        def depth2(c):
            seen.append(2)
            raise ValueError
        #
        def depth1(c):
            seen.append(1)
            try:
                continulet(depth2).switch()
            except ValueError:
                seen.append(3)
            return 4
        #
        seen = []
        c = continulet(depth1)
        res = c.switch()
        seen.append(res)
        assert seen == [1, 2, 3, 4]

    def test_exception_with_switch(self):
        from _continuation import continulet
        #
        def depth1(c):
            seen.append(1)
            c.switch()
            seen.append(3)
            raise ValueError
        #
        seen = []
        c = continulet(depth1)
        seen.append(0)
        c.switch()
        seen.append(2)
        raises(ValueError, c.switch)
        assert seen == [0, 1, 2, 3]

    def test_is_pending(self):
        from _continuation import continulet
        #
        def switchbackonce_callback(c):
            assert c.is_pending()
            res = c.switch('a')
            assert res == 'b'
            assert c.is_pending()
            return 'c'
        #
        c = continulet.__new__(continulet)
        assert not c.is_pending()
        c.__init__(switchbackonce_callback)
        assert c.is_pending()
        res = c.switch()
        assert res == 'a'
        assert c.is_pending()
        res = c.switch('b')
        assert res == 'c'
        assert not c.is_pending()

    def test_switch_alternate(self):
        from _continuation import continulet
        #
        def func_lower(c):
            res = c.switch('a')
            assert res == 'b'
            res = c.switch('c')
            assert res == 'd'
            return 'e'
        #
        def func_upper(c):
            res = c.switch('A')
            assert res == 'B'
            res = c.switch('C')
            assert res == 'D'
            return 'E'
        #
        c_lower = continulet(func_lower)
        c_upper = continulet(func_upper)
        res = c_lower.switch()
        assert res == 'a'
        res = c_upper.switch()
        assert res == 'A'
        res = c_lower.switch('b')
        assert res == 'c'
        res = c_upper.switch('B')
        assert res == 'C'
        res = c_lower.switch('d')
        assert res == 'e'
        res = c_upper.switch('D')
        assert res == 'E'

    def test_exception_with_switch_depth2(self):
        from _continuation import continulet
        #
        def depth2(c):
            seen.append(4)
            c.switch()
            seen.append(6)
            raise ValueError
        #
        def depth1(c):
            seen.append(1)
            c.switch()
            seen.append(3)
            c2 = continulet(depth2)
            c2.switch()
            seen.append(5)
            raises(ValueError, c2.switch)
            assert not c2.is_pending()
            seen.append(7)
            assert c.is_pending()
            raise KeyError
        #
        seen = []
        c = continulet(depth1)
        c.switch()
        seen.append(2)
        raises(KeyError, c.switch)
        assert not c.is_pending()
        assert seen == [1, 2, 3, 4, 5, 6, 7]

    def test_random_switching(self):
        from _continuation import continulet
        #
        def t1(c1):
            return c1.switch()
        def s1(c1, n):
            assert n == 123
            c2 = t1(c1)
            return c1.switch('a') + 1
        #
        def s2(c2, c1):
            res = c1.switch(c2)
            assert res == 'a'
            return c2.switch('b') + 2
        #
        def f():
            c1 = continulet(s1, 123)
            c2 = continulet(s2, c1)
            c1.switch()
            res = c2.switch()
            assert res == 'b'
            res = c1.switch(1000)
            assert res == 1001
            return c2.switch(2000)
        #
        res = f()
        assert res == 2002

    def test_f_back_is_None_for_now(self):
        import sys
        from _continuation import continulet
        #
        def g(c):
            c.switch(sys._getframe(0))
            c.switch(sys._getframe(0).f_back)
            c.switch(sys._getframe(1))
            c.switch(sys._getframe(1).f_back)
            c.switch(sys._getframe(2))
        def f(c):
            g(c)
        #
        c = continulet(f)
        f1 = c.switch()
        assert f1.f_code.co_name == 'g'
        f2 = c.switch()
        assert f2.f_code.co_name == 'f'
        f3 = c.switch()
        assert f3.f_code.co_name == 'f'
        f4 = c.switch()
        assert f4 is None
        raises(ValueError, c.switch)    # "call stack is not deep enough"

    def test_traceback_is_complete(self):
        import sys
        from _continuation import continulet
        #
        def g():
            raise KeyError
        def f(c):
            g()
        #
        def do(c):
            c.switch()
        #
        c = continulet(f)
        try:
            do(c)
        except KeyError:
            tb = sys.exc_info()[2]
        else:
            raise AssertionError("should have raised!")
        #
        assert tb.tb_next.tb_frame.f_code.co_name == 'do'
        assert tb.tb_next.tb_next.tb_frame.f_code.co_name == 'f'
        assert tb.tb_next.tb_next.tb_next.tb_frame.f_code.co_name == 'g'
        assert tb.tb_next.tb_next.tb_next.tb_next is None

    def test_switch2_simple(self):
        skip("in-progress")
        from _continuation import continulet
        #
        def f1(c1):
            res = c1.switch_to(c2)
            assert res == 'a'
            return 41
        def f2(c2):
            c2.switch_to(c1, 'a')
            return 42
        #
        c1 = continulet(f1)
        c2 = continulet(f2)
        res = c1.switch()
        assert res == 41
        assert c2.is_pending()    # already
        res = c2.switch()
        assert res == 42

    def test_various_depths(self):
        skip("may fail on top of CPython")
        # run it from test_translated, but not while being actually translated
        d = {}
        execfile(self.translated, d)
        d['set_fast_mode']()
        d['test_various_depths']()

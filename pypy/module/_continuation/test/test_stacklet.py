import os
from pypy.conftest import gettestobjspace


class AppTestStacklet:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_continuation'])
        cls.w_translated = cls.space.wrap(
            os.path.join(os.path.dirname(__file__),
                         'test_translated.py'))

    def test_new_empty(self):
        from _continuation import continuation
        #
        def empty_callback(c):
            pass
        #
        c = continuation(empty_callback)
        assert type(c) is continuation

    def test_call_empty(self):
        from _continuation import continuation
        #
        def empty_callback(c1):
            assert c1 is c
            seen.append(1)
            return 42
        #
        seen = []
        c = continuation(empty_callback)
        res = c.switch()
        assert res == 42
        assert seen == [1]

    def test_no_init_after_started(self):
        from _continuation import continuation, error
        #
        def empty_callback(c1):
            raises(error, c1.__init__, empty_callback)
            return 42
        #
        c = continuation(empty_callback)
        res = c.switch()
        assert res == 42

    def test_no_init_after_finished(self):
        from _continuation import continuation, error
        #
        def empty_callback(c1):
            return 42
        #
        c = continuation(empty_callback)
        res = c.switch()
        assert res == 42
        raises(error, c.__init__, empty_callback)

    def test_propagate_exception(self):
        from _continuation import continuation
        #
        def empty_callback(c1):
            assert c1 is c
            seen.append(42)
            raise ValueError
        #
        seen = []
        c = continuation(empty_callback)
        raises(ValueError, c.switch)
        assert seen == [42]

    def test_callback_with_arguments(self):
        from _continuation import continuation
        #
        def empty_callback(c1, *args, **kwds):
            seen.append(c1)
            seen.append(args)
            seen.append(kwds)
            return 42
        #
        seen = []
        c = continuation(empty_callback, 42, 43, foo=44, bar=45)
        res = c.switch()
        assert res == 42
        assert seen == [c, (42, 43), {'foo': 44, 'bar': 45}]

    def test_switch(self):
        from _continuation import continuation
        #
        def switchbackonce_callback(c):
            seen.append(1)
            res = c.switch('a')
            assert res == 'b'
            seen.append(3)
            return 'c'
        #
        seen = []
        c = continuation(switchbackonce_callback)
        seen.append(0)
        res = c.switch()
        assert res == 'a'
        seen.append(2)
        res = c.switch('b')
        assert res == 'c'
        assert seen == [0, 1, 2, 3]

    def test_continuation_error(self):
        from _continuation import continuation, error
        #
        def empty_callback(c):
            return 42
        #
        c = continuation(empty_callback)
        c.switch()
        raises(error, c.switch)

    def test_not_initialized_yet(self):
        from _continuation import continuation, error
        c = continuation.__new__(continuation)
        raises(error, c.switch)

    def test_go_depth2(self):
        from _continuation import continuation
        #
        def depth2(c):
            seen.append(3)
            return 4
        #
        def depth1(c):
            seen.append(1)
            c2 = continuation(depth2)
            seen.append(2)
            res = c2.switch()
            seen.append(res)
            return 5
        #
        seen = []
        c = continuation(depth1)
        seen.append(0)
        res = c.switch()
        seen.append(res)
        assert seen == [0, 1, 2, 3, 4, 5]

    def test_exception_depth2(self):
        from _continuation import continuation
        #
        def depth2(c):
            seen.append(2)
            raise ValueError
        #
        def depth1(c):
            seen.append(1)
            try:
                continuation(depth2).switch()
            except ValueError:
                seen.append(3)
            return 4
        #
        seen = []
        c = continuation(depth1)
        res = c.switch()
        seen.append(res)
        assert seen == [1, 2, 3, 4]

    def test_exception_with_switch(self):
        from _continuation import continuation
        #
        def depth1(c):
            seen.append(1)
            c.switch()
            seen.append(3)
            raise ValueError
        #
        seen = []
        c = continuation(depth1)
        seen.append(0)
        c.switch()
        seen.append(2)
        raises(ValueError, c.switch)
        assert seen == [0, 1, 2, 3]

    def test_is_pending(self):
        from _continuation import continuation
        #
        def switchbackonce_callback(c):
            assert c.is_pending()
            res = c.switch('a')
            assert res == 'b'
            assert c.is_pending()
            return 'c'
        #
        c = continuation.__new__(continuation)
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
        from _continuation import continuation
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
        c_lower = continuation(func_lower)
        c_upper = continuation(func_upper)
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
        from _continuation import continuation
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
            c2 = continuation(depth2)
            c2.switch()
            seen.append(5)
            raises(ValueError, c2.switch)
            assert not c2.is_pending()
            seen.append(7)
            assert c.is_pending()
            raise KeyError
        #
        seen = []
        c = continuation(depth1)
        c.switch()
        seen.append(2)
        raises(KeyError, c.switch)
        assert not c.is_pending()
        assert seen == [1, 2, 3, 4, 5, 6, 7]

    def test_various_depths(self):
        skip("may fail on top of CPython")
        # run it from test_translated, but not while being actually translated
        d = {}
        execfile(self.translated, d)
        d['set_fast_mode']()
        d['test_various_depths']()

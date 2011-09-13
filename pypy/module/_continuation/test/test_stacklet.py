import os
from pypy.module._continuation.test.support import BaseAppTest


class AppTestStacklet(BaseAppTest):
    def setup_class(cls):
        BaseAppTest.setup_class.im_func(cls)
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

    def test_f_back(self):
        import sys
        from _continuation import continulet
        #
        def g(c):
            c.switch(sys._getframe(0))
            c.switch(sys._getframe(0).f_back)
            c.switch(sys._getframe(1))
            c.switch(sys._getframe(1).f_back)
            assert sys._getframe(2) is f3.f_back
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
        assert f3 is f2
        assert f1.f_back is f3
        def main():
            f4 = c.switch()
            assert f4.f_code.co_name == 'main', repr(f4.f_code.co_name)
            assert f3.f_back is f1    # not running, so a loop
        def main2():
            f5 = c.switch()
            assert f5.f_code.co_name == 'main2', repr(f5.f_code.co_name)
            assert f3.f_back is f1    # not running, so a loop
        main()
        main2()
        res = c.switch()
        assert res is None
        assert f3.f_back is None

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
        from _continuation import continulet
        #
        def f1(c1):
            res = c1.switch('started 1')
            assert res == 'a'
            res = c1.switch('b', to=c2)
            assert res == 'c'
            return 42
        def f2(c2):
            res = c2.switch('started 2')
            assert res == 'b'
            res = c2.switch('c', to=c1)
            not_reachable
        #
        c1 = continulet(f1)
        c2 = continulet(f2)
        res = c1.switch()
        assert res == 'started 1'
        res = c2.switch()
        assert res == 'started 2'
        res = c1.switch('a')
        assert res == 42

    def test_switch2_pingpong(self):
        from _continuation import continulet
        #
        def f1(c1):
            res = c1.switch('started 1')
            assert res == 'go'
            for i in range(10):
                res = c1.switch(i, to=c2)
                assert res == 100 + i
            return 42
        def f2(c2):
            res = c2.switch('started 2')
            for i in range(10):
                assert res == i
                res = c2.switch(100 + i, to=c1)
            not_reachable
        #
        c1 = continulet(f1)
        c2 = continulet(f2)
        res = c1.switch()
        assert res == 'started 1'
        res = c2.switch()
        assert res == 'started 2'
        res = c1.switch('go')
        assert res == 42

    def test_switch2_more_complex(self):
        from _continuation import continulet
        #
        def f1(c1):
            res = c1.switch(to=c2)
            assert res == 'a'
            res = c1.switch('b', to=c2)
            assert res == 'c'
            return 41
        def f2(c2):
            res = c2.switch('a', to=c1)
            assert res == 'b'
            return 42
        #
        c1 = continulet(f1)
        c2 = continulet(f2)
        res = c1.switch()
        assert res == 42
        assert not c2.is_pending()    # finished by returning 42
        res = c1.switch('c')
        assert res == 41

    def test_switch2_no_op(self):
        from _continuation import continulet
        #
        def f1(c1):
            res = c1.switch('a', to=c1)
            assert res == 'a'
            return 42
        #
        c1 = continulet(f1)
        res = c1.switch()
        assert res == 42

    def test_switch2_immediately_away(self):
        from _continuation import continulet
        #
        def f1(c1):
            print 'in f1'
            return 'm'
        #
        def f2(c2):
            res = c2.switch('z')
            print 'got there!'
            assert res == 'a'
            return None
        #
        c1 = continulet(f1)
        c2 = continulet(f2)
        res = c2.switch()
        assert res == 'z'
        assert c1.is_pending()
        assert c2.is_pending()
        print 'calling!'
        res = c1.switch('a', to=c2)
        print 'back'
        assert res == 'm'

    def test_switch2_immediately_away_corner_case(self):
        from _continuation import continulet
        #
        def f1(c1):
            this_is_never_seen
        #
        def f2(c2):
            res = c2.switch('z')
            assert res is None
            return 'b'    # this goes back into the caller, which is f1,
                          # but f1 didn't start yet, so a None-value value
                          # has nowhere to go to...
        c1 = continulet(f1)
        c2 = continulet(f2)
        res = c2.switch()
        assert res == 'z'
        raises(TypeError, c1.switch, to=c2)  # "can't send non-None value"

    def test_switch2_not_initialized_yet(self):
        from _continuation import continulet, error
        #
        def f1(c1):
            not_reachable
        #
        c1 = continulet(f1)
        c2 = continulet.__new__(continulet)
        e = raises(error, c1.switch, to=c2)
        assert str(e.value) == "continulet not initialized yet"

    def test_switch2_already_finished(self):
        from _continuation import continulet, error
        #
        def f1(c1):
            not_reachable
        def empty_callback(c):
            return 42
        #
        c1 = continulet(f1)
        c2 = continulet(empty_callback)
        c2.switch()
        e = raises(error, c1.switch, to=c2)
        assert str(e.value) == "continulet already finished"

    def test_throw(self):
        import sys
        from _continuation import continulet
        #
        def f1(c1):
            try:
                c1.switch()
            except KeyError:
                res = "got keyerror"
            try:
                c1.switch(res)
            except IndexError, e:
                pass
            try:
                c1.switch(e)
            except IndexError, e2:
                pass
            try:
                c1.switch(e2)
            except IndexError:
                c1.throw(*sys.exc_info())
            should_never_reach_here
        #
        c1 = continulet(f1)
        c1.switch()
        res = c1.throw(KeyError)
        assert res == "got keyerror"
        class FooError(IndexError):
            pass
        foo = FooError()
        res = c1.throw(foo)
        assert res is foo
        res = c1.throw(IndexError, foo)
        assert res is foo
        #
        def main():
            def do_raise():
                raise foo
            try:
                do_raise()
            except IndexError:
                tb = sys.exc_info()[2]
            try:
                c1.throw(IndexError, foo, tb)
            except IndexError:
                tb = sys.exc_info()[2]
            return tb
        #
        tb = main()
        assert tb.tb_frame.f_code.co_name == 'main'
        assert tb.tb_next.tb_frame.f_code.co_name == 'f1'
        assert tb.tb_next.tb_next.tb_frame.f_code.co_name == 'main'
        assert tb.tb_next.tb_next.tb_next.tb_frame.f_code.co_name == 'do_raise'
        assert tb.tb_next.tb_next.tb_next.tb_next is None

    def test_throw_to_starting(self):
        from _continuation import continulet
        #
        def f1(c1):
            not_reached
        #
        c1 = continulet(f1)
        raises(IndexError, c1.throw, IndexError)

    def test_throw2_simple(self):
        from _continuation import continulet
        #
        def f1(c1):
            not_reached
        def f2(c2):
            try:
                c2.switch("ready")
            except IndexError:
                raise ValueError
        #
        c1 = continulet(f1)
        c2 = continulet(f2)
        res = c2.switch()
        assert res == "ready"
        assert c1.is_pending()
        assert c2.is_pending()
        raises(ValueError, c1.throw, IndexError, to=c2)
        assert not c1.is_pending()
        assert not c2.is_pending()

    def test_throw2_no_op(self):
        from _continuation import continulet
        #
        def f1(c1):
            raises(ValueError, c1.throw, ValueError, to=c1)
            return "ok"
        #
        c1 = continulet(f1)
        res = c1.switch()
        assert res == "ok"

    def test_permute(self):
        import sys
        from _continuation import continulet, permute
        #
        def f1(c1):
            res = c1.switch()
            assert res == "ok"
            return "done"
        #
        def f2(c2):
            assert sys._getframe(1).f_code.co_name == 'main'
            permute(c1, c2)
            assert sys._getframe(1).f_code.co_name == 'f1'
            return "ok"
        #
        c1 = continulet(f1)
        c2 = continulet(f2)
        def main():
            c1.switch()
            res = c2.switch()
            assert res == "done"
        main()

    def test_bug_finish_with_already_finished_stacklet(self):
        from _continuation import continulet, error
        # make an already-finished continulet
        c1 = continulet(lambda x: x)
        c1.switch()
        # make another continulet
        c2 = continulet(lambda x: x)
        # this switch is forbidden, because it causes a crash when c2 finishes
        raises(error, c1.switch, to=c2)

    def test_various_depths(self):
        skip("may fail on top of CPython")
        # run it from test_translated, but not while being actually translated
        d = {}
        execfile(self.translated, d)
        d['set_fast_mode']()
        d['test_various_depths']()

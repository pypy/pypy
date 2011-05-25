from pypy.conftest import gettestobjspace, option
from py.test import skip


class AppTest_Coroutine:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('_stackless',))
        cls.space = space

    def test_raise_propagate(self):
        import _stackless as stackless
        co = stackless.coroutine()
        def f():
            return 1/0
        co.bind(f)
        try:
            co.switch()
        except ZeroDivisionError:
            pass
        else:
            raise AssertionError("exception not propagated")

    def test_strange_test(self):
        from _stackless import coroutine
        def f():
            print "in new coro"
            return 42
        def create():
            b = coroutine()
            b.bind(f)
            print "bound"
            b.switch()
            print "switched"
            return b
        a = coroutine()
        a.bind(create)
        b = a.switch()
        # now b.parent = a
        def nothing():
            pass
        a.bind(nothing)
        def kill():
            # this sets a.parent = b
            a.kill()
        b.bind(kill)
        b.switch()

    def test_kill(self):
        import _stackless as stackless
        co = stackless.coroutine()
        def f():
            pass
        co.bind(f)
        assert co.is_alive
        co.kill()
        assert not co.is_alive

    def test_kill_running(self):
        coroutineexit = []
        import _stackless as stackless
        main = stackless.coroutine.getcurrent()
        result = []
        co = stackless.coroutine()
        def f():
            x = 2
            try:
                result.append(1)
                main.switch()
                x = 3
            except CoroutineExit:
                coroutineexit.append(True)
                raise
            finally:
                result.append(x)
            result.append(4)
        co.bind(f)
        assert co.is_alive
        co.switch()
        assert co.is_alive
        assert result == [1]
        co.kill()
        assert not co.is_alive
        assert result == [1, 2]
        assert coroutineexit == [True]

    def test_bogus_bind(self):
        import _stackless as stackless
        co = stackless.coroutine()
        def f():
            pass
        co.bind(f)
        raises(ValueError, co.bind, f)

    def test__framestack(self):
        import _stackless as stackless
        main = stackless.coroutine.getmain()
        co = stackless.coroutine()
        def g():
            return co._framestack
        def f():
            return g()

        co.bind(f)
        stack = co.switch()
        assert stack == () # running corountine, _framestack is empty

        co = stackless.coroutine()
        def g():
            return main.switch()
        def f():
            return g()

        co.bind(f)
        co.switch()
        stack = co._framestack
        assert len(stack) == 2
        assert stack[0].f_code is f.func_code
        assert stack[1].f_code is g.func_code

        co = stackless.coroutine()



class AppTestDirect:
    def setup_class(cls):
        if not option.runappdirect:
            skip('pure appdirect test (run with -A)')
        cls.space = gettestobjspace(usemodules=('_stackless',))

    def test_stack_depth_limit(self):
        import sys
        import _stackless as stackless
        st = stackless.get_stack_depth_limit()
        try:
            stackless.set_stack_depth_limit(1)
            assert stackless.get_stack_depth_limit() == 1
            try:
                co = stackless.coroutine()
                def f():
                    pass
                co.bind(f)
                co.switch()
            except RuntimeError:
                pass
        finally:
            stackless.set_stack_depth_limit(st)

class TestRandomThings:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('_stackless',))

    def test___del___handling(self):
        space = self.space
        w_l = space.newlist([])
        coro = space.appexec([w_l], """(l):
            from _stackless import coroutine
            class MyCoroutine(coroutine):
                def __del__(self):
                    l.append(self.is_zombie)
            return MyCoroutine()
        """)
        coro.__del__()
        space.user_del_action.perform(space.getexecutioncontext(), None)
        coro._kill_finally()
        assert space.len_w(w_l) == 1
        res = space.is_true(space.getitem(w_l, space.wrap(0)))
        assert res

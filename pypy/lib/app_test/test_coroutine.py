from pypy.lib.stackless import coroutine

from py.test import skip, raises

class Test_Coroutine:

    def test_is_zombie(self):
        co = coroutine()
        def f():
            print 'in coro'
        co.bind(f)
        assert not co.is_zombie

    def test_raise_propagate(self):
        co = coroutine()
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
        def f():
            return 42
        def create():
            b = coroutine()
            b.bind(f)
            b.switch()
            return b
        a = coroutine()
        a.bind(create)
        b = a.switch()
        def nothing():
            pass
        a.bind(nothing)
        def kill():
            a.kill()
        b.bind(kill)
        b.switch()

    def test_kill(self):
        co = coroutine()
        def f():
            pass
        co.bind(f)
        assert co.is_alive
        co.kill()
        assert not co.is_alive

    def test_bogus_bind(self):
        co = coroutine()
        def f():
            pass
        co.bind(f)
        raises(ValueError, co.bind, f)

    def test_simple_task(self):
        maintask = coroutine.getcurrent()
        def f():pass
        co = coroutine()
        co.bind(f)
        co.switch()
        assert not co.is_alive
        assert maintask is coroutine.getcurrent()

    def test_backto_main(self):
        maintask = coroutine.getcurrent()
        def f(task):
            task.switch()
        co = coroutine()
        co.bind(f,maintask)
        co.switch()

    def test_wrapped_main(self):
        class mwrap(object):
            def __init__(self, coro):
                self._coro = coro

            def __getattr__(self, attr):
                return getattr(self._coro, attr)

        maintask = mwrap(coroutine.getcurrent())
        def f(task):
            task.switch()
        co = coroutine()
        co.bind(f,maintask)
        co.switch()


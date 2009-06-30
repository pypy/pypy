from py.test import skip, raises

try:
    from pypy.lib.stackless import coroutine
except ImportError, e:
    skip('cannot import stackless: %s' % (e,))


class Test_Coroutine:

    def test_is_zombie(self):
        co = coroutine()
        def f():
            print 'in coro'
        assert not co.is_zombie
        co.bind(f)
        assert not co.is_zombie
        co.switch()
        assert not co.is_zombie

    def test_is_zombie_del_without_frame(self):
        try:
            import _stackless # are we on pypy with a stackless build?
        except ImportError:
            skip("only works on pypy-c-stackless")
        import gc
        res = []
        class MyCoroutine(coroutine):
            def __del__(self):
                res.append(self.is_zombie)
        def f():
            print 'in coro'
        co = MyCoroutine()
        co.bind(f)
        co.switch()
        del co
        for i in range(10):
            gc.collect()
            if res:
                break
        co = coroutine()
        co.bind(f)
        co.switch()
        assert res[0], "is_zombie was False in __del__"

    def test_is_zombie_del_with_frame(self):
        try:
            import _stackless # are we on pypy with a stackless build?
        except ImportError:
            skip("only works on pypy-c-stackless")
        import gc
        res = []
        class MyCoroutine(coroutine):
            def __del__(self):
                res.append(self.is_zombie)
        main = coroutine.getcurrent()
        def f():
            print 'in coro'
            main.switch()
        co = MyCoroutine()
        co.bind(f)
        co.switch()
        del co
        for i in range(10):
            gc.collect()
            if res:
                break
        co = coroutine()
        co.bind(f)
        co.switch()
        assert res[0], "is_zombie was False in __del__"

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
        assert not co.is_alive
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


import py
from pypy.module.pypystm.test_pypy_c.support import BaseTestSTM


class TestNoConflict(BaseTestSTM):

    def test_basic(self):
        def f():
            class X(object):
                pass
            def g():
                x = X()
                x.a = 5
                x.b = 6.5
                d = {}
                d[5] = 'abc'
                d['foo'] = 'def'
            run_in_threads(g)
        #
        self.check_almost_no_conflict(f)

    def test_stmdict_access(self):
        def f():
            import pypystm
            d = pypystm.stmdict()     # shared
            def g(n):
                d[n] = d.get(n, 0) + 1
            run_in_threads(g, arg_thread_num=True)
        #
        self.check_almost_no_conflict(f)

    def test_hashtable_populate(self):
        def f():
            import pypystm
            class TL(object):
                step = 0
            d = pypystm.hashtable()     # shared
            def g(n, tl):
                value = n + tl.step
                tl.step += 10
                d[value] = tl
            run_in_threads(g, arg_thread_num=True, arg_class=TL)
        #
        self.check_almost_no_conflict(f)

    def test_stmdict_populate(self):
        def f():
            import pypystm
            class TL(object):
                step = 0
            d = pypystm.stmdict()     # shared
            def g(n, tl):
                value = n + tl.step
                tl.step += 10
                d[value] = tl
            run_in_threads(g, arg_thread_num=True, arg_class=TL)
        #
        self.check_almost_no_conflict(f)

    def test_threadlocal(self):
        def f():
            import thread
            tls = thread._local()
            def g():
                tls.value = getattr(tls, 'value', 0) + 1
            run_in_threads(g)
        #
        self.check_almost_no_conflict(f)

    def test_weakrefs(self):
        def f():
            import weakref

            class X(object):
                pass

            lst = []     # shared

            def g(tnum):
                if tnum == 0:
                    lst[:] = [X() for i in range(1000)]
                barrier(tnum)
                for x in lst:
                    weakref.ref(x)
                barrier(tnum)

            run_in_threads(g, arg_thread_num=True)
        #
        self.check_almost_no_conflict(f)

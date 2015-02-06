from pypy.module.pypystm.test_pypy_c.support import BaseTestSTM


class TestConflict(BaseTestSTM):

    def test_obvious(self):
        def f():
            class X(object):
                pass
            x = X()     # shared
            x.a = 0
            def g():
                x.a += 1
            run_in_threads(g)
        #
        self.check_MANY_conflicts(f)

    def test_plain_dict_access(self):
        def f():
            d = {}     # shared
            def g(n):
                d[n] = d.get(n, 0) + 1
            run_in_threads(g, arg_thread_num=True)
        #
        self.check_MANY_conflicts(f)

    def test_write_to_many_objects_in_order(self):
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
                    x.a = 5
                barrier(tnum)

            run_in_threads(g, arg_thread_num=True)
        #
        self.check_SOME_conflicts(f)

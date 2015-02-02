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
        self.check_many_conflicts(f)

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

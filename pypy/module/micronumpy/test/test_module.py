from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest


class AppTestNumPyModule(BaseNumpyAppTest):
    def test_mean(self):
        from numpy import array, mean
        assert mean(array(range(5))) == 2.0
        assert mean(range(5)) == 2.0

    def test_average(self):
        from numpy import array, average
        assert average(range(10)) == 4.5
        assert average(array(range(10))) == 4.5

    def test_constants(self):
        import math
        from numpy import inf, e
        assert type(inf) is float
        assert inf == float("inf")
        assert e == math.e
        assert type(e) is float
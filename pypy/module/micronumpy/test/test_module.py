from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest


class AppTestNumPyModule(BaseNumpyAppTest):
    def test_mean(self):
        from _numpypy import array, mean
        assert mean(array(range(5))) == 2.0
        assert mean(range(5)) == 2.0

    def test_average(self):
        from _numpypy import array, average
        assert average(range(10)) == 4.5
        assert average(array(range(10))) == 4.5
        
    def test_sum(self):
        from _numpypy import array, sum
        assert sum(range(10)) == 45
        assert sum(array(range(10))) == 45

    def test_min(self):
        from _numpypy import array, min
        assert min(range(10)) == 0
        assert min(array(range(10))) == 0
        
    def test_max(self):
        from _numpypy import array, max
        assert max(range(10)) == 9
        assert max(array(range(10))) == 9

    def test_constants(self):
        import math
        from _numpypy import inf, e, pi
        assert type(inf) is float
        assert inf == float("inf")
        assert e == math.e
        assert type(e) is float
        assert pi == math.pi
        assert type(pi) is float

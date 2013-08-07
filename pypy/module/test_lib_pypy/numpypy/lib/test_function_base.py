from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestFunctionBase(BaseNumpyAppTest):
    def test_average(self):
        from numpypy import array, average
        assert average(range(10)) == 4.5
        assert average(array(range(10))) == 4.5

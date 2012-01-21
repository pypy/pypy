
from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest


class AppTestBaseRepr(BaseNumpyAppTest):
    def test_base3(self):
        from numpypy import base_repr
        assert base_repr(3**5, 3) == '100000'

    def test_positive(self):
        from numpypy import base_repr
        assert base_repr(12, 10) == '12'
        assert base_repr(12, 10, 4) == '000012'
        assert base_repr(12, 4) == '30'
        assert base_repr(3731624803700888, 36) == '10QR0ROFCEW'

    def test_negative(self):
        from numpypy import base_repr
        assert base_repr(-12, 10) == '-12'
        assert base_repr(-12, 10, 4) == '-000012'
        assert base_repr(-12, 4) == '-30'

class AppTestRepr(BaseNumpyAppTest):
    def test_repr(self):
        from numpypy import array
        assert repr(array([1, 2, 3, 4])) == 'array([1, 2, 3, 4])'

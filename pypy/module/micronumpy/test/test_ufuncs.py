from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest


class AppTestUfuncs(BaseNumpyAppTest):
    def test_negative(self):
        from numpy import array, negative

        a = array([-5.0, 0.0, 1.0])
        b = negative(a)
        for i in range(3):
            assert b[i] == -a[i]

        a = array([-5.0, 1.0])
        b = negative(a)
        a[0] = 5.0
        assert b[0] == 5.0

    def test_abs(self):
        from numpy import array, abs as npabs

        a = array([-5.0, -0.0, 1.0])
        b = npabs(a)
        for i in range(3):
            assert b[i] == abs(a[i])
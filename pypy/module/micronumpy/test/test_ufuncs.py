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
        from numpy import array, absolute

        a = array([-5.0, -0.0, 1.0])
        b = absolute(a)
        for i in range(3):
            assert b[i] == abs(a[i])

    def test_minimum(self):
        from numpy import array, minimum

        a = array([-5.0, -0.0, 1.0])
        b = array([ 3.0, -2.0,-3.0])
        c = minimum(a, b)
        for i in range(3):
            assert c[i] == min(a[i], b[i])

    def test_maximum(self):
        from numpy import array, maximum

        a = array([-5.0, -0.0, 1.0])
        b = array([ 3.0, -2.0,-3.0])
        c = maximum(a, b)
        for i in range(3):
            assert c[i] == max(a[i], b[i])


from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest


class AppTestUfuncs(BaseNumpyAppTest):
    def test_single_item(self):
        from numpy import negative, sign, minimum

        assert negative(5.0) == -5.0
        assert sign(-0.0) == 0.0
        assert minimum(2.0, 3.0) == 2.0

    def test_sequence(self):
        from numpy import array, negative, minimum
        a = array(range(3))
        b = [2.0, 1.0, 0.0]
        c = 1.0
        b_neg = negative(b)
        assert isinstance(b_neg, array)
        for i in range(3):
            assert b_neg[i] == -b[i]
        min_a_b = minimum(a, b)
        assert isinstance(min_a_b, array)
        for i in range(3):
            assert min_a_b[i] == min(a[i], b[i])
        min_a_c = minimum(a, c)
        assert isinstance(min_a_c, array)
        for i in range(3):
            assert min_a_c[i] == min(a[i], c)
        min_b_c = minimum(b, c)
        assert isinstance(min_b_c, array)
        for i in range(3):
            assert min_b_c[i] == min(b[i], c)

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

    def test_sign(self):
        from numpy import array, sign

        reference = [-1.0, 0.0, 0.0, 1.0]
        a = array([-5.0, -0.0, 0.0, 6.0])
        b = sign(a)
        for i in range(4):
            assert b[i] == reference[i]

    def test_reciporocal(self):
        from numpy import array, reciprocal

        reference = [-0.2, float("inf"), float("-inf"), 2.0]
        a = array([-5.0, 0.0, -0.0, 0.5])
        b = reciprocal(a)
        for i in range(4):
            assert b[i] == reference[i]

    def test_floor(self):
        from numpy import array, floor

        reference = [-2.0, -1.0, 0.0, 1.0, 1.0]
        a = array([-1.4, -1.0, 0.0, 1.0, 1.4])
        b = floor(a)
        for i in range(5):
            assert b[i] == reference[i]

    def test_copysign(self):
        from numpy import array, copysign

        reference = [5.0, -0.0, 0.0, -6.0]
        a = array([-5.0, 0.0, 0.0, 6.0])
        b = array([5.0, -0.0, 3.0, -6.0])
        c = copysign(a, b)
        for i in range(4):
            assert c[i] == reference[i]

    def test_exp(self):
        import math
        from numpy import array, exp

        a = array([-5.0, -0.0, 0.0, 12345678.0, float("inf"),
                   -float('inf'), -12343424.0])
        b = exp(a)
        for i in range(4):
            try:
                res = math.exp(a[i])
            except OverflowError:
                res = float('inf')
            assert b[i] == res

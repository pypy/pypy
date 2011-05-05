import py
from pypy.conftest import gettestobjspace


class AppTestNumpyLike(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('micronumpy',))

    def test_init(self):
        from numpy import zeros
        a = zeros(15)
        # Check that storage was actually zero'd.
        assert a[10] == 0.0
        # And check that changes stick.
        a[13] = 5.3
        assert a[13] == 5.3

    def test_iterator_init(self):
        from numpy import array
        a = array(range(5))
        assert a[3] == 3

    def test_getitem(self):
        from numpy import array
        a = array(range(5))
        raises(TypeError, "a[5]")
        a = a + a
        raises(TypeError, "a[5]")

    def test_add(self):
        from numpy import array
        a = array(range(5))
        b = a + a
        for i in range(5):
            assert b[i] == i + i

    def test_add_other(self):
        from numpy import array
        a = array(range(5))
        b = array(reversed(range(5)))
        c = a + b
        for i in range(5):
            assert c[i] == 4

    def test_add_constant(self):
        from numpy import array
        a = array(range(5))
        b = a + 5
        for i in range(5):
            assert b[i] == i + 5

    def test_subtract(self):
        from numpy import array
        a = array(range(5))
        b = a - a
        for i in range(5):
            assert b[i] == 0

    def test_subtract_other(self):
        from numpy import array
        a = array(range(5))
        b = array([1, 1, 1, 1, 1])
        c = a - b
        for i in range(5):
            assert c[i] == i - 1

    def test_subtract_constant(self):
        from numpy import array
        a = array(range(5))
        b = a - 5
        for i in range(5):
            assert b[i] == i - 5

    def test_mul(self):
        from numpy import array
        a = array(range(5))
        b = a * a
        for i in range(5):
            assert b[i] == i * i

    def test_mul_constant(self):
        from numpy import array
        a = array(range(5))
        b = a * 5
        for i in range(5):
            assert b[i] == i * 5

    def test_div(self):
        from numpy import array
        a = array(range(1, 6))
        b = a / a
        for i in range(5):
            assert b[i] == 1

    def test_div_other(self):
        from numpy import array
        a = array(range(5))
        b = array([2, 2, 2, 2, 2])
        c = a / b
        for i in range(5):
            assert c[i] == i / 2.0

    def test_div_constant(self):
        from numpy import array
        a = array(range(5))
        b = a / 5.0
        for i in range(5):
            assert b[i] == i / 5.0

    def test_auto_force(self):
        from numpy import array
        a = array(range(5))
        b = a - 1
        a[2] = 3
        for i in range(5):
            assert b[i] == i - 1

class AppTestNumpy(object):
    def setup_class(cls):
        py.test.skip("unimplemented")
        cls.space = gettestobjspace(usemodules=('micronumpy',))

    def test_zeroes(self):
        from numpy import zeros
        ar = zeros(3, dtype=int)
        assert ar[0] == 0

    def test_setitem_getitem(self):
        from numpy import zeros
        ar = zeros(8, dtype=int)
        assert ar[0] == 0
        ar[1] = 3
        assert ar[1] == 3
        raises((TypeError, ValueError), ar.__getitem__, 'xyz')
        raises(IndexError, ar.__getitem__, 38)
        assert ar[-2] == 0
        assert ar[-7] == 3
        assert len(ar) == 8

    def test_minimum(self):
        from numpy import zeros, minimum
        ar = zeros(5, dtype=int)
        ar2 = zeros(5, dtype=int)
        ar[0] = 3
        ar[1] = -3
        ar[2] = 8
        ar2[3] = -1
        ar2[4] = 8
        x = minimum(ar, ar2)
        assert x[0] == 0
        assert x[1] == -3
        assert x[2] == 0
        assert x[3] == -1
        assert x[4] == 0
        assert len(x) == 5
        raises(ValueError, minimum, ar, zeros(3, dtype=int))

class AppTestMultiDim(object):
    def setup_class(cls):
        py.test.skip("unimplemented")
        cls.space = gettestobjspace(usemodules=('micronumpy',))

    def test_multidim(self):
        from numpy import zeros
        ar = zeros((3, 3), dtype=int)
        assert ar[0, 2] == 0
        raises(IndexError, ar.__getitem__, (3, 0))
        assert ar[-2, 1] == 0

    def test_multidim_getset(self):
        from numpy import zeros
        ar = zeros((3, 3, 3), dtype=int)
        ar[1, 2, 1] = 3
        assert ar[1, 2, 1] == 3
        assert ar[-2, 2, 1] == 3
        assert ar[2, 2, 1] == 0
        assert ar[-2, 2, -2] == 3

    def test_len(self):
        from numpy import zeros
        assert len(zeros((3, 2, 1), dtype=int)) == 3

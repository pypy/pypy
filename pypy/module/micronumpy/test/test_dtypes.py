import py

from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest


class AppTestDtypes(BaseNumpyAppTest):
    def test_dtype(self):
        from numpy import dtype

        d = dtype('?')
        assert d.num == 0
        assert d.kind == 'b'
        assert dtype('int8').num == 1
        assert dtype(d) is d
        assert dtype(None) is dtype(float)

    def test_dtype_with_types(self):
        from numpy import dtype

        assert dtype(bool).num == 0
        assert dtype(long).num == 9
        assert dtype(float).num == 12

    def test_array_dtype_attr(self):
        from numpy import array, dtype

        a = array(range(5), long)
        assert a.dtype is dtype(long)

    def test_repr_str(self):
        from numpy import dtype

        d = dtype('?')
        assert repr(d) == "dtype('bool')"
        assert str(d) == "bool"

    def test_bool_array(self):
        from numpy import array

        a = array([0, 1, 2, 2.5], dtype='?')
        assert a[0] is False
        for i in xrange(1, 4):
            assert a[i] is True

    def test_copy_array_with_dtype(self):
        from numpy import array
        a = array([0, 1, 2, 3], dtype=long)
        assert isinstance(a[0], int)
        b = a.copy()
        assert isinstance(b[0], int)

        a = array([0, 1, 2, 3], dtype=bool)
        assert isinstance(a[0], bool)
        b = a.copy()
        assert isinstance(b[0], bool)

    def test_zeros_bool(self):
        from numpy import zeros
        a = zeros(10, dtype=bool)
        for i in range(10):
            assert a[i] is False

    def test_ones_bool(self):
        from numpy import ones
        a = ones(10, dtype=bool)
        for i in range(10):
            assert a[i] is True

    def test_zeros_long(self):
        from numpy import zeros
        a = zeros(10, dtype=long)
        for i in range(10):
            assert isinstance(a[i], int)
            assert a[1] == 0

    def test_ones_long(self):
        from numpy import ones
        a = ones(10, dtype=bool)
        for i in range(10):
            assert isinstance(a[i], int)
            assert a[1] == 1

    def test_add_int8(self):
        from numpy import array

        a = array(range(5), dtype="int8")
        b = a + a
        for i in range(5):
            assert b[i] == i * 2
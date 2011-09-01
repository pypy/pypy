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
        raises(TypeError, dtype, 1042)

    def test_dtype_with_types(self):
        from numpy import dtype

        assert dtype(bool).num == 0
        assert dtype(int).num == 7
        assert dtype(long).num == 9
        assert dtype(float).num == 12

    def test_array_dtype_attr(self):
        from numpy import array, dtype

        a = array(range(5), long)
        assert a.dtype is dtype(long)

    def test_repr_str(self):
        from numpy import dtype

        assert repr(dtype) == "<type 'numpy.dtype'>"
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
        # int on 64-bit, long in 32-bit
        assert isinstance(a[0], (int, long))
        b = a.copy()
        assert isinstance(b[0], (int, long))

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
            assert isinstance(a[i], (int, long))
            assert a[1] == 0

    def test_ones_long(self):
        from numpy import ones
        a = ones(10, dtype=bool)
        for i in range(10):
            assert isinstance(a[i], (int, long))
            assert a[1] == 1

    def test_overflow(self):
        from numpy import array
        assert array([128], 'b')[0] == -128
        assert array([256], 'B')[0] == 0
        assert array([32768], 'h')[0] == -32768
        assert array([65536], 'H')[0] == 0
        raises(OverflowError, "array([2147483648], 'i')")
        raises(OverflowError, "array([4294967296], 'I')")
        raises(OverflowError, "array([9223372036854775808], 'q')")
        raises(OverflowError, "array([18446744073709551616], 'Q')")

    def test_bool_binop_types(self):
        from numpy import array, dtype
        types = ('?','b','B','h','H','i','I','l','L','q','Q','f','d','g')
        N = len(types)
        a = array([True], '?')
        for t in types:
            assert (a + array([0], t)).dtype is dtype(t)

    def test_binop_types(self):
        from numpy import array, dtype
        tests = (('b','B','h'), ('b','h','h'), ('b','H','i'), ('b','I','q'),
                 ('b','Q','d'), ('B','H','H'), ('B','I','I'), ('B','Q','Q'),
                 ('B','h','h'), ('h','H','i'), ('h','i','i'), ('H','i','i'),
                 ('H','I','I'), ('i','I','q'), ('I','q','q'), ('q','Q','d'),
                 ('i','f','d'), ('q','f','d'), ('q','d','d'), ('Q','f','d'))
        for d1, d2, dout in tests:
            assert (array([1], d1) + array([1], d2)).dtype is dtype(dout)

    def test_add_int8(self):
        from numpy import array, dtype

        a = array(range(5), dtype="int8")
        b = a + a
        assert b.dtype is dtype("int8")
        for i in range(5):
            assert b[i] == i * 2

    def test_add_int16(self):
        from numpy import array, dtype

        a = array(range(5), dtype="int16")
        b = a + a
        assert b.dtype is dtype("int16")
        for i in range(5):
            assert b[i] == i * 2

    def test_add_uint32(self):
        from numpy import array, dtype

        a = array(range(5), dtype="I")
        b = a + a
        assert b.dtype is dtype("I")
        for i in range(5):
            assert b[i] == i * 2

    def test_shape(self):
        from numpy import dtype

        assert dtype(long).shape == ()

    def test_cant_subclass(self):
        from numpy import dtype

        # You can't subclass dtype
        raises(TypeError, type, "Foo", (dtype,), {})

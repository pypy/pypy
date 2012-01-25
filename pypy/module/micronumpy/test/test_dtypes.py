from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest


class AppTestDtypes(BaseNumpyAppTest):
    def test_dtype(self):
        from _numpypy import dtype

        d = dtype('?')
        assert d.num == 0
        assert d.kind == 'b'
        assert dtype('int8').num == 1
        assert dtype(d) is d
        assert dtype(None) is dtype(float)
        raises(TypeError, dtype, 1042)

    def test_dtype_with_types(self):
        from _numpypy import dtype

        assert dtype(bool).num == 0
        assert dtype(int).num == 7
        assert dtype(long).num == 9
        assert dtype(float).num == 12

    def test_array_dtype_attr(self):
        from _numpypy import array, dtype

        a = array(range(5), long)
        assert a.dtype is dtype(long)

    def test_repr_str(self):
        from _numpypy import dtype

        assert '.dtype' in repr(dtype)
        d = dtype('?')
        assert repr(d) == "dtype('bool')"
        assert str(d) == "bool"

    def test_bool_array(self):
        from _numpypy import array, False_, True_

        a = array([0, 1, 2, 2.5], dtype='?')
        assert a[0] is False_
        for i in xrange(1, 4):
            assert a[i] is True_

    def test_copy_array_with_dtype(self):
        from _numpypy import array, False_, True_, int64

        a = array([0, 1, 2, 3], dtype=long)
        # int on 64-bit, long in 32-bit
        assert isinstance(a[0], int64)
        b = a.copy()
        assert isinstance(b[0], int64)

        a = array([0, 1, 2, 3], dtype=bool)
        assert a[0] is False_
        b = a.copy()
        assert b[0] is False_

    def test_zeros_bool(self):
        from _numpypy import zeros, False_

        a = zeros(10, dtype=bool)
        for i in range(10):
            assert a[i] is False_

    def test_ones_bool(self):
        from _numpypy import ones, True_

        a = ones(10, dtype=bool)
        for i in range(10):
            assert a[i] is True_

    def test_zeros_long(self):
        from _numpypy import zeros, int64
        a = zeros(10, dtype=long)
        for i in range(10):
            assert isinstance(a[i], int64)
            assert a[1] == 0

    def test_ones_long(self):
        from _numpypy import ones, int64
        a = ones(10, dtype=long)
        for i in range(10):
            assert isinstance(a[i], int64)
            assert a[1] == 1

    def test_overflow(self):
        from _numpypy import array, dtype
        assert array([128], 'b')[0] == -128
        assert array([256], 'B')[0] == 0
        assert array([32768], 'h')[0] == -32768
        assert array([65536], 'H')[0] == 0
        if dtype('l').itemsize == 4: # 32-bit
            raises(OverflowError, "array([2**32/2], 'i')")
            raises(OverflowError, "array([2**32], 'I')")
        raises(OverflowError, "array([2**64/2], 'q')")
        raises(OverflowError, "array([2**64], 'Q')")

    def test_bool_binop_types(self):
        from _numpypy import array, dtype
        types = [
            '?', 'b', 'B', 'h', 'H', 'i', 'I', 'l', 'L', 'q', 'Q', 'f', 'd'
        ]
        a = array([True], '?')
        for t in types:
            assert (a + array([0], t)).dtype is dtype(t)

    def test_binop_types(self):
        from _numpypy import array, dtype
        tests = [('b','B','h'), ('b','h','h'), ('b','H','i'), ('b','i','i'),
                 ('b','l','l'), ('b','q','q'), ('b','Q','d'), ('B','h','h'),
                 ('B','H','H'), ('B','i','i'), ('B','I','I'), ('B','l','l'),
                 ('B','L','L'), ('B','q','q'), ('B','Q','Q'), ('h','H','i'),
                 ('h','i','i'), ('h','l','l'), ('h','q','q'), ('h','Q','d'),
                 ('H','i','i'), ('H','I','I'), ('H','l','l'), ('H','L','L'),
                 ('H','q','q'), ('H','Q','Q'), ('i','l','l'), ('i','q','q'),
                 ('i','Q','d'), ('I','L','L'), ('I','q','q'), ('I','Q','Q'),
                 ('q','Q','d'), ('b','f','f'), ('B','f','f'), ('h','f','f'),
                 ('H','f','f'), ('i','f','d'), ('I','f','d'), ('l','f','d'),
                 ('L','f','d'), ('q','f','d'), ('Q','f','d'), ('q','d','d')]
        if dtype('i').itemsize == dtype('l').itemsize: # 32-bit
            tests.extend([('b','I','q'), ('b','L','q'), ('h','I','q'),
                          ('h','L','q'), ('i','I','q'), ('i','L','q')])
        else:
            tests.extend([('b','I','l'), ('b','L','d'), ('h','I','l'),
                          ('h','L','d'), ('i','I','l'), ('i','L','d')])
        for d1, d2, dout in tests:
            assert (array([1], d1) + array([1], d2)).dtype is dtype(dout)

    def test_add_int8(self):
        from _numpypy import array, dtype

        a = array(range(5), dtype="int8")
        b = a + a
        assert b.dtype is dtype("int8")
        for i in range(5):
            assert b[i] == i * 2

    def test_add_int16(self):
        from _numpypy import array, dtype

        a = array(range(5), dtype="int16")
        b = a + a
        assert b.dtype is dtype("int16")
        for i in range(5):
            assert b[i] == i * 2

    def test_add_uint32(self):
        from _numpypy import array, dtype

        a = array(range(5), dtype="I")
        b = a + a
        assert b.dtype is dtype("I")
        for i in range(5):
            assert b[i] == i * 2

    def test_shape(self):
        from _numpypy import dtype

        assert dtype(long).shape == ()

    def test_cant_subclass(self):
        from _numpypy import dtype

        # You can't subclass dtype
        raises(TypeError, type, "Foo", (dtype,), {})

    def test_aliases(self):
        from _numpypy import dtype

        assert dtype("float") is dtype(float)


class AppTestTypes(BaseNumpyAppTest):
    def test_abstract_types(self):
        import _numpypy as numpy
        raises(TypeError, numpy.generic, 0)
        raises(TypeError, numpy.number, 0)
        raises(TypeError, numpy.integer, 0)
        exc = raises(TypeError, numpy.signedinteger, 0)
        assert str(exc.value) == "cannot create 'signedinteger' instances"
        exc = raises(TypeError, numpy.unsignedinteger, 0)
        assert str(exc.value) == "cannot create 'unsignedinteger' instances"

        raises(TypeError, numpy.floating, 0)
        raises(TypeError, numpy.inexact, 0)

    def test_new(self):
        import _numpypy as np
        assert np.int_(4) == 4
        assert np.float_(3.4) == 3.4

    def test_pow(self):
        from _numpypy import int_
        assert int_(4) ** 2 == 16

    def test_bool(self):
        import _numpypy as numpy

        assert numpy.bool_.mro() == [numpy.bool_, numpy.generic, object]
        assert numpy.bool_(3) is numpy.True_
        assert numpy.bool_("") is numpy.False_
        assert type(numpy.True_) is type(numpy.False_) is numpy.bool_

        class X(numpy.bool_):
            pass

        assert type(X(True)) is numpy.bool_
        assert X(True) is numpy.True_
        assert numpy.bool_("False") is numpy.True_

    def test_int8(self):
        import _numpypy as numpy

        assert numpy.int8.mro() == [numpy.int8, numpy.signedinteger, numpy.integer, numpy.number, numpy.generic, object]

        a = numpy.array([1, 2, 3], numpy.int8)
        assert type(a[1]) is numpy.int8
        assert numpy.dtype("int8").type is numpy.int8

        x = numpy.int8(128)
        assert x == -128
        assert x != 128
        assert type(x) is numpy.int8
        assert repr(x) == "-128"

        assert type(int(x)) is int
        assert int(x) == -128
        assert numpy.int8('50') == numpy.int8(50)
        raises(ValueError, numpy.int8, '50.2')
        assert numpy.int8('127') == 127
        assert numpy.int8('128') == -128

    def test_uint8(self):
        import _numpypy as numpy

        assert numpy.uint8.mro() == [numpy.uint8, numpy.unsignedinteger, numpy.integer, numpy.number, numpy.generic, object]

        a = numpy.array([1, 2, 3], numpy.uint8)
        assert type(a[1]) is numpy.uint8
        assert numpy.dtype("uint8").type is numpy.uint8

        x = numpy.uint8(128)
        assert x == 128
        assert x != -128
        assert type(x) is numpy.uint8
        assert repr(x) == "128"

        assert type(int(x)) is int
        assert int(x) == 128

        assert numpy.uint8(255) == 255
        assert numpy.uint8(256) == 0
        assert numpy.uint8('255') == 255
        assert numpy.uint8('256') == 0

    def test_int16(self):
        import _numpypy as numpy

        x = numpy.int16(3)
        assert x == 3
        assert numpy.int16(32767) == 32767
        assert numpy.int16(32768) == -32768
        assert numpy.int16('32767') == 32767
        assert numpy.int16('32768') == -32768

    def test_uint16(self):
        import _numpypy as numpy

        assert numpy.uint16(65535) == 65535
        assert numpy.uint16(65536) == 0
        assert numpy.uint16('65535') == 65535
        assert numpy.uint16('65536') == 0

    def test_int32(self):
        import sys
        import _numpypy as numpy

        x = numpy.int32(23)
        assert x == 23
        assert numpy.int32(2147483647) == 2147483647
        assert numpy.int32('2147483647') == 2147483647
        if sys.maxint > 2 ** 31 - 1:
            assert numpy.int32(2147483648) == -2147483648
            assert numpy.int32('2147483648') == -2147483648
        else:
            raises(OverflowError, numpy.int32, 2147483648)
            raises(OverflowError, numpy.int32, '2147483648')

    def test_uint32(self):
        import sys
        import _numpypy as numpy

        assert numpy.uint32(10) == 10

        if sys.maxint > 2 ** 31 - 1:
            assert numpy.uint32(4294967295) == 4294967295
            assert numpy.uint32(4294967296) == 0
            assert numpy.uint32('4294967295') == 4294967295
            assert numpy.uint32('4294967296') == 0

    def test_int_(self):
        import _numpypy as numpy

        assert numpy.int_ is numpy.dtype(int).type
        assert numpy.int_.mro() == [numpy.int_, numpy.signedinteger, numpy.integer, numpy.number, numpy.generic, int, object]

    def test_int64(self):
        import sys
        import _numpypy as numpy

        if sys.maxint == 2 ** 63 -1:
            assert numpy.int64.mro() == [numpy.int64, numpy.signedinteger, numpy.integer, numpy.number, numpy.generic, int, object]
        else:
            assert numpy.int64.mro() == [numpy.int64, numpy.signedinteger, numpy.integer, numpy.number, numpy.generic, object]

        assert numpy.dtype(numpy.int64).type is numpy.int64
        assert numpy.int64(3) == 3

        if sys.maxint >= 2 ** 63 - 1:
            assert numpy.int64(9223372036854775807) == 9223372036854775807
            assert numpy.int64('9223372036854775807') == 9223372036854775807
        else:
            raises(OverflowError, numpy.int64, 9223372036854775807)
            raises(OverflowError, numpy.int64, '9223372036854775807')

        raises(OverflowError, numpy.int64, 9223372036854775808)
        raises(OverflowError, numpy.int64, '9223372036854775808')

    def test_uint64(self):
        import sys
        import _numpypy as numpy

        assert numpy.uint64.mro() == [numpy.uint64, numpy.unsignedinteger, numpy.integer, numpy.number, numpy.generic, object]

        assert numpy.dtype(numpy.uint64).type is numpy.uint64
        skip("see comment")
        # These tests pass "by chance" on numpy, things that are larger than
        # platform long (i.e. a python int), don't get put in a normal box,
        # instead they become an object array containing a long, we don't have
        # yet, so these can't pass.
        assert numpy.uint64(9223372036854775808) == 9223372036854775808
        assert numpy.uint64(18446744073709551615) == 18446744073709551615
        raises(OverflowError, numpy.uint64(18446744073709551616))

    def test_float32(self):
        import _numpypy as numpy

        assert numpy.float32.mro() == [numpy.float32, numpy.floating, numpy.inexact, numpy.number, numpy.generic, object]

        assert numpy.float32(12) == numpy.float64(12)
        assert numpy.float32('23.4') == numpy.float32(23.4)
        raises(ValueError, numpy.float32, '23.2df')

    def test_float64(self):
        import _numpypy as numpy

        assert numpy.float64.mro() == [numpy.float64, numpy.floating, numpy.inexact, numpy.number, numpy.generic, float, object]

        a = numpy.array([1, 2, 3], numpy.float64)
        assert type(a[1]) is numpy.float64
        assert numpy.dtype(float).type is numpy.float64

        assert numpy.float64(2.0) == 2.0
        assert numpy.float64('23.4') == numpy.float64(23.4)
        raises(ValueError, numpy.float64, '23.2df')

    def test_subclass_type(self):
        import _numpypy as numpy

        class X(numpy.float64):
            def m(self):
                return self + 2

        b = X(10)
        assert type(b) is X
        assert b.m() == 12

    def test_long_as_index(self):
        from _numpypy import int_
        assert (1, 2, 3)[int_(1)] == 2

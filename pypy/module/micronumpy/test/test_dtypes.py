import py, sys
from pypy.conftest import option
from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest
from pypy.interpreter.gateway import interp2app

class BaseAppTestDtypes(BaseNumpyAppTest):
    def setup_class(cls):
        BaseNumpyAppTest.setup_class.im_func(cls)
        if option.runappdirect:
            import platform
            bits, linkage = platform.architecture()
            ptr_size = int(bits[:-3]) // 8
        else:
            from rpython.rtyper.lltypesystem import rffi
            ptr_size = rffi.sizeof(rffi.CCHARP)
        cls.w_ptr_size = cls.space.wrap(ptr_size)

class AppTestDtypes(BaseAppTestDtypes):
    def test_dtype(self):
        from _numpypy import dtype

        d = dtype('?')
        assert d.num == 0
        assert d.kind == 'b'
        assert dtype('int8').num == 1
        assert dtype(d) is d
        assert dtype(None) is dtype(float)
        assert dtype('int8').name == 'int8'
        assert dtype(int).fields is None
        assert dtype(int).names is None
        raises(TypeError, dtype, 1042)
        raises(KeyError, 'dtype(int)["asdasd"]')

    def test_dtype_eq(self):
        from _numpypy import dtype

        assert dtype("int8") == "int8"
        assert "int8" == dtype("int8")
        raises(TypeError, lambda: dtype("int8") == 3)
        assert dtype(bool) == bool

    def test_dtype_with_types(self):
        from _numpypy import dtype

        assert dtype(bool).num == 0
        if self.ptr_size == 4:
            assert dtype('intp').num == 5
            assert dtype('uintp').num == 6
            assert dtype('int32').num == 7
            assert dtype('uint32').num == 8
            assert dtype('int64').num == 9
            assert dtype('uint64').num == 10
        else:
            assert dtype('intp').num == 7
            assert dtype('uintp').num == 8
            assert dtype('int32').num == 5
            assert dtype('uint32').num == 6
            assert dtype('int64').num == 7
            assert dtype('uint64').num == 8
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
        from _numpypy import array, False_, longlong

        a = array([0, 1, 2, 3], dtype=long)
        # int on 64-bit, long in 32-bit
        assert isinstance(a[0], longlong)
        b = a.copy()
        assert isinstance(b[0], longlong)

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
        from _numpypy import zeros, longlong
        a = zeros(10, dtype=long)
        for i in range(10):
            assert isinstance(a[i], longlong)
            assert a[1] == 0

    def test_ones_long(self):
        from _numpypy import ones, longlong
        a = ones(10, dtype=long)
        for i in range(10):
            assert isinstance(a[i], longlong)
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
            '?', 'b', 'B', 'h', 'H', 'i', 'I', 'l', 'L', 'q', 'Q', 'f', 'd', 
            'e'
        ]
        if array([0], dtype='longdouble').itemsize > 8:
            types += ['g', 'G']
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
            # make a failed test print helpful info
            d3 = (array([1], d1) + array([1], d2)).dtype
            assert (d1, d2, repr(d3)) == (d1, d2, repr(dtype(dout)))

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

    def test_can_subclass(self):
        import _numpypy
        class xyz(_numpypy.void):
            pass
        assert True

    def test_aliases(self):
        from _numpypy import dtype

        assert dtype("float") is dtype(float)

    def test_index_int8(self):
        from _numpypy import array, int8

        a = array(range(10), dtype=int8)
        b = array([0] * 10, dtype=int8)
        for idx in b: a[idx] += 1

    def test_index_int16(self):
        from _numpypy import array, int16

        a = array(range(10), dtype=int16)
        b = array([0] * 10, dtype=int16)
        for idx in b: a[idx] += 1

    def test_index_int32(self):
        from _numpypy import array, int32

        a = array(range(10), dtype=int32)
        b = array([0] * 10, dtype=int32)
        for idx in b: a[idx] += 1

    def test_index_int64(self):
        from _numpypy import array, int64

        a = array(range(10), dtype=int64)
        b = array([0] * 10, dtype=int64)
        for idx in b:
            a[idx] += 1

    def test_hash(self):
        import _numpypy as numpy
        for tp, value in [
            (numpy.int8, 4),
            (numpy.int16, 5),
            (numpy.uint32, 7),
            (numpy.int64, 3),
            (numpy.float16, 10.),
            (numpy.float32, 2.0),
            (numpy.float64, 4.32),
            (numpy.longdouble, 4.32),
        ]:
            assert hash(tp(value)) == hash(value)


class AppTestTypes(BaseAppTestDtypes):
    def test_abstract_types(self):
        import _numpypy as numpy

        raises(TypeError, numpy.generic, 0)
        raises(TypeError, numpy.number, 0)
        raises(TypeError, numpy.integer, 0)
        exc = raises(TypeError, numpy.signedinteger, 0)
        assert 'cannot create' in str(exc.value)
        assert 'signedinteger' in str(exc.value)
        exc = raises(TypeError, numpy.unsignedinteger, 0)
        assert 'cannot create' in str(exc.value)
        assert 'unsignedinteger' in str(exc.value)
        raises(TypeError, numpy.floating, 0)
        raises(TypeError, numpy.inexact, 0)

        # numpy allows abstract types in array creation
        a_n = numpy.array([4,4], numpy.number)
        a_i = numpy.array([4,4], numpy.integer)
        a_s = numpy.array([4,4], numpy.signedinteger)
        a_u = numpy.array([4,4], numpy.unsignedinteger)

        assert a_n.dtype.num == 12
        assert a_i.dtype.num == 7
        assert a_s.dtype.num == 7
        assert a_u.dtype.num == 8

        assert a_n.dtype is numpy.dtype('float64')
        if self.ptr_size == 4:
            assert a_i.dtype is numpy.dtype('int32')
            assert a_s.dtype is numpy.dtype('int32')
            assert a_u.dtype is numpy.dtype('uint32')
        else:
            assert a_i.dtype is numpy.dtype('int64')
            assert a_s.dtype is numpy.dtype('int64')
            assert a_u.dtype is numpy.dtype('uint64')

        # too ambitious for now
        #a = numpy.array('xxxx', numpy.generic)
        #assert a.dtype is numpy.dtype('|V4')

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

        assert numpy.int8.mro() == [numpy.int8, numpy.signedinteger,
                                    numpy.integer, numpy.number, 
                                    numpy.generic, object]

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

        assert numpy.uint8.mro() == [numpy.uint8, numpy.unsignedinteger, 
                                     numpy.integer, numpy.number, 
                                     numpy.generic, object]

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
        assert numpy.dtype('int32') is numpy.dtype(numpy.int32)

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
        assert numpy.int_.mro() == [numpy.int_, numpy.signedinteger, 
                                    numpy.integer, numpy.number, 
                                    numpy.generic, int, object]

    def test_int64(self):
        import sys
        import _numpypy as numpy

        if sys.maxint == 2 ** 63 -1:
            assert numpy.int64.mro() == [numpy.int64, numpy.signedinteger, 
                                         numpy.integer, numpy.number, 
                                         numpy.generic, int, object]
        else:
            assert numpy.int64.mro() == [numpy.int64, numpy.signedinteger, 
                                         numpy.integer, numpy.number, 
                                         numpy.generic, object]

        assert numpy.dtype(numpy.int64).type is numpy.int64
        assert numpy.int64(3) == 3

        assert numpy.int64(9223372036854775807) == 9223372036854775807
        assert numpy.int64(9223372036854775807) == 9223372036854775807

        raises(OverflowError, numpy.int64, 9223372036854775808)
        raises(OverflowError, numpy.int64, 9223372036854775808L)

    def test_uint64(self):
        import sys
        import _numpypy as numpy

        assert numpy.uint64.mro() == [numpy.uint64, numpy.unsignedinteger, 
                                      numpy.integer, numpy.number, 
                                      numpy.generic, object]

        assert numpy.dtype(numpy.uint64).type is numpy.uint64
        skip("see comment")
        # These tests pass "by chance" on numpy, things that are larger than
        # platform long (i.e. a python int), don't get put in a normal box,
        # instead they become an object array containing a long, we don't have
        # yet, so these can't pass.
        assert numpy.uint64(9223372036854775808) == 9223372036854775808
        assert numpy.uint64(18446744073709551615) == 18446744073709551615
        raises(OverflowError, numpy.uint64(18446744073709551616))

    def test_float16(self):
        import _numpypy as numpy
        assert numpy.float16.mro() == [numpy.float16, numpy.floating, 
                                       numpy.inexact, numpy.number, 
                                       numpy.generic, object]

        assert numpy.float16(12) == numpy.float64(12)
        assert numpy.float16('23.4') == numpy.float16(23.4)
        raises(ValueError, numpy.float16, '23.2df')


    def test_float32(self):
        import _numpypy as numpy

        assert numpy.float32.mro() == [numpy.float32, numpy.floating, 
                                       numpy.inexact, numpy.number, 
                                       numpy.generic, object]

        assert numpy.float32(12) == numpy.float64(12)
        assert numpy.float32('23.4') == numpy.float32(23.4)
        raises(ValueError, numpy.float32, '23.2df')

    def test_float64(self):
        import _numpypy as numpy

        assert numpy.float64.mro() == [numpy.float64, numpy.floating, 
                                       numpy.inexact, numpy.number, 
                                       numpy.generic, float, object]

        a = numpy.array([1, 2, 3], numpy.float64)
        assert type(a[1]) is numpy.float64
        assert numpy.dtype(float).type is numpy.float64

        assert "{:3f}".format(numpy.float64(3)) == "3.000000"

        assert numpy.float64(2.0) == 2.0
        assert numpy.float64('23.4') == numpy.float64(23.4)
        raises(ValueError, numpy.float64, '23.2df')

    def test_float_None(self):
        import _numpypy as numpy
        from math import isnan
        assert isnan(numpy.float32(None))
        assert isnan(numpy.float64(None))
        assert isnan(numpy.longdouble(None))

    def test_longfloat(self):
        import _numpypy as numpy
        # it can be float96 or float128
        if numpy.longfloat != numpy.float64:
            assert numpy.longfloat.mro()[1:] == [numpy.floating,
                                       numpy.inexact, numpy.number, 
                                       numpy.generic, object]
        a = numpy.array([1, 2, 3], numpy.longdouble)
        assert repr(type(a[1])) == repr(numpy.longdouble)
        assert numpy.float64(12) == numpy.longdouble(12)
        assert numpy.float64(12) == numpy.longfloat(12)
        raises(ValueError, numpy.longfloat, '23.2df')

    def test_complex_floating(self):
        import _numpypy as numpy

        assert numpy.complexfloating.__mro__ == (numpy.complexfloating,
            numpy.inexact, numpy.number, numpy.generic, object)

    def test_complex_format(self):
        import sys
        import _numpypy as numpy

        for complex_ in (numpy.complex128, numpy.complex64,):
            for real, imag, should in [
                (1, 2, '(1+2j)'),
                (0, 1, '1j'),
                (1, 0, '(1+0j)'),
                (-1, -2, '(-1-2j)'),
                (0.5, -0.75, '(0.5-0.75j)'),
                #xxx
                #(numpy.inf, numpy.inf, '(inf+inf*j)'),
                ]:

                c = complex_(complex(real, imag))
                assert c == complex(real, imag)
                assert c.real == real
                assert c.imag == imag
                assert repr(c) == should

        real, imag, should = (1e100, 3e66, '(1e+100+3e+66j)')
        c128 = numpy.complex128(complex(real, imag))
        assert type(c128.real) is type(c128.imag) is numpy.float64
        assert c128.real == real
        assert c128.imag == imag
        assert repr(c128) == should

        c64 = numpy.complex64(complex(real, imag))
        assert repr(c64.real) == 'inf'  
        assert type(c64.real) is type(c64.imag) is numpy.float32
        assert repr(c64.imag).startswith('inf')
        assert repr(c64) in ('(inf+inf*j)', '(inf+infj)')


        assert numpy.complex128(1.2) == numpy.complex128(complex(1.2, 0))
        assert numpy.complex64(1.2) == numpy.complex64(complex(1.2, 0))
        raises((ValueError, TypeError), numpy.array, [3+4j], dtype=float)
        if sys.version_info >= (2, 7):
            assert "{:g}".format(numpy.complex_(0.5+1.5j)) == '{:g}'.format(0.5+1.5j)

    def test_complex(self):
        import _numpypy as numpy

        assert numpy.complex_ is numpy.complex128
        assert numpy.complex64.__mro__ == (numpy.complex64,
            numpy.complexfloating, numpy.inexact, numpy.number, numpy.generic,
            object)
        assert numpy.complex128.__mro__ == (numpy.complex128,
            numpy.complexfloating, numpy.inexact, numpy.number, numpy.generic,
            complex, object)

        assert numpy.dtype(complex).type is numpy.complex128
        assert numpy.dtype("complex").type is numpy.complex128
        d = numpy.dtype('complex64')
        assert d.kind == 'c'
        assert d.num == 14
        assert d.char == 'F'

    def test_subclass_type(self):
        import _numpypy as numpy

        class X(numpy.float64):
            def m(self):
                return self + 2

        b = X(10)
        assert type(b) is X
        assert b.m() == 12

    def test_long_as_index(self):
        from _numpypy import int_, float64
        assert (1, 2, 3)[int_(1)] == 2
        raises(TypeError, lambda: (1, 2, 3)[float64(1)])

    def test_int(self):
        from _numpypy import int32, int64, int_
        import sys
        assert issubclass(int_, int)
        if sys.maxint == (1<<31) - 1:
            assert issubclass(int32, int)
            assert int_ is int32
        else:
            assert issubclass(int64, int)
            assert int_ is int64

    def test_various_types(self):
        import _numpypy as numpy

        assert numpy.bool is bool
        assert numpy.int is int

        assert numpy.int16 is numpy.short
        assert numpy.int8 is numpy.byte
        assert numpy.bool_ is numpy.bool8
        if self.ptr_size == 4:
            assert numpy.intp is numpy.int32
            assert numpy.uintp is numpy.uint32
        elif self.ptr_size == 8:
            assert numpy.intp is numpy.int64
            assert numpy.uintp is numpy.uint64

    def test_mro(self):
        import _numpypy as numpy

        assert numpy.int16.__mro__ == (numpy.int16, numpy.signedinteger,
                                       numpy.integer, numpy.number,
                                       numpy.generic, object)
        assert numpy.bool_.__mro__ == (numpy.bool_, numpy.generic, object)

    def test_operators(self):
        from operator import truediv
        from _numpypy import float64, int_, True_, False_
        assert 5 / int_(2) == int_(2)
        assert truediv(int_(3), int_(2)) == float64(1.5)
        assert truediv(3, int_(2)) == float64(1.5)
        assert int_(8) % int_(3) == int_(2)
        assert 8 % int_(3) == int_(2)
        assert divmod(int_(8), int_(3)) == (int_(2), int_(2))
        assert divmod(8, int_(3)) == (int_(2), int_(2))
        assert 2 ** int_(3) == int_(8)
        assert int_(3) << int_(2) == int_(12)
        assert 3 << int_(2) == int_(12)
        assert int_(8) >> int_(2) == int_(2)
        assert 8 >> int_(2) == int_(2)
        assert int_(3) & int_(1) == int_(1)
        assert 2 & int_(3) == int_(2)
        assert int_(2) | int_(1) == int_(3)
        assert 2 | int_(1) == int_(3)
        assert int_(3) ^ int_(5) == int_(6)
        assert True_ ^ False_ is True_
        assert 5 ^ int_(3) == int_(6)
        assert +int_(3) == int_(3)
        assert ~int_(3) == int_(-4)
        raises(TypeError, lambda: float64(3) & 1)

    def test_alternate_constructs(self):
        from _numpypy import dtype
        nnp = self.non_native_prefix
        byteorder = self.native_prefix
        assert dtype('i8') == dtype(byteorder + 'i8') == dtype('=i8') # XXX should be equal == dtype(long)
        assert dtype(nnp + 'i8') != dtype('i8')
        assert dtype(nnp + 'i8').byteorder == nnp
        assert dtype('=i8').byteorder == '='
        assert dtype(byteorder + 'i8').byteorder == '='

    def test_intp(self):
        from _numpypy import dtype
        assert dtype('p') == dtype('intp')
        assert dtype('P') == dtype('uintp')

    def test_alignment(self):
        from _numpypy import dtype
        assert dtype('i4').alignment == 4

class AppTestStrUnicodeDtypes(BaseNumpyAppTest):
    def test_str_unicode(self):
        from _numpypy import str_, unicode_, character, flexible, generic

        assert str_.mro() == [str_, str, basestring, character, flexible, generic, object]
        assert unicode_.mro() == [unicode_, unicode, basestring, character, flexible, generic, object]

    def test_str_dtype(self):
        from _numpypy import dtype, str_

        raises(TypeError, "dtype('Sx')")
        d = dtype('S8')
        assert d.itemsize == 8
        assert dtype(str) == dtype('S')
        assert d.kind == 'S'
        assert d.type is str_
        assert d.name == "string64"
        assert d.num == 18

    def test_unicode_dtype(self):
        from _numpypy import dtype, unicode_

        raises(TypeError, "dtype('Ux')")
        d = dtype('U8')
        assert d.itemsize == 8 * 4
        assert dtype(unicode) == dtype('U')
        assert d.kind == 'U'
        assert d.type is unicode_
        assert d.name == "unicode256"
        assert d.num == 19

    def test_string_boxes(self):
        from _numpypy import str_
        assert isinstance(str_(3), str_)

    def test_unicode_boxes(self):
        from _numpypy import unicode_
        assert isinstance(unicode_(3), unicode)

class AppTestRecordDtypes(BaseNumpyAppTest):
    def test_create(self):
        from _numpypy import dtype, void

        raises(ValueError, "dtype([('x', int), ('x', float)])")
        d = dtype([("x", "int32"), ("y", "int32"), ("z", "int32"), ("value", float)])
        assert d.fields['x'] == (dtype('int32'), 0)
        assert d.fields['value'] == (dtype(float), 12)
        assert d['x'] == dtype('int32')
        assert d.name == "void160"
        assert d.num == 20
        assert d.itemsize == 20
        assert d.kind == 'V'
        assert d.type is void
        assert d.char == 'V'
        assert d.names == ("x", "y", "z", "value")
        raises(KeyError, 'd["xyz"]')
        raises(KeyError, 'd.fields["xyz"]')

    def test_create_from_dict(self):
        skip("not yet")
        from _numpypy import dtype
        d = dtype({'names': ['a', 'b', 'c'],
                   })

class AppTestNotDirect(BaseNumpyAppTest):
    def setup_class(cls):
        BaseNumpyAppTest.setup_class.im_func(cls)
        def check_non_native(w_obj, w_obj2):
            stor1 = w_obj.implementation.storage
            stor2 = w_obj2.implementation.storage
            assert stor1[0] == stor2[1]
            assert stor1[1] == stor2[0]
            if stor1[0] == '\x00':
                assert stor2[1] == '\x00'
                assert stor2[0] == '\x01'
            else:
                assert stor2[1] == '\x01'
                assert stor2[0] == '\x00'
        if option.runappdirect:
            cls.w_check_non_native = lambda *args : None
        else:
            cls.w_check_non_native = cls.space.wrap(interp2app(check_non_native))

    def test_non_native(self):
        from _numpypy import array
        a = array([1, 2, 3], dtype=self.non_native_prefix + 'i2')
        assert a[0] == 1
        assert (a + a)[1] == 4
        self.check_non_native(a, array([1, 2, 3], 'i2'))
        a = array([1, 2, 3], dtype=self.non_native_prefix + 'f8')
        assert a[0] == 1
        assert (a + a)[1] == 4
        a = array([1, 2, 3], dtype=self.non_native_prefix + 'f4')
        assert a[0] == 1
        assert (a + a)[1] == 4
        a = array([1, 2, 3], dtype=self.non_native_prefix + 'f2')
        assert a[0] == 1
        assert (a + a)[1] == 4
        a = array([1, 2, 3], dtype=self.non_native_prefix + 'g') # longdouble
        assert a[0] == 1
        assert (a + a)[1] == 4
        a = array([1, 2, 3], dtype=self.non_native_prefix + 'G') # clongdouble
        assert a[0] == 1
        assert (a + a)[1] == 4

class AppTestPyPyOnly(BaseNumpyAppTest):
    def setup_class(cls):
        if option.runappdirect and '__pypy__' not in sys.builtin_module_names:
            py.test.skip("pypy only test")
        BaseNumpyAppTest.setup_class.im_func(cls)

    def test_typeinfo(self):
        from _numpypy import typeinfo, void, number, int64, bool_
        assert typeinfo['Number'] == number
        assert typeinfo['LONGLONG'] == ('q', 9, 64, 8, 9223372036854775807L, -9223372036854775808L, int64)
        assert typeinfo['VOID'] == ('V', 20, 0, 1, void)
        assert typeinfo['BOOL'] == ('?', 0, 8, 1, 1, 0, bool_)

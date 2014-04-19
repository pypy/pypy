from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestScalar(BaseNumpyAppTest):
    spaceconfig = dict(usemodules=["micronumpy", "binascii", "struct"])

    def test_init(self):
        import numpy as np
        import math
        import sys
        assert np.intp() == np.intp(0)
        assert np.intp('123') == np.intp(123)
        raises(TypeError, np.intp, None)
        assert np.float64() == np.float64(0)
        assert math.isnan(np.float64(None))
        assert np.bool_() == np.bool_(False)
        assert np.bool_('abc') == np.bool_(True)
        assert np.bool_(None) == np.bool_(False)
        assert np.complex_() == np.complex_(0)
        #raises(TypeError, np.complex_, '1+2j')
        assert math.isnan(np.complex_(None))
        for c in ['i', 'I', 'l', 'L', 'q', 'Q']:
            assert np.dtype(c).type().dtype.char == c
        for c in ['l', 'q']:
            assert np.dtype(c).type(sys.maxint) == sys.maxint
        for c in ['L', 'Q']:
            assert np.dtype(c).type(sys.maxint + 42) == sys.maxint + 42
        assert np.float32(np.array([True, False])).dtype == np.float32
        assert type(np.float32(np.array([True]))) is np.ndarray
        assert type(np.float32(1.0)) is np.float32
        a = np.array([True, False])
        assert np.bool_(a) is a

    def test_builtin(self):
        import numpy as np
        assert int(np.str_('12')) == 12
        exc = raises(ValueError, "int(np.str_('abc'))")
        assert exc.value.message.startswith('invalid literal for int()')
        assert int(np.uint64((2<<63) - 1)) == (2<<63) - 1
        exc = raises(ValueError, "int(np.float64(np.nan))")
        assert str(exc.value) == "cannot convert float NaN to integer"
        exc = raises(OverflowError, "int(np.float64(np.inf))")
        assert str(exc.value) == "cannot convert float infinity to integer"
        assert int(np.float64(1e100)) == int(1e100)
        assert long(np.float64(1e100)) == int(1e100)
        assert int(np.complex128(1e100+2j)) == int(1e100)
        exc = raises(OverflowError, "int(np.complex64(1e100+2j))")
        assert str(exc.value) == "cannot convert float infinity to integer"
        assert int(np.str_('100000000000000000000')) == 100000000000000000000
        assert long(np.str_('100000000000000000000')) == 100000000000000000000

        assert float(np.float64(1e100)) == 1e100
        assert float(np.complex128(1e100+2j)) == 1e100
        assert float(np.str_('1e100')) == 1e100
        assert float(np.str_('inf')) == np.inf
        assert str(float(np.float64(np.nan))) == 'nan'

        assert oct(np.int32(11)) == '013'
        assert oct(np.float32(11.6)) == '013'
        assert oct(np.complex64(11-12j)) == '013'
        assert hex(np.int32(11)) == '0xb'
        assert hex(np.float32(11.6)) == '0xb'
        assert hex(np.complex64(11-12j)) == '0xb'
        assert bin(np.int32(11)) == '0b1011'
        exc = raises(TypeError, "bin(np.float32(11.6))")
        assert "index" in exc.value.message
        exc = raises(TypeError, "len(np.int32(11))")
        assert "has no len" in exc.value.message
        assert len(np.string_('123')) == 3

    def test_pickle(self):
        from numpy import dtype, zeros
        try:
            from numpy.core.multiarray import scalar
        except ImportError:
            # running on dummy module
            from numpy import scalar
        from cPickle import loads, dumps
        i = dtype('int32').type(1337)
        f = dtype('float64').type(13.37)
        c = dtype('complex128').type(13 + 37.j)

        assert i.__reduce__() == (scalar, (dtype('int32'), '9\x05\x00\x00'))
        assert f.__reduce__() == (scalar, (dtype('float64'), '=\n\xd7\xa3p\xbd*@'))
        assert c.__reduce__() == (scalar, (dtype('complex128'), '\x00\x00\x00\x00\x00\x00*@\x00\x00\x00\x00\x00\x80B@'))

        assert loads(dumps(i)) == i
        assert loads(dumps(f)) == f
        assert loads(dumps(c)) == c

        a = zeros(3)
        assert loads(dumps(a.sum())) == a.sum()

    def test_round(self):
        import numpy as np
        i = np.dtype('int32').type(1337)
        f = np.dtype('float64').type(13.37)
        c = np.dtype('complex128').type(13 + 37.j)
        b = np.dtype('bool').type(1)
        assert i.round(decimals=-2) == 1300
        assert i.round(decimals=1) == 1337
        assert c.round() == c
        assert f.round() == 13.
        assert f.round(decimals=-1) == 10.
        assert f.round(decimals=1) == 13.4
        assert f.round(decimals=1, out=None) == 13.4
        assert b.round() == 1.0
        assert b.round(decimals=5) is b

    def test_astype(self):
        import numpy as np
        a = np.bool_(True).astype(np.float32)
        assert type(a) is np.float32
        assert a == 1.0
        a = np.bool_(True).astype('int32')
        assert type(a) is np.int32
        assert a == 1
        a = np.str_('123').astype('int32')
        assert type(a) is np.int32
        assert a == 123

    def test_copy(self):
        import numpy as np
        a = np.int32(2)
        b = a.copy()
        assert type(b) is type(a)
        assert b == a
        assert b is not a

    def test_methods(self):
        import numpy as np
        for a in [np.int32(2), np.float64(2.0), np.complex64(42)]:
            for op in ['min', 'max', 'sum', 'prod']:
                assert getattr(a, op)() == a
            for op in ['argmin', 'argmax']:
                b = getattr(a, op)()
                assert type(b) is np.int_
                assert b == 0

    def test_buffer(self):
        import numpy as np
        a = np.int32(123)
        b = buffer(a)
        assert type(b) is buffer
        a = np.string_('abc')
        b = buffer(a)
        assert str(b) == a

    def test_byteswap(self):
        import numpy as np
        assert np.int64(123).byteswap() == 8863084066665136128
        a = np.complex64(1+2j).byteswap()
        assert repr(a.real).startswith('4.60060')
        assert repr(a.imag).startswith('8.96831')

    def test_squeeze(self):
        import numpy as np
        assert np.True_.squeeze() is np.True_
        a = np.float32(1.0)
        assert a.squeeze() is a
        raises(TypeError, a.squeeze, 2)

    def test_bitshift(self):
        import numpy as np
        assert np.int32(123) >> 1 == 61
        assert type(np.int32(123) >> 1) is np.int_
        assert np.int64(123) << 1 == 246
        assert type(np.int64(123) << 1) is np.int64
        exc = raises(TypeError, "np.uint64(123) >> 1")
        assert 'not supported for the input types' in exc.value.message

    def test_attributes(self):
        import numpy as np
        value = np.dtype('int64').type(12345)
        assert value.dtype == np.dtype('int64')
        assert value.size == 1
        assert value.itemsize == 8
        assert value.nbytes == 8
        assert value.shape == ()
        assert value.strides == ()
        assert value.ndim == 0
        assert value.T is value

    def test_indexing(self):
        import numpy as np
        v = np.int32(2)
        for b in [v[()], v[...]]:
            assert isinstance(b, np.ndarray)
            assert b.shape == ()
            assert b == v
        raises(IndexError, "v['blah']")

    def test_realimag(self):
        import numpy as np
        a = np.int64(2)
        assert a.real == 2
        assert a.imag == 0
        a = np.float64(2.5)
        assert a.real == 2.5
        assert a.imag == 0.0
        a = np.complex64(2.5-1.5j)
        assert a.real == 2.5
        assert a.imag == -1.5

    def test_view(self):
        import numpy as np
        import sys
        s = np.dtype('int64').type(12)
        exc = raises(ValueError, s.view, 'int8')
        assert exc.value[0] == "new type not compatible with array."
        t = s.view('double')
        assert type(t) is np.double
        assert t < 7e-323
        t = s.view('complex64')
        assert type(t) is np.complex64
        assert 0 < t.real < 1
        assert t.imag == 0
        exc = raises(TypeError, s.view, 'string')
        assert exc.value[0] == "data-type must not be 0-sized"
        t = s.view('S8')
        assert type(t) is np.string_
        assert t == '\x0c'
        s = np.dtype('string').type('abc1')
        assert s.view('S4') == 'abc1'
        if '__pypy__' in sys.builtin_module_names:
            raises(NotImplementedError, s.view, [('a', 'i2'), ('b', 'i2')])
        else:
            b = s.view([('a', 'i2'), ('b', 'i2')])
            assert b.shape == ()
            assert b[0] == 25185
            assert b[1] == 12643
        if '__pypy__' in sys.builtin_module_names:
            raises(TypeError, "np.dtype([('a', 'int64'), ('b', 'int64')]).type('a' * 16)")
        else:
            s = np.dtype([('a', 'int64'), ('b', 'int64')]).type('a' * 16)
            assert s.view('S16') == 'a' * 16

    def test_as_integer_ratio(self):
        import numpy as np
        raises(AttributeError, 'np.float32(1.5).as_integer_ratio()')
        assert np.float64(1.5).as_integer_ratio() == (3, 2)

    def test_tostring(self):
        import numpy as np
        assert np.int64(123).tostring() == np.array(123, dtype='i8').tostring()
        assert np.int64(123).tostring('C') == np.array(123, dtype='i8').tostring()
        assert np.float64(1.5).tostring() == np.array(1.5, dtype=float).tostring()
        exc = raises(TypeError, 'np.int64(123).tostring("Z")')
        assert exc.value[0] == 'order not understood'

    def test_reshape(self):
        import numpy as np
        assert np.int64(123).reshape((1,)) == 123
        assert np.int64(123).reshape(1).shape == (1,)
        assert np.int64(123).reshape((1,)).shape == (1,)
        exc = raises(ValueError, "np.int64(123).reshape((2,))")
        assert exc.value[0] == 'total size of new array must be unchanged'

    def test_complex_scalar_complex_cast(self):
        import numpy as np
        for tp in [np.csingle, np.cdouble, np.clongdouble]:
            x = tp(1+2j)
            assert hasattr(x, '__complex__') == (tp != np.cdouble)
            assert complex(x) == 1+2j

    def test_complex_str_format(self):
        import numpy as np
        for t in [np.complex64, np.complex128]:
            assert str(t(complex(1, float('nan')))) == '(1+nan*j)'
            assert str(t(complex(1, float('-nan')))) == '(1+nan*j)'
            assert str(t(complex(1, float('inf')))) == '(1+inf*j)'
            assert str(t(complex(1, float('-inf')))) == '(1-inf*j)'
            for x in [0, 1, -1]:
                assert str(t(complex(x))) == str(complex(x))
                assert str(t(x*1j)) == str(complex(x*1j))
                assert str(t(x + x*1j)) == str(complex(x + x*1j))

    def test_complex_zero_division(self):
        import numpy as np
        for t in [np.complex64, np.complex128]:
            a = t(0.0)
            b = t(1.0)
            assert np.isinf(b/a)
            b = t(complex(np.inf, np.inf))
            assert np.isinf(b/a)
            b = t(complex(np.inf, np.nan))
            assert np.isinf(b/a)
            b = t(complex(np.nan, np.inf))
            assert np.isinf(b/a)
            b = t(complex(np.nan, np.nan))
            assert np.isnan(b/a)
            b = t(0.)
            assert np.isnan(b/a)

from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestScalar(BaseNumpyAppTest):
    spaceconfig = dict(usemodules=["micronumpy", "binascii", "struct"])

    def test_init(self):
        import numpypy as np
        import math
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

    def test_pickle(self):
        from numpypy import dtype, zeros
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

    def test_squeeze(self):
        import numpy as np
        assert np.True_.squeeze() is np.True_
        a = np.float32(1.0)
        assert a.squeeze() is a
        raises(TypeError, a.squeeze, 2)

    def test_attributes(self):
        import numpypy as np
        value = np.dtype('int64').type(12345)
        assert value.dtype == np.dtype('int64')
        assert value.itemsize == 8
        assert value.nbytes == 8
        assert value.shape == ()
        assert value.strides == ()
        assert value.ndim == 0
        assert value.T is value

    def test_complex_scalar_complex_cast(self):
        import numpy as np
        for tp in [np.csingle, np.cdouble, np.clongdouble]:
            x = tp(1+2j)
            assert hasattr(x, '__complex__') == (tp != np.cdouble)
            assert complex(x) == 1+2j

    def test_complex_str_format(self):
        import numpy as np
        assert str(np.complex128(complex(1, float('nan')))) == '(1+nan*j)'
        assert str(np.complex128(complex(1, float('-nan')))) == '(1+nan*j)'
        assert str(np.complex128(complex(1, float('inf')))) == '(1+inf*j)'
        assert str(np.complex128(complex(1, float('-inf')))) == '(1-inf*j)'

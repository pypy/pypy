from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestScalar(BaseNumpyAppTest):
    spaceconfig = dict(usemodules=["micronumpy", "binascii", "struct"])

    def test_pickle(self):
        from numpypy import dtype, int32, float64, complex128, zeros, sum
        from numpypy.core.multiarray import scalar
        from cPickle import loads, dumps
        i = int32(1337)
        f = float64(13.37)
        c = complex128(13 + 37.j)

        assert i.__reduce__() == (scalar, (dtype('int32'), '9\x05\x00\x00'))
        assert f.__reduce__() == (scalar, (dtype('float64'), '=\n\xd7\xa3p\xbd*@'))
        assert c.__reduce__() == (scalar, (dtype('complex128'), '\x00\x00\x00\x00\x00\x00*@\x00\x00\x00\x00\x00\x80B@'))

        assert loads(dumps(i)) == i
        assert loads(dumps(f)) == f
        assert loads(dumps(c)) == c

        a = zeros(3)
        assert loads(dumps(sum(a))) == sum(a)

    def test_round(self):
        from numpypy import int32, float64, complex128, bool
        i = int32(1337)
        f = float64(13.37)
        c = complex128(13 + 37.j)
        b = bool(0)
        assert i.round(decimals=-2) == 1300
        assert i.round(decimals=1) == 1337
        assert c.round() == c
        assert f.round() == 13.
        assert f.round(decimals=-1) == 10.
        assert f.round(decimals=1) == 13.4
        exc = raises(AttributeError, 'b.round()')
        assert exc.value[0] == "'bool' object has no attribute 'round'"

    def test_itemsize(self):
        import numpypy as np
        assert np.int64(0).itemsize == 8

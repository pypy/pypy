from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestScalar(BaseNumpyAppTest):
    spaceconfig = dict(usemodules=["micronumpy", "binascii", "struct"])

    def test_pickle(self):
        from numpypy import dtype, int32, float64, complex128
        from numpypy.core.multiarray import scalar
        assert int32(1337).__reduce__() == (scalar, (dtype('int32'), '9\x05\x00\x00'))
        assert float64(13.37).__reduce__() == (scalar, (dtype('float64'), '=\n\xd7\xa3p\xbd*@'))
        assert complex128(13 + 37.j).__reduce__() == (scalar, (dtype('complex128'), '\x00\x00\x00\x00\x00\x00*@\x00\x00\x00\x00\x00\x80B@'))

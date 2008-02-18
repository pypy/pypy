# Test specifically-sized containers.

from ctypes import *
from support import BaseCTypesTestChecker

class TestSizes(BaseCTypesTestChecker):
    def test_8(self):
        assert 1 == sizeof(c_int8)
        assert 1 == sizeof(c_uint8)

    def test_16(self):
        assert 2 == sizeof(c_int16)
        assert 2 == sizeof(c_uint16)

    def test_32(self):
        assert 4 == sizeof(c_int32)
        assert 4 == sizeof(c_uint32)

    def test_64(self):
        assert 8 == sizeof(c_int64)
        assert 8 == sizeof(c_uint64)

    def test_size_t(self):
        assert sizeof(c_void_p) == sizeof(c_size_t)

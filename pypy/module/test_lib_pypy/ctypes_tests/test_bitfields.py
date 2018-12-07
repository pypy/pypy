import pytest
from ctypes import *


class TestBitField:
    def test_set_fields_attr(self):
        class A(Structure):
            pass
        A._fields_ = [("a", c_byte),
                      ("b", c_ubyte)]

    def test_set_fields_attr_bitfields(self):
        class A(Structure):
            pass
        A._fields_ = [("a", POINTER(A)),
                      ("b", c_ubyte, 4)]

    def test_set_fields_cycle_fails(self):
        class A(Structure):
            pass
        with pytest.raises(AttributeError):
            A._fields_ = [("a", A)]

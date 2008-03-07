from support import WhiteBoxTests

from ctypes import *

# WhiteBoxTests

class TestCTypesBase(WhiteBoxTests):
    def test_pointer(self):
        p = pointer(pointer(c_int(2)))
        x = p[0]
        assert x._base is p

    def test_structure(self):
        class X(Structure):
            _fields_ = [('x', POINTER(c_int)),
                        ('y', POINTER(c_int))]

        x = X()
        assert x.y._base is x
        assert x.y._index == 1
    
    def test_array(self):
        X = POINTER(c_int) * 24
        x = X()
        assert x[16]._base is x
        assert x[16]._index == 16

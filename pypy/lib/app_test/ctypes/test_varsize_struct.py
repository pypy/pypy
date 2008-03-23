import py
from support import BaseCTypesTestChecker
from ctypes import *

class TestVarSize(BaseCTypesTestChecker):
    def test_resize(self):
        py.test.skip("resizing not implemented")
        class X(Structure):
            _fields_ = [("item", c_int),
                        ("array", c_int * 1)]

        assert sizeof(X) == sizeof(c_int) * 2
        x = X()
        x.item = 42
        x.array[0] = 100
        assert sizeof(x) == sizeof(c_int) * 2

        # make room for one additional item
        new_size = sizeof(X) + sizeof(c_int) * 1
        resize(x, new_size)
        assert sizeof(x) == new_size
        assert (x.item, x.array[0]) == (42, 100)

        # make room for 10 additional items
        new_size = sizeof(X) + sizeof(c_int) * 9
        resize(x, new_size)
        assert sizeof(x) == new_size
        assert (x.item, x.array[0]) == (42, 100)

        # make room for one additional item
        new_size = sizeof(X) + sizeof(c_int) * 1
        resize(x, new_size)
        assert sizeof(x) == new_size
        assert (x.item, x.array[0]) == (42, 100)

    def test_array_invalid_length(self):
        # cannot create arrays with non-positive size
        raises(ValueError, lambda: c_int * -1)
        raises(ValueError, lambda: c_int * -3)

    def test_zerosized_array(self):
        array = (c_int * 0)()
        # accessing elements of zero-sized arrays raise IndexError
        raises(IndexError, array.__setitem__, 0, None)
        raises(IndexError, array.__getitem__, 0)
        raises(IndexError, array.__setitem__, 1, None)
        raises(IndexError, array.__getitem__, 1)
        raises(IndexError, array.__setitem__, -1, None)
        raises(IndexError, array.__getitem__, -1)

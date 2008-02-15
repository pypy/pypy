
from ctypes import *

class TestKeepalive:
    """ Tests whether various objects land in _objects
    or not
    """
    def test_array_of_pointers(self):
        A = POINTER(c_int) * 24
        a = A()
        l = c_long(2)
        p = pointer(l)
        a[3] = p
        assert l._objects is None
        assert p._objects == {'1':l}
        assert a._objects == {'3':{'1':l}}

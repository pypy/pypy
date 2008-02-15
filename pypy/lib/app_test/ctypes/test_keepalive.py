
from ctypes import *

class TestKeepalive:
    """ Tests whether various objects land in _objects
    or not
    """
    def test_array_of_pointers(self):
        # tests array item assignements & pointer.contents = ...
        A = POINTER(c_int) * 24
        a = A()
        l = c_long(2)
        p = pointer(l)
        a[3] = p
        assert l._objects is None
        assert p._objects == {'1':l}
        assert a._objects == {'3':{'1':l}}

    def test_structure_with_pointers(self):
        class X(Structure):
            _fields_ = [('x', POINTER(c_int))]

        x = X()
        u = c_int(3)
        p = pointer(u)
        x.x = p
        assert x.x._objects is None
        assert p._objects == {'1': u}
        assert x._objects == {'0': p._objects}

    def test_pointer_setitem(self):
        x = c_int(2)
        y = c_int(3)
        p = pointer(x)
        assert p._objects == {'1':x}
        p[0] = y
        assert p._objects.keys() == ['1']
        assert p._objects['1'].value == 3

    def test_char_p(self):
        assert c_char_p("abc")._objects == "abc"
        assert c_int(3)._objects is None
    

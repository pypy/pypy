
from ctypes import *

class TestUnion:
    def test_getattr(self):
        class Stuff(Union):
            _fields_ = [('x', c_char), ('y', c_int)]

        stuff = Stuff()
        stuff.y = ord('x')
        assert stuff.x == 'x'


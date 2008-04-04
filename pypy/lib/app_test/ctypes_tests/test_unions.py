
from ctypes import *
from support import BaseCTypesTestChecker

class TestUnion(BaseCTypesTestChecker):
    def test_getattr(self):
        class Stuff(Union):
            _fields_ = [('x', c_char), ('y', c_int)]

        stuff = Stuff()
        stuff.y = ord('x')
        assert stuff.x == 'x'

    def test_union_of_structures(self):
        class Stuff(Structure):
            _fields_ = [('x', c_int)]

        class Stuff2(Structure):
            _fields_ = [('x', c_int)]

        class UnionofStuff(Union):
            _fields_ = [('one', Stuff),
                        ('two', Stuff2)]

        u = UnionofStuff()
        u.one.x = 3
        assert u.two.x == 3
        

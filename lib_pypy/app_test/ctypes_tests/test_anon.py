from ctypes import *
from support import BaseCTypesTestChecker

class TestAnon(BaseCTypesTestChecker):

    def test_anon(self):
        class ANON(Union):
            _fields_ = [("a", c_int),
                        ("b", c_int)]

        class Y(Structure):
            _fields_ = [("x", c_int),
                        ("_", ANON),
                        ("y", c_int)]
            _anonymous_ = ["_"]

        assert Y.a.offset == sizeof(c_int)
        assert Y.b.offset == sizeof(c_int)

        assert ANON.a.offset == 0
        assert ANON.b.offset == 0

    def test_anon_nonseq(self):
        # TypeError: _anonymous_ must be a sequence
        raises(TypeError,
                              lambda: type(Structure)("Name",
                                                      (Structure,),
                                                      {"_fields_": [], "_anonymous_": 42}))

    def test_anon_nonmember(self):
        # AttributeError: type object 'Name' has no attribute 'x'
        raises(AttributeError,
                              lambda: type(Structure)("Name",
                                                      (Structure,),
                                                      {"_fields_": [],
                                                       "_anonymous_": ["x"]}))

    def test_nested(self):
        class ANON_S(Structure):
            _fields_ = [("a", c_int)]

        class ANON_U(Union):
            _fields_ = [("_", ANON_S),
                        ("b", c_int)]
            _anonymous_ = ["_"]

        class Y(Structure):
            _fields_ = [("x", c_int),
                        ("_", ANON_U),
                        ("y", c_int)]
            _anonymous_ = ["_"]

        assert Y.x.offset == 0
        assert Y.a.offset == sizeof(c_int)
        assert Y.b.offset == sizeof(c_int)
        assert Y._.offset == sizeof(c_int)
        assert Y.y.offset == sizeof(c_int) * 2


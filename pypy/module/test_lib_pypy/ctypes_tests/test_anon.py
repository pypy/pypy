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

        assert Y._names_ == ['x', 'a', 'b', 'y']

    def test_anonymous_fields_on_instance(self):
        # this is about the *instance-level* access of anonymous fields,
        # which you'd guess is the most common, but used not to work
        # (issue #2230)

        class B(Structure):
            _fields_ = [("x", c_int), ("y", c_int), ("z", c_int)]
        class A(Structure):
            _anonymous_ = ["b"]
            _fields_ = [("b", B)]

        a = A()
        a.x = 5
        assert a.x == 5
        assert a.b.x == 5
        a.b.x += 1
        assert a.x == 6

        class C(Structure):
            _anonymous_ = ["a"]
            _fields_ = [("v", c_int), ("a", A)]

        c = C()
        c.v = 3
        c.y = -8
        assert c.v == 3
        assert c.y == c.a.y == c.a.b.y == -8
        assert not hasattr(c, 'b')

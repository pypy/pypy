import py
from support import BaseCTypesTestChecker
from ctypes import *

class MyInt(c_int):
    def __cmp__(self, other):
        if type(other) != MyInt:
            return -1
        return cmp(self.value, other.value)

class Test(BaseCTypesTestChecker):

    def test_compare(self):
        assert MyInt(3) == MyInt(3)
        assert not MyInt(42) == MyInt(43)

    def test_ignore_retval(self):
        # Test if the return value of a callback is ignored
        # if restype is None
        proto = CFUNCTYPE(None)
        def func():
            return (1, "abc", None)

        cb = proto(func)
        assert None == cb()


    def test_int_callback(self):
        py.test.skip("subclassing semantics and implementation details not implemented")
        args = []
        def func(arg):
            args.append(arg)
            return arg

        cb = CFUNCTYPE(None, MyInt)(func)

        assert None == cb(42)
        assert type(args[-1]) == MyInt

        cb = CFUNCTYPE(c_int, c_int)(func)

        assert 42 == cb(42)
        assert type(args[-1]) == int

    def test_int_struct(self):
        py.test.skip("subclassing semantics and implementation details not implemented")
        class X(Structure):
            _fields_ = [("x", MyInt)]

        assert X().x == MyInt()

        s = X()
        s.x = MyInt(42)

        assert s.x == MyInt(42)

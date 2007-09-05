import sys
from pypy.rlib.rarithmetic import r_uint, r_ulonglong, r_longlong, intmask

def to_int(x):
    return int(x)

def to_uint(x):
    return r_uint(x)

def to_float(x):
    return float(x)

def to_longlong(x):
    return r_longlong(x)

def uint_to_int(x):
    return intmask(x)

class BaseTestCast:

    def check(self, fn, args):
        res1 = self.interpret(fn, args)
        res2 = fn(*args)
        assert res1 == res2

    def test_bool_to_int(self):
        self.check(to_int, [True])
        self.check(to_int, [False])

    def test_bool_to_uint(self):
        self.check(to_uint, [True])
        self.check(to_uint, [False])

    def test_bool_to_float(self):
        self.check(to_float, [True])
        self.check(to_float, [False])

    def test_int_to_uint(self):
        self.check(to_uint, [42])

    def test_int_to_float(self):
        self.check(to_float, [42])

    def test_int_to_longlong(self):
        self.check(to_longlong, [42])

    def test_uint_to_int(self):
        self.check(uint_to_int, [r_uint(sys.maxint+1)])

    def test_float_to_int(self):
        self.check(to_int, [42.5])

    def test_uint_to_float(self):
        self.check(to_float, [r_uint(sys.maxint+1)])

    def test_cast_primitive(self):
        from pypy.rpython.lltypesystem.lltype import cast_primitive, \
             UnsignedLongLong, SignedLongLong, Signed
        def f(x):
            x = cast_primitive(UnsignedLongLong, x)
            x <<= 60
            x /= 3
            x <<= 1
            x = cast_primitive(SignedLongLong, x)
            x >>= 32
            return cast_primitive(Signed, x)
        res = self.interpret(f, [14])
        assert res == -1789569707

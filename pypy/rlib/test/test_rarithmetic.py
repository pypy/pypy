from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.rlib.rarithmetic import *
import sys
import py

maxint_mask = (sys.maxint*2 + 1)
machbits = 0
i = 1
l = 1L
while i == l and type(i) is int:
    i *= 2
    l *= 2
    machbits += 1
#print machbits



class Test_r_int:

    def setup_method(self,method):
        space = self.space

    def test__add__(self):
        self.binary_test(lambda x, y: x + y)
    def test__sub__(self):
        self.binary_test(lambda x, y: x - y)
    def test__mul__(self):
        self.binary_test(lambda x, y: x * y)
        x = 3; y = [2]
        assert x*y == r_int(x)*y
        assert y*x == y*r_int(x)
    def test__div__(self):
        self.binary_test(lambda x, y: x // y)
    def test__mod__(self):
        self.binary_test(lambda x, y: x % y)
    def test__divmod__(self):
        self.binary_test(divmod)
    def test__lshift__(self):
        self.binary_test(lambda x, y: x << y, (1, 2, 3))
    def test__rshift__(self):
        self.binary_test(lambda x, y: x >> y, (1, 2, 3))
    def test__or__(self):
        self.binary_test(lambda x, y: x | y)
    def test__and__(self):
        self.binary_test(lambda x, y: x & y)
    def test__xor__(self):
        self.binary_test(lambda x, y: x ^ y)
    def test__neg__(self):
        self.unary_test(lambda x: -x)
    def test__pos__(self):
        self.unary_test(lambda x: +x)
    def test__invert__(self):
        self.unary_test(lambda x: ~x)
    def test__pow__(self):
        self.binary_test(lambda x, y: x**y, (2, 3))
        self.binary_test(lambda x, y: pow(x, y, 42L), (2, 3, 5, 1000))

    def unary_test(self, f):
        for arg in (-10, -1, 0, 3, 12345):
            res = f(arg)
            cmp = f(r_int(arg))
            assert res == cmp
        
    def binary_test(self, f, rargs = None):
        if not rargs:
            rargs = (-10, -1, 3, 55)
        for larg in (-10, -1, 0, 3, 1234):
            for rarg in rargs:
                for types in ((int, r_int), (r_int, int), (r_int, r_int)):
                    res = f(larg, rarg)
                    left, right = types
                    cmp = f(left(larg), right(rarg))
                    assert res == cmp
                    
class Test_r_uint:

    def setup_method(self,method):
        space = self.space

    def test__add__(self):
        self.binary_test(lambda x, y: x + y)
    def test__sub__(self):
        self.binary_test(lambda x, y: x - y)
    def test__mul__(self):
        self.binary_test(lambda x, y: x * y)
        x = 3; y = [2]
        assert x*y == r_uint(x)*y
        assert y*x == y*r_uint(x)
    def test__div__(self):
        self.binary_test(lambda x, y: x // y)
    def test__mod__(self):
        self.binary_test(lambda x, y: x % y)
    def test__divmod__(self):
        self.binary_test(divmod)
    def test__lshift__(self):
        self.binary_test(lambda x, y: x << y, (1, 2, 3))
    def test__rshift__(self):
        self.binary_test(lambda x, y: x >> y, (1, 2, 3))
    def test__or__(self):
        self.binary_test(lambda x, y: x | y)
    def test__and__(self):
        self.binary_test(lambda x, y: x & y)
    def test__xor__(self):
        self.binary_test(lambda x, y: x ^ y)
    def test__neg__(self):
        self.unary_test(lambda x: -x)
    def test__pos__(self):
        self.unary_test(lambda x: +x)
    def test__invert__(self):
        self.unary_test(lambda x: ~x)
    def test__pow__(self):
        self.binary_test(lambda x, y: x**y, (2, 3))
        # pow is buggy, dowsn't allow our type
        #self.binary_test(lambda x, y: pow(x, y, 42), (2, 3, 5, 1000))

    def test_back_to_int(self):
        #assert int(r_uint(-1)) == -1
        # ^^^ that looks wrong IMHO: int(x) should not by itself return
        #     an integer that has a different value than x, especially
        #     if x is a subclass of long.
        assert int(r_uint(1)) == 1

    def unary_test(self, f):
        for arg in (0, 3, 12345):
            res = f(arg) & maxint_mask 
            cmp = f(r_uint(arg))
            assert res == cmp
        
    def binary_test(self, f, rargs = None):
        mask = maxint_mask 
        if not rargs:
            rargs = (1, 3, 55)
        for larg in (0, 1, 2, 3, 1234):
            for rarg in rargs:
                for types in ((int, r_uint), (r_uint, int), (r_uint, r_uint)):
                    res = f(larg, rarg)
                    left, right = types
                    cmp = f(left(larg), right(rarg))
                    if type(res) is tuple:
                        res = res[0] & mask, res[1] & mask
                    else:
                        res = res & mask
                    assert res == cmp

    def test_from_float(self):
        assert r_uint(2.3) == 2
        assert r_uint(sys.maxint * 1.234) == long(sys.maxint * 1.234)

    def test_to_float(self):
        assert float(r_uint(2)) == 2.0
        val = long(sys.maxint * 1.234)
        assert float(r_uint(val)) == float(val)

def test_mixed_types():
    types = [r_uint, r_ulonglong]
    for left in types:
        for right in types:
            x = left(3) + right(5)
            expected = max(types.index(left), types.index(right))
            assert types.index(type(x)) == expected

def test_limits():
    for cls in r_uint, r_ulonglong:
        mask = cls.MASK
        assert cls(mask) == mask
        assert cls(mask+1) == 0

    for cls in r_int, r_longlong:
        mask = cls.MASK>>1
        assert cls(mask) == mask
        assert cls(-mask-1) == -mask-1
        py.test.raises(OverflowError, "cls(mask) + 1")
        py.test.raises(OverflowError, "cls(-mask-1) - 1")

def test_intmask():
    assert intmask(1) == 1
    assert intmask(sys.maxint) == sys.maxint
    minint = -sys.maxint-1
    assert intmask(minint) == minint
    assert intmask(2*sys.maxint+1) == -1
    assert intmask(sys.maxint*2) == -2
    assert intmask(sys.maxint*2+2) == 0
    assert intmask(2*(sys.maxint*1+1)) == 0    
    assert intmask(1 << (machbits-1)) == 1 << (machbits-1)
    assert intmask(sys.maxint+1) == minint
    assert intmask(minint-1) == sys.maxint
    assert intmask(r_uint(-1)) == -1
    assert intmask(r_ulonglong(-1)) == -1

def test_intmask_small():
    from pypy.rpython.lltypesystem import rffi
    for tp in [rffi.r_signedchar, rffi.r_short, rffi.r_int,
               rffi.r_long, rffi.r_longlong]:
        x = intmask(tp(5))
        assert (type(x), x) == (int, 5)
        x = intmask(tp(-5))
        assert (type(x), x) == (int, -5)
    for tp in [rffi.r_uchar, rffi.r_ushort, rffi.r_uint,
               rffi.r_ulong, rffi.r_ulonglong]:
        x = intmask(tp(5))
        assert (type(x), x) == (int, 5)

def test_bug_creating_r_int():
    minint = -sys.maxint-1
    assert r_int(r_int(minint)) == minint

def test_ovfcheck():
    one = 1
    x = sys.maxint
    minusx = -sys.maxint
    n = -sys.maxint-1
    y = sys.maxint-1
    # sanity
    raises(AssertionError, ovfcheck, r_uint(0))

    # not overflowing
    try:
        ovfcheck(y+one)
    except OverflowError:
        assert False
    else:
        pass
    try:
        ovfcheck(minusx-one)
    except OverflowError:
        assert False
    else:
        pass
    try:
        ovfcheck(x-x)
    except OverflowError:
        assert False
    else:
        pass        
    try:
        ovfcheck(n-n)
    except OverflowError:
        assert False
    else:
        pass    

    # overflowing
    try:
        ovfcheck(x+one)
    except OverflowError:
        pass
    else:
        assert False        
    try:
        ovfcheck(x+x)
    except OverflowError:
        pass
    else:
        assert False
    try:
        ovfcheck(n-one)
    except OverflowError:
        pass
    else:
        assert False
    try:
        ovfcheck(n-y)
    except OverflowError:
        pass
    else:
        assert False    

def test_ovfcheck_float_to_int():
    assert ovfcheck_float_to_int(1.0) == 1
    assert ovfcheck_float_to_int(0.0) == 0
    assert ovfcheck_float_to_int(13.0) == 13
    assert ovfcheck_float_to_int(-1.0) == -1
    assert ovfcheck_float_to_int(-13.0) == -13

    # strange things happening for float to int on 64 bit:
    # int(float(i)) != i  because of rounding issues
    x = sys.maxint
    while int(float(x)) > sys.maxint:
        x -= 1
    assert ovfcheck_float_to_int(float(x)) == int(float(x))

    x = sys.maxint + 1
    while int(float(x)) <= sys.maxint:
        x += 1
    py.test.raises(OverflowError, ovfcheck_float_to_int, x)

    x = -sys.maxint-1
    while int(float(x)) < -sys.maxint-1:
        x += 1
    assert ovfcheck_float_to_int(float(x)) == int(float(x))

    x = -sys.maxint-1
    while int(float(x)) >= -sys.maxint-1:
        x -= 1
    py.test.raises(OverflowError, ovfcheck_float_to_int, x)


def test_abs():
    assert type(abs(r_longlong(1))) is r_longlong


def test_r_singlefloat():
    x = r_singlefloat(2.5)       # exact number
    assert float(x) == 2.5
    x = r_singlefloat(2.1)       # approximate number, bits are lost
    assert float(x) != 2.1
    assert abs(float(x) - 2.1) < 1E-6

def test_r_singlefloat_eq():
    x = r_singlefloat(2.5)       # exact number
    y = r_singlefloat(2.5)
    assert x == y
    assert not x != y
    assert not x == 2.5
    assert x != 2.5
    py.test.raises(TypeError, "x>y")

class BaseTestRarithmetic(BaseRtypingTest):
    def test_compare_singlefloat_crashes(self):
        from pypy.rlib.rarithmetic import r_singlefloat
        from pypy.rpython.error import MissingRTypeOperation
        def f(x):
            a = r_singlefloat(x)
            b = r_singlefloat(x+1)
            return a == b
        py.test.raises(MissingRTypeOperation, "self.interpret(f, [42.0])")

class TestLLtype(BaseTestRarithmetic, LLRtypeMixin):
    pass

class TestOOtype(BaseTestRarithmetic, OORtypeMixin):
    pass

def test_int_real_union():
    from pypy.rpython.lltypesystem.rffi import r_int_real
    assert compute_restype(r_int_real, r_int_real) is r_int_real

def test_most_neg_value_of():
    assert most_neg_value_of_same_type(123) == -sys.maxint-1
    assert most_neg_value_of_same_type(r_uint(123)) == 0
    llmin = -(2**(r_longlong.BITS-1))
    assert most_neg_value_of_same_type(r_longlong(123)) == llmin
    assert most_neg_value_of_same_type(r_ulonglong(123)) == 0

def test_r_ulonglong():
    x = r_longlong(-1)
    y = r_ulonglong(x)
    assert long(y) == 2**r_ulonglong.BITS - 1

def test_highest_bit():
    py.test.raises(AssertionError, highest_bit, 0)
    py.test.raises(AssertionError, highest_bit, 14)
    for i in xrange(31):
        assert highest_bit(2**i) == i

def test_int_between():
    assert int_between(1, 1, 3)
    assert int_between(1, 2, 3)
    assert not int_between(1, 0, 2)
    assert not int_between(1, 5, 2)
    assert not int_between(1, 2, 2)
    assert not int_between(1, 1, 1)


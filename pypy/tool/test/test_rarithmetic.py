import unittest
import autopath
from pypy.tool.rarithmetic import *
import sys


maxint_mask = (sys.maxint*2 + 1)
machbits = 0
i = 1
l = 1L
while i == l and type(i) is int:
    i *= 2
    l *= 2
    machbits += 1
#print machbits


objspacename = 'std'

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
        self.binary_test(lambda x, y: pow(x, y, 42), (2, 3, 5, 1000))

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
        assert int(r_uint(-1)) == -1
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

import sys, py

#from pypy.objspace.std.model import WITHSMALLINT
#if not WITHSMALLINT:
#    py.test.skip("WITHSMALLINT is not enabled")

from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.objspace import FailedToImplement
from pypy.rlib.rarithmetic import r_uint

from pypy.conftest import gettestobjspace

class TestW_IntObject:

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withsmallint": True})

    def test_int_w(self):
        assert self.space.int_w(self.space.wrap(42)) == 42

    def test_uint_w(self):
        space = self.space
        assert space.uint_w(space.wrap(42)) == 42
        assert isinstance(space.uint_w(space.wrap(42)), r_uint)
        space.raises_w(space.w_ValueError, space.uint_w, space.wrap(-1))
        
    def test_repr(self):
        x = 1
        f1 = wrapint(self.space, x)
        result = self.space.repr(f1)
        assert self.space.unwrap(result) == repr(x)

    def test_str(self):
        x = 12345
        f1 = wrapint(self.space, x)
        result = self.space.str(f1)
        assert self.space.unwrap(result) == str(x)

    def test_hash(self):
        x = 42
        f1 = wrapint(self.space, x)
        result = self.space.hash(f1)
        assert result.intval == hash(x)

    def test_compare(self):
        import operator
        optab = ['lt', 'le', 'eq', 'ne', 'gt', 'ge']
        for x in (-10, -1, 0, 1, 2, 1000, sys.maxint):
            for y in (-sys.maxint-1, -11, -9, -2, 0, 1, 3, 1111, sys.maxint):
                for op in optab:
                    wx = wrapint(self.space, x)
                    wy = wrapint(self.space, y)
                    res = getattr(operator, op)(x, y)
                    method = getattr(self.space, op)
                    myres = method(wx, wy)
                    assert self.space.unwrap(myres) == res
                    
    def test_add(self):
        for x in [1, 100, sys.maxint // 2 - 50,
                  sys.maxint // 2, sys.maxint - 1000, sys.maxint]:
            for y in [1, 100, sys.maxint // 2 - 50,
                      sys.maxint // 2, sys.maxint - 1000, sys.maxint]:
                f1 = wrapint(self.space, x)
                f2 = wrapint(self.space, y)
                result = self.space.unwrap(self.space.add(f1, f2))
                assert result == x+y and type(result) == type(x+y)

    def test_sub(self):
        for x in [1, 100, sys.maxint // 2 - 50,
                  sys.maxint // 2, sys.maxint - 1000, sys.maxint]:
            for y in [1, 100, sys.maxint // 2 - 50,
                      sys.maxint // 2, sys.maxint - 1000, sys.maxint]:
                f1 = wrapint(self.space, x)
                f2 = wrapint(self.space, y)
                result = self.space.unwrap(self.space.sub(f1, f2))
                assert result == x-y and type(result) == type(x-y)

    def test_mul(self):
        for x in [0, 1, 100, sys.maxint // 2 - 50, sys.maxint - 1000]:
            for y in [0, 1, 100, sys.maxint // 2 - 50, sys.maxint - 1000]:
                f1 = wrapint(self.space, x)
                f2 = wrapint(self.space, y)
                result = self.space.unwrap(self.space.mul(f1, f2))
                assert result == x*y and type(result) == type(x*y)

    def test_div(self):
        for i in range(10):
            res = i//3
            f1 = wrapint(self.space, i)
            f2 = wrapint(self.space, 3)
            result = self.space.div(f1, f2)
            assert result.intval == res

    def test_mod(self):
        x = 1
        y = 2
        f1 = wrapint(self.space, x)
        f2 = wrapint(self.space, y)
        v = self.space.mod(f1, f2)
        assert v.intval == x % y
        # not that mod cannot overflow

    def test_divmod(self):
        x = 1
        y = 2
        f1 = wrapint(self.space, x)
        f2 = wrapint(self.space, y)
        ret = self.space.divmod(f1, f2)
        v, w = self.space.unwrap(ret)
        assert (v, w) == divmod(x, y)

    def test_pow_iii(self):
        x = 10
        y = 2
        z = 13
        f1 = wrapint(self.space, x)
        f2 = wrapint(self.space, y)
        f3 = wrapint(self.space, z)
        v = self.space.pow(f1, f2, f3)
        assert v.intval == pow(x, y, z)
        f1, f2, f3 = [wrapint(self.space, i) for i in (10, -1, 42)]
        self.space.raises_w(self.space.w_TypeError,
                            self.space.pow,
                            f1, f2, f3)
        f1, f2, f3 = [wrapint(self.space, i) for i in (10, 5, 0)]
        self.space.raises_w(self.space.w_ValueError,
                            self.space.pow,
                            f1, f2, f3)

    def test_pow_iin(self):
        x = 10
        y = 2
        f1 = wrapint(self.space, x)
        f2 = wrapint(self.space, y)
        v = self.space.pow(f1, f2, self.space.w_None)
        assert v.intval == x ** y

    def test_neg(self):
        x = 42
        f1 = wrapint(self.space, x)
        v = self.space.neg(f1)
        assert v.intval == -x

    def test_pos(self):
        x = 42
        f1 = wrapint(self.space, x)
        v = self.space.pos(f1)
        assert v.intval == +x
        x = -42
        f1 = wrapint(self.space, x)
        v = self.space.pos(f1)
        assert v.intval == +x

    def test_abs(self):
        x = 42
        f1 = wrapint(self.space, x)
        v = self.space.abs(f1)
        assert v.intval == abs(x)
        x = -42
        f1 = wrapint(self.space, x)
        v = self.space.abs(f1)
        assert v.intval == abs(x)

    def test_invert(self):
        x = 42
        f1 = wrapint(self.space, x)
        v = self.space.invert(f1)
        assert v.intval == ~x

    def test_lshift(self):
        x = 12345678
        y = 2
        f1 = wrapint(self.space, x)
        f2 = wrapint(self.space, y)
        v = self.space.lshift(f1, f2)
        assert v.intval == x << y

    def test_rshift(self):
        x = 12345678
        y = 2
        f1 = wrapint(self.space, x)
        f2 = wrapint(self.space, y)
        v = self.space.rshift(f1, f2)
        assert v.intval == x >> y

    def test_and(self):
        x = 12345678
        y = 2
        f1 = wrapint(self.space, x)
        f2 = wrapint(self.space, y)
        v = self.space.and_(f1, f2)
        assert v.intval == x & y

    def test_xor(self):
        x = 12345678
        y = 2
        f1 = wrapint(self.space, x)
        f2 = wrapint(self.space, y)
        v = self.space.xor(f1, f2)
        assert v.intval == x ^ y

    def test_or(self):
        x = 12345678
        y = 2
        f1 = wrapint(self.space, x)
        f2 = wrapint(self.space, y)
        v = self.space.or_(f1, f2)
        assert v.intval == x | y

    def test_int(self):
        f1 = wrapint(self.space, 1)
        result = self.space.int(f1)
        assert result == f1

    def test_oct(self):
        x = 012345
        f1 = wrapint(self.space, x)
        result = self.space.oct(f1)
        assert self.space.unwrap(result) == oct(x)

    def test_hex(self):
        x = 0x12345
        f1 = wrapint(self.space, x)
        result = self.space.hex(f1)
        assert self.space.unwrap(result) == hex(x)

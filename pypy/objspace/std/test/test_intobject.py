import sys
import autopath
from pypy.objspace.std import intobject as iobj
from pypy.objspace.std.objspace import FailedToImplement
from pypy.tool import test

class TestW_IntObject(test.TestCase):

    def setUp(self):
        self.space = test.objspace('std')

    def tearDown(self):
        pass

    def _longshiftresult(self, x):
        """ calculate an overflowing shift """
        n = 1
        l = long(x)
        while 1:
            ires = x << n
            lres = l << n
            if type(ires) is long or lres != ires:
                return n
            n += 1

    def _unwrap_nonimpl(self, func, *args, **kwds):
        """ make sure that the expected exception occours, and unwrap it """
        try:
            res = func(*args, **kwds)
            raise Exception, "should have failed but returned '%s'!" %repr(res)
        except FailedToImplement, arg:
            return arg[0]

    def test_repr(self):
        x = 1
        f1 = iobj.W_IntObject(self.space, x)
        result = iobj.repr__Int(self.space, f1)
        self.assertEquals(self.space.unwrap(result), repr(x))

    def test_str(self):
        x = 12345
        f1 = iobj.W_IntObject(self.space, x)
        result = iobj.str__Int(self.space, f1)
        self.assertEquals(self.space.unwrap(result), str(x))

    def test_hash(self):
        x = 42
        f1 = iobj.W_IntObject(self.space, x)
        result = iobj.hash__Int(self.space, f1)
        self.assertEquals(result.intval, hash(x))

    def test_compare(self):
        import operator
        optab = ['lt', 'le', 'eq', 'ne', 'gt', 'ge']
        for x in (-10, -1, 0, 1, 2, 1000, sys.maxint):
            for y in (-sys.maxint-1, -11, -9, -2, 0, 1, 3, 1111, sys.maxint):
                for op in optab:
                    wx = iobj.W_IntObject(self.space, x)
                    wy = iobj.W_IntObject(self.space, y)
                    res = getattr(operator, op)(x, y)
                    method = getattr(iobj, '%s__Int_Int' % op)
                    myres = method(self.space, wx, wy)
                    self.assertEquals(self.space.unwrap(myres), res)
                    
    def test_add(self):
        x = 1
        y = 2
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        result = iobj.add__Int_Int(self.space, f1, f2)
        self.assertEquals(result.intval, x+y)
        x = sys.maxint
        y = 1
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        self.assertEquals(self.space.w_OverflowError,
                          self._unwrap_nonimpl(iobj.add__Int_Int, self.space, f1, f2))

    def test_sub(self):
        x = 1
        y = 2
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        result = iobj.sub__Int_Int(self.space, f1, f2)
        self.assertEquals(result.intval, x-y)
        x = sys.maxint
        y = -1
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        self.assertEquals(self.space.w_OverflowError,
                          self._unwrap_nonimpl(iobj.sub__Int_Int, self.space, f1, f2))

    def test_mul(self):
        x = 2
        y = 3
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        result = iobj.mul__Int_Int(self.space, f1, f2)
        self.assertEquals(result.intval, x*y)
        x = -sys.maxint-1
        y = -1
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        self.assertEquals(self.space.w_OverflowError,
                          self._unwrap_nonimpl(iobj.mul__Int_Int, self.space, f1, f2))

    def test_div(self):
        for i in range(10):
            res = i//3
            f1 = iobj.W_IntObject(self.space, i)
            f2 = iobj.W_IntObject(self.space, 3)
            result = iobj.div__Int_Int(self.space, f1, f2)
            self.assertEquals(result.intval, res)
        x = -sys.maxint-1
        y = -1
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        self.assertEquals(self.space.w_OverflowError,
                          self._unwrap_nonimpl(iobj.div__Int_Int, self.space, f1, f2))

    def test_mod(self):
        x = 1
        y = 2
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        v = iobj.mod__Int_Int(self.space, f1, f2)
        self.assertEquals(v.intval, x % y)
        # not that mod cannot overflow

    def test_divmod(self):
        x = 1
        y = 2
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        ret = iobj.divmod__Int_Int(self.space, f1, f2)
        v, w = self.space.unwrap(ret)
        self.assertEquals((v, w), divmod(x, y))
        x = -sys.maxint-1
        y = -1
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        self.assertEquals(self.space.w_OverflowError,
                          self._unwrap_nonimpl(iobj.divmod__Int_Int, self.space, f1, f2))

    def test_pow_iii(self):
        x = 10
        y = 2
        z = 13
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        f3 = iobj.W_IntObject(self.space, z)
        v = iobj.pow__Int_Int_ANY(self.space, f1, f2, f3)
        self.assertEquals(v.intval, pow(x, y, z))
        f1, f2, f3 = [iobj.W_IntObject(self.space, i) for i in (10, -1, 42)]
        self.assertRaises_w(self.space.w_TypeError,
                            iobj.pow__Int_Int_ANY,
                            self.space, f1, f2, f3)
        f1, f2, f3 = [iobj.W_IntObject(self.space, i) for i in (10, 5, 0)]
        self.assertRaises_w(self.space.w_ValueError,
                            iobj.pow__Int_Int_ANY,
                            self.space, f1, f2, f3)

    def test_pow_iin(self):
        x = 10
        y = 2
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        v = iobj.pow__Int_Int_ANY(self.space, f1, f2, self.space.w_None)
        self.assertEquals(v.intval, x ** y)
        f1, f2 = [iobj.W_IntObject(self.space, i) for i in (10, 20)]
        self.assertEquals(self.space.w_OverflowError,
                          self._unwrap_nonimpl(iobj.pow__Int_Int_ANY, self.space, f1, f2, self.space.w_None))
        f1, f2 = [iobj.W_IntObject(self.space, i) for i in (10, -1)]
        self.assertEquals(self.space.w_ValueError,
                          self._unwrap_nonimpl(iobj.pow__Int_Int_ANY, self.space, f1, f2, self.space.w_None))

    def test_neg(self):
        x = 42
        f1 = iobj.W_IntObject(self.space, x)
        v = iobj.neg__Int(self.space, f1)
        self.assertEquals(v.intval, -x)
        x = -sys.maxint-1
        f1 = iobj.W_IntObject(self.space, x)
        self.assertEquals(self.space.w_OverflowError,
                          self._unwrap_nonimpl(iobj.neg__Int, self.space, f1))

    def test_pos(self):
        x = 42
        f1 = iobj.W_IntObject(self.space, x)
        v = iobj.pos__Int(self.space, f1)
        self.assertEquals(v.intval, +x)
        x = -42
        f1 = iobj.W_IntObject(self.space, x)
        v = iobj.pos__Int(self.space, f1)
        self.assertEquals(v.intval, +x)

    def test_abs(self):
        x = 42
        f1 = iobj.W_IntObject(self.space, x)
        v = iobj.abs__Int(self.space, f1)
        self.assertEquals(v.intval, abs(x))
        x = -42
        f1 = iobj.W_IntObject(self.space, x)
        v = iobj.abs__Int(self.space, f1)
        self.assertEquals(v.intval, abs(x))
        x = -sys.maxint-1
        f1 = iobj.W_IntObject(self.space, x)
        self.assertEquals(self.space.w_OverflowError,
                          self._unwrap_nonimpl(iobj.abs__Int, self.space, f1))

    def test_invert(self):
        x = 42
        f1 = iobj.W_IntObject(self.space, x)
        v = iobj.invert__Int(self.space, f1)
        self.assertEquals(v.intval, ~x)

    def test_lshift(self):
        x = 12345678
        y = 2
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        v = iobj.lshift__Int_Int(self.space, f1, f2)
        self.assertEquals(v.intval, x << y)
        y = self._longshiftresult(x)
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        self.assertEquals(self.space.w_OverflowError,
                          self._unwrap_nonimpl(iobj.lshift__Int_Int, self.space, f1, f2))

    def test_rshift(self):
        x = 12345678
        y = 2
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        v = iobj.rshift__Int_Int(self.space, f1, f2)
        self.assertEquals(v.intval, x >> y)

    def test_and(self):
        x = 12345678
        y = 2
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        v = iobj.and__Int_Int(self.space, f1, f2)
        self.assertEquals(v.intval, x & y)

    def test_xor(self):
        x = 12345678
        y = 2
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        v = iobj.xor__Int_Int(self.space, f1, f2)
        self.assertEquals(v.intval, x ^ y)

    def test_or(self):
        x = 12345678
        y = 2
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        v = iobj.or__Int_Int(self.space, f1, f2)
        self.assertEquals(v.intval, x | y)

    def test_int(self):
        f1 = iobj.W_IntObject(self.space, 1)
        result = iobj.int__Int(self.space, f1)
        self.assertEquals(result, f1)

##    def test_long(self):
##        x = 1
##        f1 = iobj.W_IntObject(self.space, x)
##        result = iobj.int_long(self.space, f1)
##        self.assertEquals(self.space.unwrap(result), long(x))

##    def test_float(self):
##        x = 1
##        f1 = iobj.W_IntObject(self.space, x)
##        result = iobj.int_float(self.space, f1)
##        self.assertEquals(self.space.unwrap(result), float(x))

    def test_oct(self):
        x = 012345
        f1 = iobj.W_IntObject(self.space, x)
        result = iobj.oct__Int(self.space, f1)
        self.assertEquals(self.space.unwrap(result), oct(x))

    def test_hex(self):
        x = 0x12345
        f1 = iobj.W_IntObject(self.space, x)
        result = iobj.hex__Int(self.space, f1)
        self.assertEquals(self.space.unwrap(result), hex(x))

class AppIntTest(test.AppTestCase):
    def setUp(self):
        self.space = test.objspace('std')

    def test_int_callable(self):
        self.assertEquals(42, int(42))

    def test_int_string(self):
        self.assertEquals(42, int("42"))

    def test_int_float(self):
        self.assertEquals(4, int(4.2))

    def test_int_str_repr(self):
        self.assertEquals("42", str(42))
        self.assertEquals("42", repr(42))
        

if __name__ == '__main__':
    test.main()

import sys
import autopath
from pypy.objspace.std import intobject as iobj
from pypy.objspace.std.objspace import FailedToImplement
from pypy.tool.rarithmetic import r_uint

objspacename = 'std'

class TestW_IntObject:

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
            return arg.w_type

    def test_int_w(self):
        assert self.space.int_w(self.space.wrap(42)) == 42

    def test_uint_w(self):
        space = self.space
        assert space.uint_w(space.wrap(42)) == 42
        assert isinstance(space.uint_w(space.wrap(42)), r_uint)
        space.raises_w(space.w_ValueError, space.uint_w, space.wrap(-1))
        
    def test_repr(self):
        x = 1
        f1 = iobj.W_IntObject(self.space, x)
        result = iobj.repr__Int(self.space, f1)
        assert self.space.unwrap(result) == repr(x)

    def test_str(self):
        x = 12345
        f1 = iobj.W_IntObject(self.space, x)
        result = iobj.str__Int(self.space, f1)
        assert self.space.unwrap(result) == str(x)

    def test_hash(self):
        x = 42
        f1 = iobj.W_IntObject(self.space, x)
        result = iobj.hash__Int(self.space, f1)
        assert result.intval == hash(x)

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
                    assert self.space.unwrap(myres) == res
                    
    def test_add(self):
        x = 1
        y = 2
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        result = iobj.add__Int_Int(self.space, f1, f2)
        assert result.intval == x+y
        x = sys.maxint
        y = 1
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        assert self.space.w_OverflowError == (
                          self._unwrap_nonimpl(iobj.add__Int_Int, self.space, f1, f2))

    def test_sub(self):
        x = 1
        y = 2
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        result = iobj.sub__Int_Int(self.space, f1, f2)
        assert result.intval == x-y
        x = sys.maxint
        y = -1
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        assert self.space.w_OverflowError == (
                          self._unwrap_nonimpl(iobj.sub__Int_Int, self.space, f1, f2))

    def test_mul(self):
        x = 2
        y = 3
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        result = iobj.mul__Int_Int(self.space, f1, f2)
        assert result.intval == x*y
        x = -sys.maxint-1
        y = -1
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        assert self.space.w_OverflowError == (
                          self._unwrap_nonimpl(iobj.mul__Int_Int, self.space, f1, f2))

    def test_div(self):
        for i in range(10):
            res = i//3
            f1 = iobj.W_IntObject(self.space, i)
            f2 = iobj.W_IntObject(self.space, 3)
            result = iobj.div__Int_Int(self.space, f1, f2)
            assert result.intval == res
        x = -sys.maxint-1
        y = -1
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        assert self.space.w_OverflowError == (
                          self._unwrap_nonimpl(iobj.div__Int_Int, self.space, f1, f2))

    def test_mod(self):
        x = 1
        y = 2
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        v = iobj.mod__Int_Int(self.space, f1, f2)
        assert v.intval == x % y
        # not that mod cannot overflow

    def test_divmod(self):
        x = 1
        y = 2
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        ret = iobj.divmod__Int_Int(self.space, f1, f2)
        v, w = self.space.unwrap(ret)
        assert (v, w) == divmod(x, y)
        x = -sys.maxint-1
        y = -1
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        assert self.space.w_OverflowError == (
                          self._unwrap_nonimpl(iobj.divmod__Int_Int, self.space, f1, f2))

    def test_pow_iii(self):
        x = 10
        y = 2
        z = 13
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        f3 = iobj.W_IntObject(self.space, z)
        v = iobj.pow__Int_Int_Int(self.space, f1, f2, f3)
        assert v.intval == pow(x, y, z)
        f1, f2, f3 = [iobj.W_IntObject(self.space, i) for i in (10, -1, 42)]
        self.space.raises_w(self.space.w_TypeError,
                            iobj.pow__Int_Int_Int,
                            self.space, f1, f2, f3)
        f1, f2, f3 = [iobj.W_IntObject(self.space, i) for i in (10, 5, 0)]
        self.space.raises_w(self.space.w_ValueError,
                            iobj.pow__Int_Int_Int,
                            self.space, f1, f2, f3)

    def test_pow_iin(self):
        x = 10
        y = 2
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        v = iobj.pow__Int_Int_None(self.space, f1, f2, self.space.w_None)
        assert v.intval == x ** y
        f1, f2 = [iobj.W_IntObject(self.space, i) for i in (10, 20)]
        assert self.space.w_OverflowError == (
                          self._unwrap_nonimpl(iobj.pow__Int_Int_None, self.space, f1, f2, self.space.w_None))

    def test_neg(self):
        x = 42
        f1 = iobj.W_IntObject(self.space, x)
        v = iobj.neg__Int(self.space, f1)
        assert v.intval == -x
        x = -sys.maxint-1
        f1 = iobj.W_IntObject(self.space, x)
        assert self.space.w_OverflowError == (
                          self._unwrap_nonimpl(iobj.neg__Int, self.space, f1))

    def test_pos(self):
        x = 42
        f1 = iobj.W_IntObject(self.space, x)
        v = iobj.pos__Int(self.space, f1)
        assert v.intval == +x
        x = -42
        f1 = iobj.W_IntObject(self.space, x)
        v = iobj.pos__Int(self.space, f1)
        assert v.intval == +x

    def test_abs(self):
        x = 42
        f1 = iobj.W_IntObject(self.space, x)
        v = iobj.abs__Int(self.space, f1)
        assert v.intval == abs(x)
        x = -42
        f1 = iobj.W_IntObject(self.space, x)
        v = iobj.abs__Int(self.space, f1)
        assert v.intval == abs(x)
        x = -sys.maxint-1
        f1 = iobj.W_IntObject(self.space, x)
        assert self.space.w_OverflowError == (
                          self._unwrap_nonimpl(iobj.abs__Int, self.space, f1))

    def test_invert(self):
        x = 42
        f1 = iobj.W_IntObject(self.space, x)
        v = iobj.invert__Int(self.space, f1)
        assert v.intval == ~x

    def test_lshift(self):
        x = 12345678
        y = 2
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        v = iobj.lshift__Int_Int(self.space, f1, f2)
        assert v.intval == x << y
        y = self._longshiftresult(x)
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        assert self.space.w_OverflowError == (
                          self._unwrap_nonimpl(iobj.lshift__Int_Int, self.space, f1, f2))

    def test_rshift(self):
        x = 12345678
        y = 2
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        v = iobj.rshift__Int_Int(self.space, f1, f2)
        assert v.intval == x >> y

    def test_and(self):
        x = 12345678
        y = 2
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        v = iobj.and__Int_Int(self.space, f1, f2)
        assert v.intval == x & y

    def test_xor(self):
        x = 12345678
        y = 2
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        v = iobj.xor__Int_Int(self.space, f1, f2)
        assert v.intval == x ^ y

    def test_or(self):
        x = 12345678
        y = 2
        f1 = iobj.W_IntObject(self.space, x)
        f2 = iobj.W_IntObject(self.space, y)
        v = iobj.or__Int_Int(self.space, f1, f2)
        assert v.intval == x | y

    def test_int(self):
        f1 = iobj.W_IntObject(self.space, 1)
        result = iobj.int__Int(self.space, f1)
        assert result == f1

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
        assert self.space.unwrap(result) == oct(x)

    def test_hex(self):
        x = 0x12345
        f1 = iobj.W_IntObject(self.space, x)
        result = iobj.hex__Int(self.space, f1)
        assert self.space.unwrap(result) == hex(x)

class AppTestInt:

    def test_int_callable(self):
        assert 43 == int(43)

    def test_int_string(self):
        assert 42 == int("42")
        assert 10000000000 == long("10000000000")

    def test_int_unicode(self):
        assert 42 == int(unicode('42'))

    def test_int_float(self):
        assert 4 == int(4.2)

    def test_int_str_repr(self):
        assert "42" == str(42)
        assert "42" == repr(42)
        raises(ValueError, int, '0x2A')
        
    def test_int_two_param(self):
        assert 42 == int('0x2A', 0)
        assert 42 == int('2A', 16)
        assert 42 == int('42', 10)
        raises(TypeError, int, 1, 10)

    def test_shift_zeros(self):
        assert (1 << 0) == 1
        assert (1 >> 0) == 1

    def test_overflow(self):
        import sys
        n = sys.maxint + 1
        assert isinstance(n, long)

    def test_pow(self):
        assert pow(2, -10) == 1/1024.

    def test_int_w_long_arg(self):
        assert int(10000000000) == 10000000000L
        assert int("10000000000") == 10000000000L

    def test_int_subclass_ctr(self):
        class j(int):
            pass
        assert j(100) == 100
        assert isinstance(j(100),j)
        assert j(100L) == 100
        assert j("100") == 100
        assert j("100",2) == 4
        assert isinstance(j("100",2),j)
        raises(OverflowError,j,10000000000)
        raises(OverflowError,j,"10000000000")

    def test_special_int(self):
        class a:
            def __int__(self): 
                self.ar = True 
                return None
        inst = a()
        raises(TypeError, int, inst) 
        assert inst.ar == True 

        class b: 
            pass 
        raises((AttributeError,TypeError), int, b()) 

    def test_special_long(self):
        class a:
            def __long__(self): 
                self.ar = True 
                return None
        inst = a()
        raises(TypeError, long, inst) 
        assert inst.ar == True 

        class b: 
            pass 
        raises((AttributeError,TypeError), long, b()) 

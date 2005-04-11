"""
This file defines restricted arithmetic:

classes and operations to express integer arithmetic,
such that before and after translation semantics are
consistent

r_uint   an unsigned integer which has not overflow
         checking. It is always positive and always
         truncated to the internal machine word size.
intmask  mask a possibly long value when running on CPython
         back to a signed int value
ovfcheck check on CPython whether the result of a signed
         integer operation did overflow
ovfcheck_lshift
         << with oveflow checking
         catering to 2.3/2.4 differences about <<

These are meant to be erased by translation, r_uint
in the process should mark unsigned values, ovfcheck should
mark where overflow checking is required.


"""

class r_int(int):
    """ fake integer implementation in order to make sure that
    primitive integer operations do overflow """

    def __add__(self, other):
        x = int(self)
        y = int(other)
        return r_int(x + y)
    __radd__ = __add__
    
    def __sub__(self, other):
        x = int(self)
        y = int(other)
        return r_int(x - y)

    def __rsub__(self, other):
        y = int(self)
        x = int(other)
        return r_int(x - y)
    
    def __mul__(self, other):
        x = int(self)
        if not isinstance(other, (int, long)):
            return x * other
        y = int(other)
        return r_int(x * y)
    __rmul__ = __mul__

    def __div__(self, other):
        x = int(self)
        y = int(other)
        return r_int(x // y)

    __floordiv__ = __div__

    def __rdiv__(self, other):
        y = int(self)
        x = int(other)
        return r_int(x // y)

    __rfloordiv__ = __rdiv__

    def __mod__(self, other):
        x = int(self)
        y = int(other)
        return r_int(x % y)

    def __rmod__(self, other):
        y = int(self)
        x = int(other)
        return r_int(x % y)

    def __divmod__(self, other):
        x = int(self)
        y = int(other)
        res = divmod(x, y)
        return (r_int(res[0]), r_int(res[1]))

    def __lshift__(self, n):
        # ensure long shift, so we don't depend on
        # shift truncation (2.3) vs. long(2.4)
        x = long(self)
        y = int(n)
        return r_int(x << y)

    def __rlshift__(self, n):
        y = long(self)
        x = int(n)
        return r_int(x << y)

    def __rshift__(self, n):
        x = int(self)
        y = int(n)
        return r_int(x >> y)

    def __rrshift__(self, n):
        y = int(self)
        x = int(n)
        return r_int(x >> y)

    def __or__(self, other):
        x = int(self)
        y = int(other)
        return r_int(x | y)
    __ror__ = __or__

    def __and__(self, other):
        x = int(self)
        y = int(other)
        return r_int(x & y)
    __rand__ = __and__

    def __xor__(self, other):
        x = int(self)
        y = int(other)
        return r_int(x ^ y)
    __rxor__ = __xor__

    def __neg__(self):
        x = int(self)
        return r_int(-x)

    def __pos__(self):
        return r_int(self)

    def __invert__(self):
        x = int(self)
        return r_int(~x)

    def __pow__(self, other, m=None):
        x = int(self)
        y = int(other)
        res = pow(x, y, m)
        return r_int(res)

    def __rpow__(self, other, m=None):
        y = int(self)
        x = int(other)
        res = pow(x, y, m)
        return r_int(res)

# set up of machine internals
_bits = 0
_itest = 1
_Ltest = 1L
while _itest == _Ltest and type(_itest) is int:
    _itest *= 2
    _Ltest *= 2
    _bits += 1

LONG_BIT = _bits+1
LONG_MASK = _Ltest*2-1
LONG_TEST = _Ltest

def intmask(n):
    if isinstance(n, int):
        return n
    if isinstance(n, r_uint):
        n = long(n)
    n &= LONG_MASK
    if n >= LONG_TEST:
        n -= 2*LONG_TEST
    return int(n)

del _bits, _itest, _Ltest

def ovfcheck(r):
    # to be used as ovfcheck(x <op> y)
    # raise OverflowError if the operation did overflow
    assert not isinstance(r, r_uint), "unexpected ovf check on unsigned"
    if isinstance(r, long):
        raise OverflowError, "signed integer expression did overflow"
    return r

def ovfcheck_lshift(a, b):
    return ovfcheck(int(long(a) << b))

class r_uint(long):
    """ fake unsigned integer implementation """

    _mask = LONG_MASK

    def __new__(klass, val):
        return long.__new__(klass, val & klass._mask)

    def __int__(self):
        if self < LONG_TEST:
            return int(self)
        else:
            return intmask(self)

    def __add__(self, other):
        x = long(self)
        y = long(other)
        return r_uint(x + y)
    __radd__ = __add__
    
    def __sub__(self, other):
        x = long(self)
        y = long(other)
        return r_uint(x - y)

    def __rsub__(self, other):
        y = long(self)
        x = long(other)
        return r_uint(x - y)
    
    def __mul__(self, other):
        x = long(self)
        if not isinstance(other, (int, long)):
            return x * other
        y = long(other)
        return r_uint(x * y)
    __rmul__ = __mul__

    def __div__(self, other):
        x = long(self)
        y = long(other)
        return r_uint(x // y)

    __floordiv__ = __div__

    def __rdiv__(self, other):
        y = long(self)
        x = long(other)
        return r_uint(x // y)

    __rfloordiv__ = __rdiv__

    def __mod__(self, other):
        x = long(self)
        y = long(other)
        return r_uint(x % y)

    def __rmod__(self, other):
        y = long(self)
        x = long(other)
        return r_uint(x % y)

    def __divmod__(self, other):
        x = long(self)
        y = long(other)
        res = divmod(x, y)
        return (r_uint(res[0]), r_uint(res[1]))

    def __lshift__(self, n):
        x = long(self)
        y = long(n)
        return r_uint(x << y)

    def __rlshift__(self, n):
        y = long(self)
        x = long(n)
        return r_uint(x << y)

    def __rshift__(self, n):
        x = long(self)
        y = long(n)
        return r_uint(x >> y)

    def __rrshift__(self, n):
        y = long(self)
        x = long(n)
        return r_uint(x >> y)

    def __or__(self, other):
        x = long(self)
        y = long(other)
        return r_uint(x | y)
    __ror__ = __or__

    def __and__(self, other):
        x = long(self)
        y = long(other)
        return r_uint(x & y)
    __rand__ = __and__

    def __xor__(self, other):
        x = long(self)
        y = long(other)
        return r_uint(x ^ y)
    __rxor__ = __xor__

    def __neg__(self):
        x = long(self)
        return r_uint(-x)

    def __pos__(self):
        return r_uint(self)

    def __invert__(self):
        x = long(self)
        return r_uint(~x)

    def __pow__(self, other, m=None):
        x = long(self)
        y = long(other)
        res = pow(x, y, m)
        return r_uint(res)

    def __rpow__(self, other, m=None):
        y = long(self)
        x = long(other)
        res = pow(x, y, m)
        return r_uint(res)

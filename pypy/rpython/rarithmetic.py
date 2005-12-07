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
ovfcheck_float_to_int
         convert to an integer or raise OverflowError
r_ushort like r_uint but half word size
r_ulong  like r_uint but double word size

These are meant to be erased by translation, r_uint
in the process should mark unsigned values, ovfcheck should
mark where overflow checking is required.


"""
import math

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
        return int(n)   # possibly bool->int
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

def _local_ovfcheck(r):
    # a copy of the above, because we cannot call ovfcheck
    # in a context where no primitiveoperator is involved.
    assert not isinstance(r, r_uint), "unexpected ovf check on unsigned"
    if isinstance(r, long):
        raise OverflowError, "signed integer expression did overflow"
    return r

def ovfcheck_lshift(a, b):
    return _local_ovfcheck(int(long(a) << b))

FL_MAXINT = float(LONG_TEST-1)
FL_MININT = float(-LONG_TEST)

def ovfcheck_float_to_int(x):
    _, intp = math.modf(x)
    if FL_MININT < intp < FL_MAXINT:
        return int(intp)
    raise OverflowError


class base_int(long):
    """ fake unsigned integer implementation """


    def _widen(self, other, value):
        """
        if one argument is int or long, the other type wins.
        otherwise, produce the largest class to hold the result.
        """
        return self.typemap[ type(self), type(other) ](value)

    def __new__(klass, val):
        if klass is base_int:
            raise TypeError("abstract base!")
        else:
            return super(base_int, klass).__new__(klass, val)

    def __int__(self):
        if self < LONG_TEST:
            return long.__int__(self)
        else:
            return intmask(self)

    def __add__(self, other):
        x = long(self)
        y = long(other)
        return self._widen(other, x + y)
    __radd__ = __add__
    
    def __sub__(self, other):
        x = long(self)
        y = long(other)
        return self._widen(other, x - y)

    def __rsub__(self, other):
        y = long(self)
        x = long(other)
        return self._widen(other, x - y)
    
    def __mul__(self, other):
        x = long(self)
        if not isinstance(other, (int, long)):
            return x * other
        y = long(other)
        return self._widen(other, x * y)
    __rmul__ = __mul__

    def __div__(self, other):
        x = long(self)
        y = long(other)
        return self._widen(other, x // y)

    __floordiv__ = __div__

    def __rdiv__(self, other):
        y = long(self)
        x = long(other)
        return self._widen(other, x // y)

    __rfloordiv__ = __rdiv__

    def __mod__(self, other):
        x = long(self)
        y = long(other)
        return self._widen(other, x % y)

    def __rmod__(self, other):
        y = long(self)
        x = long(other)
        return self._widen(other, x % y)

    def __divmod__(self, other):
        x = long(self)
        y = long(other)
        res = divmod(x, y)
        return (self.__class__(res[0]), self.__class__(res[1]))

    def __lshift__(self, n):
        x = long(self)
        y = long(n)
        return self.__class__(x << y)

    def __rlshift__(self, n):
        y = long(self)
        x = long(n)
        return self._widen(n, x << y)

    def __rshift__(self, n):
        x = long(self)
        y = long(n)
        return self._widen(n, x >> y)

    def __rrshift__(self, n):
        y = long(self)
        x = long(n)
        return self._widen(n, x >> y)

    def __or__(self, other):
        x = long(self)
        y = long(other)
        return self._widen(other, x | y)
    __ror__ = __or__

    def __and__(self, other):
        x = long(self)
        y = long(other)
        return self._widen(other, x & y)
    __rand__ = __and__

    def __xor__(self, other):
        x = long(self)
        y = long(other)
        return self._widen(other, x ^ y)
    __rxor__ = __xor__

    def __neg__(self):
        x = long(self)
        return self.__class__(-x)

    def __pos__(self):
        return self.__class__(self)

    def __invert__(self):
        x = long(self)
        return self.__class__(~x)

    def __pow__(self, other, m=None):
        x = long(self)
        y = long(other)
        res = pow(x, y, m)
        return self._widen(other, res)

    def __rpow__(self, other, m=None):
        y = long(self)
        x = long(other)
        res = pow(x, y, m)
        return self._widen(other, res)

class signed_int(base_int):
    def __new__(klass, val):
        if val > klass.MASK>>1 or val < -(klass.MASK>>1)-1:
            raise OverflowError("%s does not fit in signed %d-bit integer"%(val, klass.BITS))
        if val < 0:
            val = - ((-val) & klass.MASK)
        return super(signed_int, klass).__new__(klass, val)
    typemap = {}

class unsigned_int(base_int):
    def __new__(klass, val):
        return super(unsigned_int, klass).__new__(klass, val & klass.MASK)
    typemap = {}

class r_int(signed_int):
    MASK = LONG_MASK
    BITS = LONG_BIT


class r_uint(unsigned_int):
    MASK = LONG_MASK
    BITS = LONG_BIT


if LONG_BIT == 64:
    r_ulonglong = r_uint
    r_longlong = r_int
else:
    assert LONG_BIT == 32
    
    class r_longlong(signed_int):
        BITS = LONG_BIT * 2
        MASK = 2**BITS-1

    class r_ulonglong(unsigned_int):
        BITS = LONG_BIT * 2
        MASK = 2**BITS-1

def setup_typemap(typemap, types):
    for left in types:
        for right in types:
            if left in (int, long):
                restype = right
            elif right in (int, long):
                restype = left
            else:
                if left.BITS > right.BITS:
                    restype = left
                else:
                    restype = right
            if restype not in (int, long):
                typemap[ left, right ] = restype

setup_typemap(unsigned_int.typemap, (int, long, r_uint, r_ulonglong))
setup_typemap(signed_int.typemap, (int, long, r_int, r_longlong))

del setup_typemap

# string -> float helper

def parts_to_float(sign, beforept, afterpt, exponent):
    if not exponent:
        exponent = '0'
    return float("%s%s.%se%s" % (sign, beforept, afterpt, exponent))

# float -> string

formatd_max_length = 120

def formatd(fmt, x):
    return fmt % (x,)

# a common string hash function

def _hash_string(s):
    length = len(s)
    if length == 0:
        x = -1
    else:
        x = ord(s[0]) << 7
        i = 0
        while i < length:
            x = (1000003*x) ^ ord(s[i])
            i += 1
        x ^= length
        if x == 0:
            x = -1
    return intmask(x)

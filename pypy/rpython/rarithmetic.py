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
r_ushort like r_uint but half word size
r_ulong  like r_uint but double word size

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

def _widen(self, other, value):
    """
    if one argument is int or long, the other type wins.
    otherwise, produce the largest class to hold the result.
    """
    return _typemap[ type(self), type(other) ](value)

class r_uint(long):
    """ fake unsigned integer implementation """

    MASK = LONG_MASK
    BITS = LONG_BIT

    def __new__(klass, val):
        return long.__new__(klass, val & klass.MASK)

    def __int__(self):
        if self < LONG_TEST:
            return long.__int__(self)
        else:
            return intmask(self)

    def __add__(self, other):
        x = long(self)
        y = long(other)
        return _widen(self, other, x + y)
    __radd__ = __add__
    
    def __sub__(self, other):
        x = long(self)
        y = long(other)
        return _widen(self, other, x - y)

    def __rsub__(self, other):
        y = long(self)
        x = long(other)
        return _widen(self, other, x - y)
    
    def __mul__(self, other):
        x = long(self)
        if not isinstance(other, (int, long)):
            return x * other
        y = long(other)
        return _widen(self, other, x * y)
    __rmul__ = __mul__

    def __div__(self, other):
        x = long(self)
        y = long(other)
        return _widen(self, other, x // y)

    __floordiv__ = __div__

    def __rdiv__(self, other):
        y = long(self)
        x = long(other)
        return _widen(self, other, x // y)

    __rfloordiv__ = __rdiv__

    def __mod__(self, other):
        x = long(self)
        y = long(other)
        return _widen(self, other, x % y)

    def __rmod__(self, other):
        y = long(self)
        x = long(other)
        return _widen(self, other, x % y)

    def __divmod__(self, other):
        x = long(self)
        y = long(other)
        res = divmod(x, y)
        return (r_uint(res[0]), r_uint(res[1]))

    def __lshift__(self, n):
        x = long(self)
        y = long(n)
        return self.__class__(x << y)

    def __rlshift__(self, n):
        y = long(self)
        x = long(n)
        return _widen(self, n, x << y)

    def __rshift__(self, n):
        x = long(self)
        y = long(n)
        return _widen(self, n, x >> y)

    def __rrshift__(self, n):
        y = long(self)
        x = long(n)
        return _widen(self, n, x >> y)

    def __or__(self, other):
        x = long(self)
        y = long(other)
        return _widen(self, other, x | y)
    __ror__ = __or__

    def __and__(self, other):
        x = long(self)
        y = long(other)
        return _widen(self, other, x & y)
    __rand__ = __and__

    def __xor__(self, other):
        x = long(self)
        y = long(other)
        return _widen(self, other, x ^ y)
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
        return _widen(self, other, res)

    def __rpow__(self, other, m=None):
        y = long(self)
        x = long(other)
        res = pow(x, y, m)
        return _widen(self, other, res)

class r_ushort(r_uint):
    BITS = r_uint.BITS // 2
    MASK = (1L << BITS) - 1

class r_ulong(r_uint):
    BITS = r_uint.BITS * 2
    MASK = (1L << BITS) - 1

def setup_typemap():
    types = int, long, r_uint, r_ushort, r_ulong
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
                _typemap[ left, right ] = restype
_typemap = {}

setup_typemap()
del setup_typemap

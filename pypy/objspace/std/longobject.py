import sys, operator
from pypy.objspace.std.objspace import *
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.floatobject import W_FloatObject
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.rpython.rarithmetic import intmask, r_uint, r_ushort, r_ulong
from pypy.rpython.rarithmetic import LONG_BIT

import math

# for now, we use r_uint as a digit.
# we may later switch to r_ushort, when it is supported by rtyper etc.

Digit = r_uint # already works: r_ushort
Twodigits = r_uint

# the following describe a plain digit
# XXX at the moment we can't save this bit,
# or we would need a large enough type to hold
# the carry bits in _x_divrem
SHIFT = (Twodigits.BITS // 2) - 1
MASK = int((1 << SHIFT) - 1)

# find the correct type for carry/borrow
if Digit.BITS - SHIFT >= 1:
    # we have one more bit in Digit
    Carryadd = Digit
    Stwodigits = int
else:
    # we need another Digit
    Carryadd = Twodigits
    raise ValueError, "need a large enough type for Stwodigits"
Carrymul = Twodigits

# Debugging digit array access.
#
# 0 == no check at all
# 1 == check correct type
# 2 == check for extra (ab)used bits
CHECK_DIGITS = 2

if CHECK_DIGITS:
    class DigitArray(list):
        if CHECK_DIGITS == 1:
            def __setitem__(self, idx, value):
                assert type(value) is Digit
                list.__setitem__(self, idx, value)
        elif CHECK_DIGITS == 2:
            def __setitem__(self, idx, value):
                assert type(value) is Digit
                assert value <= MASK
                list.__setitem__(self, idx, value)
        else:
            raise Exception, 'CHECK_DIGITS == %d not supported' % CHECK_DIGITS
else:
    DigitArray = list

# XXX some operations below return one of their input arguments
#     without checking that it's really of type long (and not a subclass).

class W_LongObject(W_Object):
    """This is a reimplementation of longs using a list of digits."""
    # All functions that still rely on the underlying Python's longs are marked
    # with YYYYYY
    from pypy.objspace.std.longtype import long_typedef as typedef
    
    def __init__(w_self, space, digits, sign=0):
        W_Object.__init__(w_self, space)
        if isinstance(digits, long):  #YYYYYY
            digits, sign = args_from_long(digits)
        w_self.digits = DigitArray(digits)
        w_self.sign = sign
        assert len(w_self.digits)

    def longval(self): #YYYYYY
        l = 0
        for d in self.digits[::-1]:
            l = l << SHIFT
            l += long(d)
        return l * self.sign

    def unwrap(w_self): #YYYYYY
        return w_self.longval()

    def _normalize(self):
        if len(self.digits) == 0:
            self.sign = 0
            self.digits = [Digit(0)]
            return
        i = len(self.digits) - 1
        while i != 0 and self.digits[i] == 0:
            self.digits.pop(-1)
            i -= 1
        if len(self.digits) == 1 and self.digits[0] == 0:
            self.sign = 0


registerimplementation(W_LongObject)

# bool-to-long
def delegate_Bool2Long(w_bool):
    return W_LongObject(w_bool.space, [Digit(w_bool.boolval)],
                        int(w_bool.boolval))

# int-to-long delegation
def delegate_Int2Long(w_intobj):
    return long__Int(w_intobj.space, w_intobj)

# long-to-float delegation
def delegate_Long2Float(w_longobj):
    try:
        return W_FloatObject(w_longobj.space, _AsDouble(w_longobj))
    except OverflowError:
        raise OperationError(w_longobj.space.w_OverflowError,
                             w_longobj.space.wrap("long int too large to convert to float"))


# long__Long is supposed to do nothing, unless it has
# a derived long object, where it should return
# an exact one.
def long__Long(space, w_long1):
    if space.is_w(space.type(w_long1), space.w_long):
        return w_long1
    digits = w_long1.digits
    sign = w_long1.sign
    return W_LongObject(space, digits, sign)

def long__Int(space, w_intobj):
    if w_intobj.intval < 0:
        sign = -1
        ival = -w_intobj.intval
    elif w_intobj.intval > 0:
        sign = 1
        ival = w_intobj.intval
    else:
        return W_LongObject(space, [Digit(0)], 0)
    # Count the number of Python digits.
    # We used to pick 5 ("big enough for anything"), but that's a
    # waste of time and space given that 5*15 = 75 bits are rarely
    # needed.
    t = r_uint(ival)
    ndigits = 0
    while t:
        ndigits += 1
        t >>= SHIFT
    v = W_LongObject(space, [Digit(0)] * ndigits, sign)
    t = r_uint(ival)
    p = 0
    while t:
        v.digits[p] = Digit(t & MASK)
        t >>= SHIFT
        p += 1
    return v

def int__Long(space, w_value):
    try:
        x = _AsLong(w_value)
    except OverflowError:
        return long__Long(space, w_value)
    else:
        return space.newint(x)

def float__Long(space, w_longobj):
    try:
        return space.newfloat(_AsDouble(w_longobj))
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("long int too large to convert to float"))

def long__Float(space, w_floatobj):
    return _FromDouble(space, w_floatobj.floatval)

def int_w__Long(space, w_value):
    try:
        return _AsLong(w_value)
    except OverflowError:
        raise OperationError(space.w_OverflowError, space.wrap(
            "long int too large to convert to int"))


def uint_w__Long(space, w_value):
    if w_value.sign == -1:
        raise OperationError(space.w_ValueError, space.wrap(
            "cannot convert negative integer to unsigned int"))
    x = r_uint(0)
    i = len(w_value.digits) - 1
    while i >= 0:
        prev = x
        x = (x << SHIFT) + w_value.digits[i]
        if (x >> SHIFT) != prev:
            raise OperationError(space.w_OverflowError, space.wrap(
                "long int too large to convert to unsigned int"))
        i -= 1
    return x

def repr__Long(space, w_long):
    return space.wrap(_format(w_long, 10, True))

def str__Long(space, w_long):
    return space.wrap(_format(w_long, 10, False))

def eq__Long_Long(space, w_long1, w_long2):
    if (w_long1.sign != w_long2.sign or
        len(w_long1.digits) != len(w_long2.digits)):
        return space.newbool(False)
    i = 0
    ld = len(w_long1.digits)
    while i < ld:
        if w_long1.digits[i] != w_long2.digits[i]:
            return space.newbool(False)
        i += 1
    return space.newbool(True)

def lt__Long_Long(space, w_long1, w_long2):
    if w_long1.sign > w_long2.sign:
        return space.newbool(False)
    if w_long1.sign < w_long2.sign:
        return space.newbool(True)
    ld1 = len(w_long1.digits)
    ld2 = len(w_long2.digits)
    if ld1 > ld2:
        if w_long2.sign > 0:
            return space.newbool(False)
        else:
            return space.newbool(True)
    elif ld1 < ld2:
        if w_long2.sign > 0:
            return space.newbool(True)
        else:
            return space.newbool(False)
    i = ld1 - 1
    while i >= 0:
        d1 = w_long1.digits[i]
        d2 = w_long2.digits[i]
        if d1 < d2:
            if w_long2.sign > 0:
                return space.newbool(True)
            else:
                return space.newbool(False)
        elif d1 > d2:
            if w_long2.sign > 0:
                return space.newbool(False)
            else:
                return space.newbool(True)
        i -= 1
    return space.newbool(False)

def hash__Long(space, w_value):
    return space.wrap(_hash(w_value))

# coerce
def coerce__Long_Long(space, w_long1, w_long2):
    return space.newtuple([w_long1, w_long2])


def add__Long_Long(space, w_long1, w_long2):
    if w_long1.sign < 0:
        if w_long2.sign < 0:
            result = _x_add(w_long1, w_long2)
            if result.sign != 0:
                result.sign = -result.sign
        else:
            result = _x_sub(w_long2, w_long1)
    else:
        if w_long2.sign < 0:
            result = _x_sub(w_long1, w_long2)
        else:
            result = _x_add(w_long1, w_long2)
    result._normalize()
    return result

def sub__Long_Long(space, w_long1, w_long2):
    if w_long1.sign < 0:
        if w_long2.sign < 0:
            result = _x_sub(w_long1, w_long2)
        else:
            result = _x_add(w_long1, w_long2)
        result.sign = -result.sign
    else:
        if w_long2.sign < 0:
            result = _x_add(w_long1, w_long2)
        else:
            result = _x_sub(w_long1, w_long2)
    result._normalize()
    return result

def mul__Long_Long(space, w_long1, w_long2):
    result = _x_mul(w_long1, w_long2)
    result.sign = w_long1.sign * w_long2.sign
    return result

def truediv__Long_Long(space, w_long1, w_long2):
    div = _long_true_divide(w_long1, w_long2)
    return space.newfloat(div)

def floordiv__Long_Long(space, w_long1, w_long2):
    div, mod = _l_divmod(w_long1, w_long2)
    return div

def div__Long_Long(space, w_long1, w_long2):
    return floordiv__Long_Long(space, w_long1, w_long2)

def mod__Long_Long(space, w_long1, w_long2):
    div, mod = _l_divmod(w_long1, w_long2)
    return mod

def divmod__Long_Long(space, w_long1, w_long2):
    div, mod = _l_divmod(w_long1, w_long2)
    return space.newtuple([div, mod])

# helper for pow()
def _impl_long_long_pow(space, lv, lw, lz=None):
    if lw.sign < 0:
        if lz is not None:
            raise OperationError(space.w_TypeError,
                             space.wrap("pow() 2nd argument "
                 "cannot be negative when 3rd argument specified"))
        return space.pow(space.newfloat(_AsDouble(lv)),
                         space.newfloat(_AsDouble(lw)),
                         space.w_None)
    if lz is not None:
        if lz.sign == 0:
            raise OperationError(space.w_ValueError,
                                    space.wrap("pow() 3rd argument cannot be 0"))
    result = W_LongObject(space, [Digit(1)], 1)
    if lw.sign == 0:
        if lz is not None:
            result = mod__Long_Long(space, result, lz)
        return result
    if lz is not None:
        temp = mod__Long_Long(space, lv, lz)
    else:
        temp = lv
    i = 0
    # Treat the most significant digit specially to reduce multiplications
    while i < len(lw.digits) - 1:
        j = 0
        m = Digit(1)
        di = lw.digits[i]
        while j < SHIFT:
            if di & m:
                result = mul__Long_Long(space, result, temp)
            temp = mul__Long_Long(space, temp, temp)
            if lz is not None:
                result = mod__Long_Long(space, result, lz)
                temp = mod__Long_Long(space, temp, lz)
            m = m << 1
            j += 1
        i += 1
    m = Digit(1) << (SHIFT - 1)
    highest_set_bit = SHIFT
    j = SHIFT - 1
    di = lw.digits[i]
    while j >= 0:
        if di & m:
            highest_set_bit = j
            break
        m = m >> 1
        j -= 1
    assert highest_set_bit != SHIFT, "long not normalized"
    j = 0
    m = Digit(1)
    while j <= highest_set_bit:
        if di & m:
            result = mul__Long_Long(space, result, temp)
        temp = mul__Long_Long(space, temp, temp)
        if lz is not None:
            result = mod__Long_Long(space, result, lz)
            temp = mod__Long_Long(space, temp, lz)
        m = m << 1
        j += 1
    if lz:
        result = mod__Long_Long(space, result, lz)
    return result


def pow__Long_Long_Long(space, w_long1, w_long2, w_long3):
    return _impl_long_long_pow(space, w_long1, w_long2, w_long3)

def pow__Long_Long_None(space, w_long1, w_long2, w_long3):
    return _impl_long_long_pow(space, w_long1, w_long2, None)

def neg__Long(space, w_long1):
    return W_LongObject(space, w_long1.digits[:], -w_long1.sign)

def pos__Long(space, w_long):
    return long__Long(space, w_long)

def abs__Long(space, w_long):
    return W_LongObject(space, w_long.digits[:], abs(w_long.sign))

def nonzero__Long(space, w_long):
    return space.newbool(w_long.sign != 0)

def invert__Long(space, w_long): #Implement ~x as -(x + 1)
    w_lpp = add__Long_Long(space, w_long, W_LongObject(space, [Digit(1)], 1))
    return neg__Long(space, w_lpp)

def lshift__Long_Long(space, w_long1, w_long2):
    if w_long2.sign < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("negative shift count"))
    elif w_long2.sign == 0:
        return w_long1
    try:
        shiftby = int_w__Long(space, w_long2)
    except OverflowError:   # b too big
        raise OperationError(space.w_OverflowError,
                             space.wrap("shift count too large"))

    a = w_long1
    # wordshift, remshift = divmod(shiftby, SHIFT)
    wordshift = shiftby // SHIFT
    remshift  = shiftby - wordshift * SHIFT

    oldsize = len(a.digits)
    newsize = oldsize + wordshift
    if remshift:
        newsize += 1
    z = W_LongObject(space, [Digit(0)] * newsize, a.sign)
    # not sure if we will initialize things in the future?
    for i in range(wordshift):
        z.digits[i] = Digit(0)
    accum = Twodigits(0)
    i = wordshift
    j = 0
    while j < oldsize:
        accum |= Twodigits(a.digits[j]) << remshift
        z.digits[i] = Digit(accum & MASK)
        accum >>= SHIFT
        i += 1
        j += 1
    if remshift:
        z.digits[newsize-1] = Digit(accum)
    else:
        assert not accum
    z._normalize()
    return z

def rshift__Long_Long(space, w_long1, w_long2):
    if w_long2.sign < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("negative shift count"))
    elif w_long2.sign == 0:
        return w_long1
    if w_long1.sign == -1:
        w_a1 = invert__Long(space, w_long1)
        w_a2 = rshift__Long_Long(space, w_a1, w_long2)
        return invert__Long(space, w_a2)
    try:
        shiftby = int_w__Long(space, w_long2)
    except OverflowError:   # b too big # XXX maybe just return 0L instead?
        raise OperationError(space.w_OverflowError,
                             space.wrap("shift count too large"))

    a = w_long1
    wordshift = shiftby // SHIFT
    newsize = len(a.digits) - wordshift
    if newsize <= 0:
        return W_LongObject(space, [Digit(0)], 0)

    loshift = shiftby % SHIFT
    hishift = SHIFT - loshift
    lomask = (Digit(1) << hishift) - 1
    himask = MASK ^ lomask
    z = W_LongObject(space, [Digit(0)] * newsize, a.sign)
    i = 0
    j = wordshift
    while i < newsize:
        z.digits[i] = (a.digits[j] >> loshift) & lomask
        if i+1 < newsize:
            z.digits[i] |= (a.digits[j+1] << hishift) & himask
        i += 1
        j += 1
    z._normalize()
    return z

def and__Long_Long(space, w_long1, w_long2):
    return _bitwise(w_long1, '&', w_long2)

def xor__Long_Long(space, w_long1, w_long2):
    return _bitwise(w_long1, '^', w_long2)

def or__Long_Long(space, w_long1, w_long2):
    return _bitwise(w_long1, '|', w_long2)

def oct__Long(space, w_long1):
    return space.wrap(_format(w_long1, 8, True))

def hex__Long(space, w_long1):
    return space.wrap(_format(w_long1, 16, True))

def getnewargs__Long(space, w_long1):
    return space.newtuple([W_LongObject(space, w_long1.digits, w_long1.sign)])


register_all(vars())

# register implementations of ops that recover int op overflows

# binary ops
for opname in ['add', 'sub', 'mul', 'div', 'floordiv', 'truediv', 'mod', 'divmod', 'lshift']:
    exec compile("""
def %(opname)s_ovr__Int_Int(space, w_int1, w_int2):
    w_long1 = delegate_Int2Long(w_int1)
    w_long2 = delegate_Int2Long(w_int2)
    return %(opname)s__Long_Long(space, w_long1, w_long2)
""" % {'opname': opname}, '', 'exec')

    getattr(StdObjSpace.MM, opname).register(globals()['%s_ovr__Int_Int' %opname], W_IntObject, W_IntObject, order=1)

# unary ops
for opname in ['neg', 'abs']:
    exec """
def %(opname)s_ovr__Int(space, w_int1):
    w_long1 = delegate_Int2Long(w_int1)
    return %(opname)s__Long(space, w_long1)
""" % {'opname': opname}

    getattr(StdObjSpace.MM, opname).register(globals()['%s_ovr__Int' %opname], W_IntObject, order=1)

# pow
def pow_ovr__Int_Int_None(space, w_int1, w_int2, w_none3):
    w_long1 = delegate_Int2Long(w_int1)
    w_long2 = delegate_Int2Long(w_int2)
    return pow__Long_Long_None(space, w_long1, w_long2, w_none3)

def pow_ovr__Int_Int_Long(space, w_int1, w_int2, w_long3):
    w_long1 = delegate_Int2Long(w_int1)
    w_long2 = delegate_Int2Long(w_int2)
    return pow__Long_Long_Long(space, w_long1, w_long2, w_long3)

StdObjSpace.MM.pow.register(pow_ovr__Int_Int_None, W_IntObject, W_IntObject, W_NoneObject, order=1)
StdObjSpace.MM.pow.register(pow_ovr__Int_Int_Long, W_IntObject, W_IntObject, W_LongObject, order=1)


# Helper Functions
def args_from_long(l): #YYYYYY
    if l < 0:
        sign = -1
    elif l > 0:
        sign = 1
    else:
        sign = 0
    l = abs(l)
    digits = []
    i = 0
    while l:
        digits.append(Digit(l & MASK))
        l = l >> SHIFT
    if sign == 0:
        digits = [Digit(0)]
    return digits, sign


def _x_add(a, b):
    """ Add the absolute values of two long integers. """
    size_a = len(a.digits)
    size_b = len(b.digits)

    # Ensure a is the larger of the two:
    if size_a < size_b:
        a, b = b, a
        size_a, size_b = size_b, size_a
    z = W_LongObject(a.space, [Digit(0)] * (len(a.digits) + 1), 1)
    i = 0
    carry = Carryadd(0)
    while i < size_b:
        carry += Carryadd(a.digits[i]) + b.digits[i]
        z.digits[i] = Digit(carry & MASK)
        carry >>= SHIFT
        i += 1
    while i < size_a:
        carry += a.digits[i]
        z.digits[i] = Digit(carry & MASK)
        carry >>= SHIFT
        i += 1
    z.digits[i] = Digit(carry)
    z._normalize()
    return z

def _x_sub(a, b):
    """ Subtract the absolute values of two integers. """
    size_a = len(a.digits)
    size_b = len(b.digits)
    sign = 1
    borrow = Carryadd(0)

    # Ensure a is the larger of the two:
    if size_a < size_b:
        sign = -1
        a, b = b, a
        size_a, size_b = size_b, size_a
    elif size_a == size_b:
        # Find highest digit where a and b differ:
        i = size_a - 1
        while i >= 0 and a.digits[i] == b.digits[i]:
            i -= 1
        if i < 0:
            return W_LongObject(a.space, [Digit(0)], 0)
        if a.digits[i] < b.digits[i]:
            sign = -1
            a, b = b, a
        size_a = size_b = i+1
    z = W_LongObject(a.space, [Digit(0)] * size_a, 1)
    i = 0
    while i < size_b:
        # The following assumes unsigned arithmetic
        # works modulo 2**N for some N>SHIFT.
        borrow = Carryadd(a.digits[i]) - b.digits[i] - borrow
        z.digits[i] = Digit(borrow & MASK)
        borrow >>= SHIFT
        borrow &= 1 # Keep only one sign bit
        i += 1
    while i < size_a:
        borrow = a.digits[i] - borrow
        z.digits[i] = Digit(borrow & MASK)
        borrow >>= SHIFT
        borrow &= 1 # Keep only one sign bit
        i += 1
    assert borrow == 0
    if sign < 0:
        z.sign = -1
    z._normalize()
    return z


#Multiply the absolute values of two longs
def _x_mul(a, b):
    size_a = len(a.digits)
    size_b = len(b.digits)
    z = W_LongObject(a.space, [Digit(0)] * (size_a + size_b), 1)
    i = 0
    while i < size_a:
        carry = Carrymul(0)
        f = Twodigits(a.digits[i])
        j = 0
        while j < size_b:
            carry += z.digits[i + j] + b.digits[j] * f
            z.digits[i + j] = Digit(carry & MASK)
            carry >>= SHIFT
            j += 1
        while carry != 0:
            assert i + j < size_a + size_b
            carry += z.digits[i + j]
            z.digits[i + j] = Digit(carry & MASK)
            carry >>= SHIFT
            j += 1
        i += 1
    z._normalize()
    return z

def _inplace_divrem1(pout, pin, n, size=0):
    """
    Divide long pin by non-zero digit n, storing quotient
    in pout, and returning the remainder. It's OK for pin == pout on entry.
    """
    rem = Twodigits(0)
    assert n > 0 and n <= MASK
    if not size:
        size = len(pin.digits)
    size -= 1
    while size >= 0:
        rem = (rem << SHIFT) + pin.digits[size]
        hi = rem // n
        pout.digits[size] = Digit(hi)
        rem -= hi * n
        size -= 1
    return rem

def _divrem1(a, n):
    """
    Divide a long integer by a digit, returning both the quotient
    and the remainder as a tuple.
    The sign of a is ignored; n should not be zero.
    """
    assert n > 0 and n <= MASK
    size = len(a.digits)
    z = W_LongObject(a.space, [Digit(0)] * size, 1)
    rem = _inplace_divrem1(z, a, n)
    z._normalize()
    return z, rem

def _muladd1(a, n, extra):
    """Multiply by a single digit and add a single digit, ignoring the sign.
    """
    size_a = len(a.digits)
    z = W_LongObject(a.space, [Digit(0)] * (size_a+1), 1)
    carry = Carrymul(extra)
    i = 0
    while i < size_a:
        carry += Twodigits(a.digits[i]) * n
        z.digits[i] = Digit(carry & MASK)
        carry >>= SHIFT
        i += 1
    z.digits[i] = Digit(carry)
    z._normalize()
    return z


def _x_divrem(v1, w1):
    """ Unsigned long division with remainder -- the algorithm """
    size_w = len(w1.digits)
    d = Digit(Twodigits(MASK+1) // (w1.digits[size_w-1] + 1))
    v = _muladd1(v1, d, Digit(0))
    w = _muladd1(w1, d, Digit(0))
    size_v = len(v.digits)
    size_w = len(w.digits)
    assert size_v >= size_w and size_w > 1 # Assert checks by div()

    size_a = size_v - size_w + 1
    a = W_LongObject(v.space, [Digit(0)] * size_a, 1)

    j = size_v
    k = size_a - 1
    while k >= 0:
        if j >= size_v:
            vj = Digit(0)
        else:
            vj = v.digits[j]
        carry = Stwodigits(0) # note: this must hold two digits and a sign!

        if vj == w.digits[size_w-1]:
            q = Twodigits(MASK)
        else:
            q = ((Twodigits(vj) << SHIFT) + v.digits[j-1]) // w.digits[size_w-1]

        # notabene!
        # this check needs a signed two digits result
        # or we get an overflow.
        while (w.digits[size_w-2] * q >
                ((
                    (Stwodigits(vj) << SHIFT) # this one dominates
                    + Stwodigits(v.digits[j-1])
                    - Stwodigits(q) * Stwodigits(w.digits[size_w-1])
                                ) << SHIFT)
                + Stwodigits(v.digits[j-2])):
            q -= 1
        i = 0
        while i < size_w and i+k < size_v:
            z = Stwodigits(w.digits[i] * q)
            zz = z >> SHIFT
            carry += Stwodigits(v.digits[i+k]) - z + (zz << SHIFT)
            v.digits[i+k] = Digit(carry & MASK)
            carry >>= SHIFT
            carry -= zz
            i += 1

        if i+k < size_v:
            carry += Stwodigits(v.digits[i+k])
            v.digits[i+k] = Digit(0)

        if carry == 0:
            a.digits[k] = Digit(q & MASK)
            assert not q >> SHIFT
        else:
            assert carry == -1
            q -= 1
            a.digits[k] = Digit(q & MASK)
            assert not q >> SHIFT

            carry = Stwodigits(0)
            i = 0
            while i < size_w and i+k < size_v:
                carry += Stwodigits(v.digits[i+k]) + Stwodigits(w.digits[i])
                v.digits[i+k] = Digit(carry & MASK)
                carry >>= SHIFT
                i += 1
        j -= 1
        k -= 1

    a._normalize()
    rem, _ = _divrem1(v, d)
    return a, rem


def _divrem(a, b):
    """ Long division with remainder, top-level routine """
    size_a = len(a.digits)
    size_b = len(b.digits)

    if b.sign == 0:
        raise OperationError(a.space.w_ZeroDivisionError,
                             a.space.wrap("long division or modulo by zero"))

    if (size_a < size_b or
        (size_a == size_b and
         a.digits[size_a-1] < b.digits[size_b-1])):
        # |a| < |b|
        z = W_LongObject(a.space, [Digit(0)], 0)
        rem = a
        return z, rem
    if size_b == 1:
        z, urem = _divrem1(a, b.digits[0])
        rem = W_LongObject(a.space, [urem], int(urem != 0))
    else:
        z, rem = _x_divrem(a, b)
    # Set the signs.
    # The quotient z has the sign of a*b;
    # the remainder r has the sign of a,
    # so a = b*z + r.
    if a.sign != b.sign:
        z.sign = - z.sign
    if a.sign < 0 and rem.sign != 0:
        rem.sign = - rem.sign
    return z, rem

# ______________ conversions to double _______________

def _AsScaledDouble(v):
    """
    NBITS_WANTED should be > the number of bits in a double's precision,
    but small enough so that 2**NBITS_WANTED is within the normal double
    range.  nbitsneeded is set to 1 less than that because the most-significant
    Python digit contains at least 1 significant bit, but we don't want to
    bother counting them (catering to the worst case cheaply).

    57 is one more than VAX-D double precision; I (Tim) don't know of a double
    format with more precision than that; it's 1 larger so that we add in at
    least one round bit to stand in for the ignored least-significant bits.
    """
    NBITS_WANTED = 57
    multiplier = float(1 << SHIFT)
    if v.sign == 0:
        return 0.0, 0
    i = len(v.digits) - 1
    sign = v.sign
    x = float(v.digits[i])
    nbitsneeded = NBITS_WANTED - 1
    # Invariant:  i Python digits remain unaccounted for.
    while i > 0 and nbitsneeded > 0:
        i -= 1
        x = x * multiplier + float(v.digits[i])
        nbitsneeded -= SHIFT
    # There are i digits we didn't shift in.  Pretending they're all
    # zeroes, the true value is x * 2**(i*SHIFT).
    exponent = i
    assert x > 0.0
    return x * sign, exponent

def isinf(x):
    return x != 0.0 and x / 2 == x

##def ldexp(x, exp):
##    assert type(x) is float
##    lb1 = LONG_BIT - 1
##    multiplier = float(Digit(1) << lb1)
##    while exp >= lb1:
##        x *= multiplier
##        exp -= lb1
##    if exp:
##        x *= float(Digit(1) << exp)
##    return x

# note that math.ldexp checks for overflows,
# while the C ldexp is not guaranteed to do.
# XXX make sure that we don't ignore this!

def _AsDouble(v):
    """ Get a C double from a long int object. """
    x, e = _AsScaledDouble(v)
    if e <= sys.maxint / SHIFT:
        x = math.ldexp(x, e * SHIFT)
        #if not isinf(x):
        # this is checked by math.ldexp
        return x
    raise OverflowError # can't say "long int too large to convert to float"

def _long_true_divide(a, b):
    try:
        ad, aexp = _AsScaledDouble(a)
        bd, bexp = _AsScaledDouble(b)
        if bd == 0.0:
            raise OperationError(a.space.w_ZeroDivisionError,
                                 a.space.wrap("long division or modulo by zero"))

        # True value is very close to ad/bd * 2**(SHIFT*(aexp-bexp))
        ad /= bd   # overflow/underflow impossible here
        aexp -= bexp
        if aexp > sys.maxint / SHIFT:
            raise OverflowError
        elif aexp < -(sys.maxint / SHIFT):
            return 0.0 # underflow to 0
        ad = math.ldexp(ad, aexp * SHIFT)
        ##if isinf(ad):   # ignore underflow to 0.0
        ##    raise OverflowError
        # math.ldexp checks and raises
        return ad
    except OverflowError:
        raise OperationError(a.space.w_OverflowError,
                             a.space.wrap("long/long too large for a float"))


def _FromDouble(space, dval):
    """ Create a new long int object from a C double """
    neg = 0
    if isinf(dval):
        raise OperationError(space.w_OverflowError,
                             space.wrap("cannot convert float infinity to long"))
    if dval < 0.0:
        neg = 1
        dval = -dval
    frac, expo = math.frexp(dval) # dval = frac*2**expo; 0.0 <= frac < 1.0
    if expo <= 0:
        return W_LongObject(space, [Digit(0)], 0)
    ndig = (expo-1) // SHIFT + 1 # Number of 'digits' in result
    v = W_LongObject(space, [Digit(0)] * ndig, 1)
    frac = math.ldexp(frac, (expo-1) % SHIFT + 1)
    for i in range(ndig-1, -1, -1):
        bits = int(frac)
        v.digits[i] = Digit(bits)
        frac -= float(bits)
        frac = math.ldexp(frac, SHIFT)
    if neg:
        v.sign = -1
    return v

def _l_divmod(v, w):
    """
    The / and % operators are now defined in terms of divmod().
    The expression a mod b has the value a - b*floor(a/b).
    The _divrem function gives the remainder after division of
    |a| by |b|, with the sign of a.  This is also expressed
    as a - b*trunc(a/b), if trunc truncates towards zero.
    Some examples:
      a   b   a rem b     a mod b
      13  10   3           3
     -13  10  -3           7
      13 -10   3          -7
     -13 -10  -3          -3
    So, to get from rem to mod, we have to add b if a and b
    have different signs.  We then subtract one from the 'div'
    part of the outcome to keep the invariant intact.
    """
    div, mod = _divrem(v, w)
    if mod.sign * w.sign == -1:
        mod = add__Long_Long(v.space, mod, w)
        one = W_LongObject(v.space, [Digit(1)], 1)
        div = sub__Long_Long(v.space, div, one)
    return div, mod


def _format(a, base, addL):
    """
    Convert a long int object to a string, using a given conversion base.
    Return a string object.
    If base is 8 or 16, add the proper prefix '0' or '0x'.
    """
    size_a = len(a.digits)

    assert base >= 2 and base <= 36

    sign = False

    # Compute a rough upper bound for the length of the string
    i = base
    bits = 0
    while i > 1:
        bits += 1
        i >>= 1
    i = 5 + int(bool(addL)) + (size_a*SHIFT + bits-1) // bits
    s = [chr(0)] * i
    p = i
    if addL:
        p -= 1
        s[p] = 'L'
    if a.sign < 0:
        sign = True

    if a.sign == 0:
        p -= 1
        s[p] = '0'
    elif (base & (base - 1)) == 0:
        # JRH: special case for power-of-2 bases
        accum = Twodigits(0)
        accumbits = 0  # # of bits in accum 
        basebits = 1   # # of bits in base-1
        i = base
        while 1:
            i >>= 1
            if i <= 1:
                break
            basebits += 1

        for i in range(size_a):
            accum |= Twodigits(a.digits[i]) << accumbits
            accumbits += SHIFT
            assert accumbits >= basebits
            while 1:
                cdigit = accum & (base - 1)
                if cdigit < 10:
                    cdigit += ord('0')
                else:
                    cdigit += ord('A') - 10
                assert p > 0
                p -= 1
                s[p] = chr(cdigit)
                accumbits -= basebits
                accum >>= basebits
                if i < size_a - 1:
                    if accumbits < basebits:
                        break
                else:
                    if accum <= 0:
                        break
    else:
        # Not 0, and base not a power of 2.  Divide repeatedly by
        # base, but for speed use the highest power of base that
        # fits in a digit.
        size = size_a
        pin = a # just for similarity to C source which uses the array
        # powbase <- largest power of base that fits in a digit.
        powbase = Digit(base)  # powbase == base ** power
        power = 1
        while 1:
            newpow = Twodigits(powbase) * Digit(base)
            if newpow >> SHIFT:  # doesn't fit in a digit
                break
            powbase = Digit(newpow)
            power += 1

        # Get a scratch area for repeated division.
        scratch = W_LongObject(a.space, [Digit(0)] * size, 1)

        # Repeatedly divide by powbase.
        while 1:
            ntostore = power
            rem = _inplace_divrem1(scratch, pin, powbase, size)
            pin = scratch  # no need to use a again
            if pin.digits[size - 1] == 0:
                size -= 1

            # Break rem into digits.
            assert ntostore > 0
            while 1:
                nextrem = rem // base
                c = rem - nextrem * base
                assert p > 0
                if c < 10:
                    c += ord('0')
                else:
                    c += ord('A') - 10
                p -= 1
                s[p] = chr(c)
                rem = nextrem
                ntostore -= 1
                # Termination is a bit delicate:  must not
                # store leading zeroes, so must get out if
                # remaining quotient and rem are both 0.
                if not (ntostore and (size or rem)):
                    break
            if size == 0:
                break

    if base == 8:
        if a.sign != 0:
            p -= 1
            s[p] = '0'
    elif base == 16:
        p -= 1
        s[p] ='x'
        p -= 1
        s[p] = '0'
    elif base != 10:
        p -= 1
        s[p] = '#'
        p -= 1
        s[p] = chr(ord('0') + base % 10)
        if base > 10:
            p -= 1
            s[p] = chr(ord('0') + base // 10)
    if sign:
        p -= 1
        s[p] = '-'

    if p == 0:
        return ''.join(s)
    else:
        return ''.join(s[p:])


def _bitwise(a, op, b): # '&', '|', '^'
    """ Bitwise and/or/xor operations """

    if a.sign < 0:
        a = invert__Long(a.space, a)
        maska = Digit(MASK)
    else:
        maska = Digit(0)
    if b.sign < 0:
        b = invert__Long(b.space, b)
        maskb = Digit(MASK)
    else:
        maskb = Digit(0)

    negz = 0
    if op == '^':
        if maska != maskb:
            maska ^= MASK
            negz = -1
    elif op == '&':
        if maska and maskb:
            op = '|'
            maska ^= MASK
            maskb ^= MASK
            negz = -1
    elif op == '|':
        if maska or maskb:
            op = '&'
            maska ^= MASK
            maskb ^= MASK
            negz = -1

    # JRH: The original logic here was to allocate the result value (z)
    # as the longer of the two operands.  However, there are some cases
    # where the result is guaranteed to be shorter than that: AND of two
    # positives, OR of two negatives: use the shorter number.  AND with
    # mixed signs: use the positive number.  OR with mixed signs: use the
    # negative number.  After the transformations above, op will be '&'
    # iff one of these cases applies, and mask will be non-0 for operands
    # whose length should be ignored.

    size_a = len(a.digits)
    size_b = len(b.digits)
    if op == '&':
        if maska:
            size_z = size_b
        else:
            if maskb:
                size_z = size_a
            else:
                size_z = min(size_a, size_b)
    else:
        size_z = max(size_a, size_b)

    z = W_LongObject(a.space, [Digit(0)] * size_z, 1)

    for i in range(size_z):
        if i < size_a:
            diga = a.digits[i] ^ maska
        else:
            diga = maska
        if i < size_b:
            digb = b.digits[i] ^ maskb
        else:
            digb = maskb
        if op == '&':
            z.digits[i] = diga & digb
        elif op == '|':
            z.digits[i] = diga | digb
        elif op == '^':
            z.digits[i] = diga ^ digb

    z._normalize()
    if negz == 0:
        return z
    return invert__Long(z.space, z)

def _AsLong(v):
    """
    Get an integer from a long int object.
    Returns -1 and sets an error condition if overflow occurs.
    """
    # This version by Tim Peters
    i = len(v.digits) - 1
    sign = v.sign
    if not sign:
        return 0
    x = r_uint(0)
    while i >= 0:
        prev = x
        x = (x << SHIFT) + v.digits[i]
        if (x >> SHIFT) != prev:
            raise OverflowError
        i -= 1

    # Haven't lost any bits, but if the sign bit is set we're in
    # trouble *unless* this is the min negative number.  So,
    # trouble iff sign bit set && (positive || some bit set other
    # than the sign bit).
    if int(x) < 0 and (sign > 0 or (x << 1) != 0):
            raise OverflowError
    return intmask(int(x) * sign)

def _hash(v):
    # This is designed so that Python ints and longs with the
    # same value hash to the same value, otherwise comparisons
    # of mapping keys will turn out weird
    i = len(v.digits) - 1
    sign = v.sign
    x = 0
    LONG_BIT_SHIFT = LONG_BIT - SHIFT
    while i >= 0:
        # Force a native long #-bits (32 or 64) circular shift
        x = ((x << SHIFT) & ~MASK) | ((x >> LONG_BIT_SHIFT) & MASK)
        x += v.digits[i]
        i -= 1
    x = intmask(x * sign)
    if x == -1:
        x = -2
    return x

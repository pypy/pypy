import sys, operator
from pypy.objspace.std.objspace import *
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.floatobject import W_FloatObject
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.rpython.rarithmetic import LONG_BIT, LONG_MASK, intmask, r_uint

import math

# It took many days of debugging and testing, until
# I (chris) finally understood how things work and where
# to expect overflows in the division code.
# In the end, I decided to throw this all out and to use
# plain integer expressions. r_uint and friends should go away!
# Unsignedness can be completely deduced by back-propagation
# of masking. I will change the annotator to do this.
# Having no special types at all, but describing everything
# in terms of operations and masks is the stronger way.

# Digit size:
# SHIFT cannot be larger than below, for the moment.
# In division, the native integer type must be able to hold
# a sign bit plus two digits plus 1 overflow bit.
# As a result, our digits will be 15 bits with one unused
# bit, exactly as it is in CPython.
#
# The algorithms are anyway not bound to a given digit size.
# There are different models possible, if we support more
# native integer sizes. To support this, the annotator should
# be extended to do some basic size tracking of integers.
#
# Examples:
# C
# Most C implementations have support for signed long long.
# use an unsigned 16 bit unsigned short for the digits.
# The operations which must hold two digits become unsigned long.
# The sign+two digits+overflow register in division becomes
# a 64 bit signed long long.
#
# X86 assembler
# Given that we support some more primitive types for integers,
# this might become a nicer layout for an X86 assembly backend:
# The digit would be 32 bit long unsigned int,
# two digits would be 64 bit long long unsigned int,
# and the signed type mentioned above would be 80 bit extended.
#
# Emulation of different integer types
# Even if we don't have machine support for certain types,
# it might be worth trying to emulate them by providing some
# means of multi-precision integers in rpython.
# It is possible to write primitive code that emits the
# necessary operations for emulation of larger types.
# But we should do some careful testing how fast this code
# will be, compared to just working with native types.
# Probably the primitive types will outperform this.

SHIFT = (LONG_BIT // 2) - 1
MASK = int((1 << SHIFT) - 1)


# Debugging digit array access.
#
# False == no checking at all
# True == check 0 <= value <= MASK

CHECK_DIGITS = True

if CHECK_DIGITS:
    class DigitArray(list):
        def __setitem__(self, idx, value):
            assert value >=0
            assert value <= MASK
            list.__setitem__(self, idx, value)
else:
    DigitArray = list


class W_LongObject(W_Object):
    """This is a reimplementation of longs using a list of digits."""
    # All functions that still rely on the underlying Python's longs are marked
    # with YYYYYY
    # Actually, all methods to be officially used are native implementations.
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
        digits = list(self.digits)
        digits.reverse()
        for d in digits:
            l = l << SHIFT
            l += long(d)
        return l * self.sign

    def unwrap(w_self): #YYYYYY
        return w_self.longval()

    def _normalize(self):
        if len(self.digits) == 0:
            self.sign = 0
            self.digits = [0]
            return
        i = len(self.digits) - 1
        while i != 0 and self.digits[i] == 0:
            self.digits.pop(-1)
            i -= 1
        if len(self.digits) == 1 and self.digits[0] == 0:
            self.sign = 0


registerimplementation(W_LongObject)

USE_KARATSUBA = True # set to False for comparison

# For long multiplication, use the O(N**2) school algorithm unless
# both operands contain more than KARATSUBA_CUTOFF digits (this
# being an internal Python long digit, in base BASE).

KARATSUBA_CUTOFF = 70
KARATSUBA_SQUARE_CUTOFF = 2 * KARATSUBA_CUTOFF

# For exponentiation, use the binary left-to-right algorithm
# unless the exponent contains more than FIVEARY_CUTOFF digits.
# In that case, do 5 bits at a time.  The potential drawback is that
# a table of 2**5 intermediate results is computed.

FIVEARY_CUTOFF = 8

# bool-to-long
def delegate_Bool2Long(w_bool):
    return W_LongObject(w_bool.space, [w_bool.boolval & MASK],
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
        return W_LongObject(space, [0], 0)
    # Count the number of Python digits.
    # We used to pick 5 ("big enough for anything"), but that's a
    # waste of time and space given that 5*15 = 75 bits are rarely
    # needed.
    t = ival
    ndigits = 0
    while t:
        ndigits += 1
        t >>= SHIFT
    v = W_LongObject(space, [0] * ndigits, sign)
    t = ival
    p = 0
    while t:
        v.digits[p] = t & MASK
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
    if USE_KARATSUBA:
        result = _k_mul(w_long1, w_long2)
    else:
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

def _impl_long_long_pow(space, a, b, c=None):
    """ pow(a, b, c) """

    negativeOutput = False  # if x<0 return negative output

    # 5-ary values.  If the exponent is large enough, table is
    # precomputed so that table[i] == a**i % c for i in range(32).
    # python translation: the table is computed when needed.

    if b.sign < 0:  # if exponent is negative
        if c is not None:
            raise OperationError(space.w_TypeError, space.wrap(
                "pow() 2nd argument "
                "cannot be negative when 3rd argument specified"))
        return space.pow(space.newfloat(_AsDouble(a)),
                         space.newfloat(_AsDouble(b)),
                         space.w_None)

    if c is not None:
        # if modulus == 0:
        #     raise ValueError()
        if c.sign == 0:
            raise OperationError(space.w_ValueError, space.wrap(
                "pow() 3rd argument cannot be 0"))

        # if modulus < 0:
        #     negativeOutput = True
        #     modulus = -modulus
        if c.sign < 0:
            negativeOutput = True
            c = W_LongObject(space, c.digits, -c.sign)

        # if modulus == 1:
        #     return 0
        if len(c.digits) == 1 and c.digits[0] == 1:
            return W_LongObject(space, [0], 0)

        # if base < 0:
        #     base = base % modulus
        # Having the base positive just makes things easier.
        if a.sign < 0:
            a, temp = _l_divmod(a, c)
            a = temp

    # At this point a, b, and c are guaranteed non-negative UNLESS
    # c is NULL, in which case a may be negative. */

    z = W_LongObject(space, [1], 1)

    # python adaptation: moved macros REDUCE(X) and MULT(X, Y, result)
    # into helper function result = _help_mult(x, y, c)
    if len(b.digits) <= FIVEARY_CUTOFF:
        # Left-to-right binary exponentiation (HAC Algorithm 14.79)
        # http://www.cacr.math.uwaterloo.ca/hac/about/chap14.pdf
        i = len(b.digits) - 1
        while i >= 0:
            bi = b.digits[i]
            j = 1 << (SHIFT-1)
            while j != 0:
                z = _help_mult(z, z, c)
                if bi & j:
                    z = _help_mult(z, a, c)
                j >>= 1
            i -= 1
    else:
        # Left-to-right 5-ary exponentiation (HAC Algorithm 14.82)
        # z still holds 1L
        table = [z] * 32
        table[0] = z;
        for i in range(1, 32):
            table[i] = _help_mult(table[i-1], a, c)
        i = len(b.digits) - 1
        while i >= 0:
            bi = b.digits[i]
            j = j = SHIFT - 5
            while j >= 0:
                index = (bi >> j) & 0x1f
                for k in range(5):
                    z = _help_mult(z, z, c)
                if index:
                    z = _help_mult(z, table[index], c)
                j -= 5
            i -= 1

    if negativeOutput and z.sign != 0:
        z = sub__Long_Long(z.space, z, c)
    return z

def _help_mult(x, y, c):
    """
    Multiply two values, then reduce the result:
    result = X*Y % c.  If c is NULL, skip the mod.
    """
    res = mul__Long_Long(x.space, x, y)
    # Perform a modular reduction, X = X % c, but leave X alone if c
    # is NULL.
    if c is not None:
        res, temp = _l_divmod(res, c)
        res = temp
    return res

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
    w_lpp = add__Long_Long(space, w_long, W_LongObject(space, [1], 1))
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
    z = W_LongObject(space, [0] * newsize, a.sign)
    # not sure if we will initialize things in the future?
    for i in range(wordshift):
        z.digits[i] = 0
    accum = 0
    i = wordshift
    j = 0
    while j < oldsize:
        accum |= a.digits[j] << remshift
        z.digits[i] = accum & MASK
        accum >>= SHIFT
        i += 1
        j += 1
    if remshift:
        z.digits[newsize-1] = accum
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
        return W_LongObject(space, [0], 0)

    loshift = shiftby % SHIFT
    hishift = SHIFT - loshift
    lomask = (1 << hishift) - 1
    himask = MASK ^ lomask
    z = W_LongObject(space, [0] * newsize, a.sign)
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
        digits.append(intmask(l & MASK))
        l = l >> SHIFT
    if sign == 0:
        digits = [0]
    return digits, sign


def _x_add(a, b):
    """ Add the absolute values of two long integers. """
    size_a = len(a.digits)
    size_b = len(b.digits)

    # Ensure a is the larger of the two:
    if size_a < size_b:
        a, b = b, a
        size_a, size_b = size_b, size_a
    z = W_LongObject(a.space, [0] * (len(a.digits) + 1), 1)
    i = 0
    carry = 0
    while i < size_b:
        carry += a.digits[i] + b.digits[i]
        z.digits[i] = carry & MASK
        carry >>= SHIFT
        i += 1
    while i < size_a:
        carry += a.digits[i]
        z.digits[i] = carry & MASK
        carry >>= SHIFT
        i += 1
    z.digits[i] = carry
    z._normalize()
    return z

def _x_sub(a, b):
    """ Subtract the absolute values of two integers. """
    size_a = len(a.digits)
    size_b = len(b.digits)
    sign = 1
    borrow = 0

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
            return W_LongObject(a.space, [0], 0)
        if a.digits[i] < b.digits[i]:
            sign = -1
            a, b = b, a
        size_a = size_b = i+1
    z = W_LongObject(a.space, [0] * size_a, 1)
    i = 0
    while i < size_b:
        # The following assumes unsigned arithmetic
        # works modulo 2**N for some N>SHIFT.
        borrow = a.digits[i] - b.digits[i] - borrow
        z.digits[i] = borrow & MASK
        borrow >>= SHIFT
        borrow &= 1 # Keep only one sign bit
        i += 1
    while i < size_a:
        borrow = a.digits[i] - borrow
        z.digits[i] = borrow & MASK
        borrow >>= SHIFT
        borrow &= 1 # Keep only one sign bit
        i += 1
    assert borrow == 0
    if sign < 0:
        z.sign = -1
    z._normalize()
    return z


def _x_mul(a, b):
    """
    Grade school multiplication, ignoring the signs.
    Returns the absolute value of the product, or NULL if error.
    """

    size_a = len(a.digits)
    size_b = len(b.digits)
    z = W_LongObject(a.space, [0] * (size_a + size_b), 1)
    if a == b:
        # Efficient squaring per HAC, Algorithm 14.16:
        # http://www.cacr.math.uwaterloo.ca/hac/about/chap14.pdf
        # Gives slightly less than a 2x speedup when a == b,
        # via exploiting that each entry in the multiplication
        # pyramid appears twice (except for the size_a squares).
        i = 0
        while i < size_a:
            f = a.digits[i]
            pz = i << 1
            pa = i + 1
            paend = size_a

            carry = z.digits[pz] + f * f
            z.digits[pz] = carry & MASK
            pz += 1
            carry >>= SHIFT
            assert carry <= MASK

            # Now f is added in twice in each column of the
            # pyramid it appears.  Same as adding f<<1 once.
            f <<= 1
            while pa < paend:
                carry += z.digits[pz] + a.digits[pa] * f
                pa += 1
                z.digits[pz] = carry & MASK
                pz += 1
                carry >>= SHIFT
                assert carry <= (MASK << 1)
            if carry:
                carry += z.digits[pz]
                z.digits[pz] = carry & MASK
                pz += 1
                carry >>= SHIFT
            if carry:
                z.digits[pz] += carry & MASK
            assert (carry >> SHIFT) == 0
            i += 1
    else:
        # a is not the same as b -- gradeschool long mult
        i = 0
        while i < size_a:
            carry = 0
            f = a.digits[i]
            pz = i
            pb = 0
            pbend = size_b
            while pb < pbend:
                carry += z.digits[pz] + b.digits[pb] * f
                pb += 1
                z.digits[pz] = carry & MASK
                pz += 1
                carry >>= SHIFT
                assert carry <= MASK
            if carry:
                z.digits[pz] += carry & MASK
            assert (carry >> SHIFT) == 0
            i += 1
    z._normalize()
    return z


def _kmul_split(n, size):
    """
    A helper for Karatsuba multiplication (k_mul).
    Takes a long "n" and an integer "size" representing the place to
    split, and sets low and high such that abs(n) == (high << size) + low,
    viewing the shift as being by digits.  The sign bit is ignored, and
    the return values are >= 0.
    """
    size_n = len(n.digits)
    size_lo = min(size_n, size)

    lo = W_LongObject(n.space, n.digits[:size_lo], 1)
    hi = W_LongObject(n.space, n.digits[size_lo:], 1)
    lo._normalize()
    hi._normalize()
    return hi, lo

def _k_mul(a, b):
    """
    Karatsuba multiplication.  Ignores the input signs, and returns the
    absolute value of the product (or raises if error).
    See Knuth Vol. 2 Chapter 4.3.3 (Pp. 294-295).
    """
    asize = len(a.digits)
    bsize = len(b.digits)
    # (ah*X+al)(bh*X+bl) = ah*bh*X*X + (ah*bl + al*bh)*X + al*bl
    # Let k = (ah+al)*(bh+bl) = ah*bl + al*bh  + ah*bh + al*bl
    # Then the original product is
    #     ah*bh*X*X + (k - ah*bh - al*bl)*X + al*bl
    # By picking X to be a power of 2, "*X" is just shifting, and it's
    # been reduced to 3 multiplies on numbers half the size.

    # We want to split based on the larger number; fiddle so that b
    # is largest.
    if asize > bsize:
        a, b, asize, bsize = b, a, bsize, asize

    # Use gradeschool math when either number is too small.
    if a == b:
        i = KARATSUBA_SQUARE_CUTOFF
    else:
        i = KARATSUBA_CUTOFF
    if asize <= i:
        if a.sign == 0:
            return W_LongObject(a.space, [0], 0)
        else:
            return _x_mul(a, b)

    # If a is small compared to b, splitting on b gives a degenerate
    # case with ah==0, and Karatsuba may be (even much) less efficient
    # than "grade school" then.  However, we can still win, by viewing
    # b as a string of "big digits", each of width a->ob_size.  That
    # leads to a sequence of balanced calls to k_mul.
    if 2 * asize <= bsize:
        return _k_lopsided_mul(a, b)

    # Split a & b into hi & lo pieces.
    shift = bsize >> 1
    ah, al = _kmul_split(a, shift)
    assert ah.sign == 1    # the split isn't degenerate

    if a == b:
        bh = ah
        bl = al
    else:
        bh, bl = _kmul_split(b, shift)

    # The plan:
    # 1. Allocate result space (asize + bsize digits:  that's always
    #    enough).
    # 2. Compute ah*bh, and copy into result at 2*shift.
    # 3. Compute al*bl, and copy into result at 0.  Note that this
    #    can't overlap with #2.
    # 4. Subtract al*bl from the result, starting at shift.  This may
    #    underflow (borrow out of the high digit), but we don't care:
    #    we're effectively doing unsigned arithmetic mod
    #    BASE**(sizea + sizeb), and so long as the *final* result fits,
    #    borrows and carries out of the high digit can be ignored.
    # 5. Subtract ah*bh from the result, starting at shift.
    # 6. Compute (ah+al)*(bh+bl), and add it into the result starting
    #    at shift.

    # 1. Allocate result space.
    ret = W_LongObject(a.space, [0] * (asize + bsize), 1)

    # 2. t1 <- ah*bh, and copy into high digits of result.
    t1 = _k_mul(ah, bh)
    assert t1.sign >= 0
    assert 2*shift + len(t1.digits) <= len(ret.digits)
    ret.digits[2*shift : 2*shift + len(t1.digits)] = t1.digits

    # Zero-out the digits higher than the ah*bh copy. */
    ## ignored, assuming that we initialize to zero
    ##i = ret->ob_size - 2*shift - t1->ob_size;
    ##if (i)
    ##    memset(ret->ob_digit + 2*shift + t1->ob_size, 0,
    ##           i * sizeof(digit));

    # 3. t2 <- al*bl, and copy into the low digits.
    t2 = _k_mul(al, bl)
    assert t2.sign >= 0
    assert len(t2.digits) <= 2*shift # no overlap with high digits
    ret.digits[:len(t2.digits)] = t2.digits

    # Zero out remaining digits.
    ## ignored, assuming that we initialize to zero
    ##i = 2*shift - t2->ob_size;  /* number of uninitialized digits */
    ##if (i)
    ##    memset(ret->ob_digit + t2->ob_size, 0, i * sizeof(digit));

    # 4 & 5. Subtract ah*bh (t1) and al*bl (t2).  We do al*bl first
    # because it's fresher in cache.
    i = len(ret.digits) - shift  # # digits after shift
    _v_isub(ret.digits, shift, i, t2.digits, len(t2.digits))
    _v_isub(ret.digits, shift, i, t1.digits, len(t1.digits))
    del t1, t2

    # 6. t3 <- (ah+al)(bh+bl), and add into result.
    t1 = _x_add(ah, al)
    del ah, al

    if a == b:
        t2 = t1
    else:
        t2 = _x_add(bh, bl)
    del bh, bl

    t3 = _k_mul(t1, t2)
    del t1, t2
    assert t3.sign ==1

    # Add t3.  It's not obvious why we can't run out of room here.
    # See the (*) comment after this function.
    _v_iadd(ret.digits, shift, i, t3.digits, len(t3.digits))
    del t3

    ret._normalize()
    return ret

""" (*) Why adding t3 can't "run out of room" above.

Let f(x) mean the floor of x and c(x) mean the ceiling of x.  Some facts
to start with:

1. For any integer i, i = c(i/2) + f(i/2).  In particular,
   bsize = c(bsize/2) + f(bsize/2).
2. shift = f(bsize/2)
3. asize <= bsize
4. Since we call k_lopsided_mul if asize*2 <= bsize, asize*2 > bsize in this
   routine, so asize > bsize/2 >= f(bsize/2) in this routine.

We allocated asize + bsize result digits, and add t3 into them at an offset
of shift.  This leaves asize+bsize-shift allocated digit positions for t3
to fit into, = (by #1 and #2) asize + f(bsize/2) + c(bsize/2) - f(bsize/2) =
asize + c(bsize/2) available digit positions.

bh has c(bsize/2) digits, and bl at most f(size/2) digits.  So bh+hl has
at most c(bsize/2) digits + 1 bit.

If asize == bsize, ah has c(bsize/2) digits, else ah has at most f(bsize/2)
digits, and al has at most f(bsize/2) digits in any case.  So ah+al has at
most (asize == bsize ? c(bsize/2) : f(bsize/2)) digits + 1 bit.

The product (ah+al)*(bh+bl) therefore has at most

    c(bsize/2) + (asize == bsize ? c(bsize/2) : f(bsize/2)) digits + 2 bits

and we have asize + c(bsize/2) available digit positions.  We need to show
this is always enough.  An instance of c(bsize/2) cancels out in both, so
the question reduces to whether asize digits is enough to hold
(asize == bsize ? c(bsize/2) : f(bsize/2)) digits + 2 bits.  If asize < bsize,
then we're asking whether asize digits >= f(bsize/2) digits + 2 bits.  By #4,
asize is at least f(bsize/2)+1 digits, so this in turn reduces to whether 1
digit is enough to hold 2 bits.  This is so since SHIFT=15 >= 2.  If
asize == bsize, then we're asking whether bsize digits is enough to hold
c(bsize/2) digits + 2 bits, or equivalently (by #1) whether f(bsize/2) digits
is enough to hold 2 bits.  This is so if bsize >= 2, which holds because
bsize >= KARATSUBA_CUTOFF >= 2.

Note that since there's always enough room for (ah+al)*(bh+bl), and that's
clearly >= each of ah*bh and al*bl, there's always enough room to subtract
ah*bh and al*bl too.
"""

def _k_lopsided_mul(a, b):
    """
    b has at least twice the digits of a, and a is big enough that Karatsuba
    would pay off *if* the inputs had balanced sizes.  View b as a sequence
    of slices, each with a->ob_size digits, and multiply the slices by a,
    one at a time.  This gives k_mul balanced inputs to work with, and is
    also cache-friendly (we compute one double-width slice of the result
    at a time, then move on, never bactracking except for the helpful
    single-width slice overlap between successive partial sums).
    """
    asize = len(a.digits)
    bsize = len(b.digits)
    # nbdone is # of b digits already multiplied

    assert asize > KARATSUBA_CUTOFF
    assert 2 * asize <= bsize

    # Allocate result space, and zero it out.
    ret = W_LongObject(a.space, [0] * (asize + bsize), 1)

    # Successive slices of b are copied into bslice.
    #bslice = W_LongObject(a.space, [0] * asize, 1)
    # XXX we cannot pre-allocate, see comments below!
    bslice = W_LongObject(a.space, [0], 1)

    nbdone = 0;
    while bsize > 0:
        nbtouse = min(bsize, asize)

        # Multiply the next slice of b by a.

        #bslice.digits[:nbtouse] = b.digits[nbdone : nbdone + nbtouse]
        # XXX: this would be more efficient if we adopted CPython's
        # way to store the size, instead of resizing the list!
        # XXX change the implementation, encoding length via the sign.
        bslice.digits = b.digits[nbdone : nbdone + nbtouse]
        product = _k_mul(a, bslice)

        # Add into result.
        _v_iadd(ret.digits, nbdone, len(ret.digits) - nbdone,
                 product.digits, len(product.digits))
        del product

        bsize -= nbtouse
        nbdone += nbtouse

    ret._normalize()
    return ret


def _inplace_divrem1(pout, pin, n, size=0):
    """
    Divide long pin by non-zero digit n, storing quotient
    in pout, and returning the remainder. It's OK for pin == pout on entry.
    """
    rem = 0
    assert n > 0 and n <= MASK
    if not size:
        size = len(pin.digits)
    size -= 1
    while size >= 0:
        rem = (rem << SHIFT) + pin.digits[size]
        hi = rem // n
        pout.digits[size] = hi
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
    z = W_LongObject(a.space, [0] * size, 1)
    rem = _inplace_divrem1(z, a, n)
    z._normalize()
    return z, rem

def _v_iadd(x, xofs, m, y, n):
    """
    x[0:m] and y[0:n] are digit vectors, LSD first, m >= n required.  x[0:n]
    is modified in place, by adding y to it.  Carries are propagated as far as
    x[m-1], and the remaining carry (0 or 1) is returned.
    Python adaptation: x is addressed relative to xofs!
    """
    carry = 0;

    assert m >= n
    i = xofs
    iend = xofs + n
    while i < iend:
        carry += x[i] + y[i-xofs]
        x[i] = carry & MASK
        carry >>= SHIFT
        assert (carry & 1) == carry
        i += 1
    iend = xofs + m
    while carry and i < iend:
        carry += x[i]
        x[i] = carry & MASK
        carry >>= SHIFT
        assert (carry & 1) == carry
        i += 1
    return carry

def _v_isub(x, xofs, m, y, n):
    """
    x[0:m] and y[0:n] are digit vectors, LSD first, m >= n required.  x[0:n]
    is modified in place, by subtracting y from it.  Borrows are propagated as
    far as x[m-1], and the remaining borrow (0 or 1) is returned.
    Python adaptation: x is addressed relative to xofs!
    """
    borrow = 0

    assert m >= n
    i = xofs
    iend = xofs + n
    while i < iend:
        borrow = x[i] - y[i-xofs] - borrow
        x[i] = borrow & MASK
        borrow >>= SHIFT
        borrow &= 1    # keep only 1 sign bit
        i += 1
    iend = xofs + m
    while borrow and i < iend:
        borrow = x[i] - borrow
        x[i] = borrow & MASK
        borrow >>= SHIFT
        borrow &= 1
        i += 1
    return borrow


def _muladd1(a, n, extra):
    """Multiply by a single digit and add a single digit, ignoring the sign.
    """
    size_a = len(a.digits)
    z = W_LongObject(a.space, [0] * (size_a+1), 1)
    carry = extra
    assert carry & MASK == carry
    i = 0
    while i < size_a:
        carry += a.digits[i] * n
        z.digits[i] = carry & MASK
        carry >>= SHIFT
        i += 1
    z.digits[i] = carry
    z._normalize()
    return z


def _x_divrem(v1, w1):
    """ Unsigned long division with remainder -- the algorithm """
    size_w = len(w1.digits)
    d = (MASK+1) // (w1.digits[size_w-1] + 1)
    v = _muladd1(v1, d, 0)
    w = _muladd1(w1, d, 0)
    size_v = len(v.digits)
    size_w = len(w.digits)
    assert size_v >= size_w and size_w > 1 # Assert checks by div()

    size_a = size_v - size_w + 1
    a = W_LongObject(v.space, [0] * size_a, 1)

    j = size_v
    k = size_a - 1
    while k >= 0:
        if j >= size_v:
            vj = 0
        else:
            vj = v.digits[j]
        carry = 0

        if vj == w.digits[size_w-1]:
            q = MASK
        else:
            q = ((vj << SHIFT) + v.digits[j-1]) // w.digits[size_w-1]

        while (w.digits[size_w-2] * q >
                ((
                    (vj << SHIFT)
                    + v.digits[j-1]
                    - q * w.digits[size_w-1]
                                ) << SHIFT)
                + v.digits[j-2]):
            q -= 1
        i = 0
        while i < size_w and i+k < size_v:
            z = w.digits[i] * q
            zz = z >> SHIFT
            carry += v.digits[i+k] - z + (zz << SHIFT)
            v.digits[i+k] = carry & MASK
            carry >>= SHIFT
            carry -= zz
            i += 1

        if i+k < size_v:
            carry += v.digits[i+k]
            v.digits[i+k] = 0

        if carry == 0:
            a.digits[k] = q & MASK
            assert not q >> SHIFT
        else:
            assert carry == -1
            q -= 1
            a.digits[k] = q & MASK
            assert not q >> SHIFT

            carry = 0
            i = 0
            while i < size_w and i+k < size_v:
                carry += v.digits[i+k] + w.digits[i]
                v.digits[i+k] = carry & MASK
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
        z = W_LongObject(a.space, [0], 0)
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
##    multiplier = float(1 << lb1)
##    while exp >= lb1:
##        x *= multiplier
##        exp -= lb1
##    if exp:
##        x *= float(1 << exp)
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
        return W_LongObject(space, [0], 0)
    ndig = (expo-1) // SHIFT + 1 # Number of 'digits' in result
    v = W_LongObject(space, [0] * ndig, 1)
    frac = math.ldexp(frac, (expo-1) % SHIFT + 1)
    for i in range(ndig-1, -1, -1):
        bits = int(frac) & MASK # help the future annotator?
        v.digits[i] = bits
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
        one = W_LongObject(v.space, [1], 1)
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
        accum = 0
        accumbits = 0  # # of bits in accum 
        basebits = 1   # # of bits in base-1
        i = base
        while 1:
            i >>= 1
            if i <= 1:
                break
            basebits += 1

        for i in range(size_a):
            accum |= a.digits[i] << accumbits
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
        powbase = base  # powbase == base ** power
        power = 1
        while 1:
            newpow = powbase * base
            if newpow >> SHIFT:  # doesn't fit in a digit
                break
            powbase = newpow
            power += 1

        # Get a scratch area for repeated division.
        scratch = W_LongObject(a.space, [0] * size, 1)

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
        maska = MASK
    else:
        maska = 0
    if b.sign < 0:
        b = invert__Long(b.space, b)
        maskb = MASK
    else:
        maskb = 0

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

    z = W_LongObject(a.space, [0] * size_z, 1)

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
    Raises OverflowError if overflow occurs.
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
    if intmask(x) < 0 and (sign > 0 or (x << 1) != 0):
            raise OverflowError
    return intmask(x*sign)

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

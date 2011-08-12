from pypy.rlib.rarithmetic import LONG_BIT, intmask, r_uint, r_ulonglong
from pypy.rlib.rarithmetic import ovfcheck, r_longlong, widen
from pypy.rlib.rarithmetic import most_neg_value_of_same_type
from pypy.rlib.rfloat import isfinite
from pypy.rlib.debug import make_sure_not_resized, check_regular_int
from pypy.rlib.objectmodel import we_are_translated, specialize
from pypy.rlib import jit
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython import extregistry

import math, sys

# note about digit sizes:
# In division, the native integer type must be able to hold
# a sign bit plus two digits plus 1 overflow bit.

#SHIFT = (LONG_BIT // 2) - 1
SHIFT = 31

MASK = int((1 << SHIFT) - 1)
FLOAT_MULTIPLIER = float(1 << SHIFT)


# Debugging digit array access.
#
# False == no checking at all
# True == check 0 <= value <= MASK


# For long multiplication, use the O(N**2) school algorithm unless
# both operands contain more than KARATSUBA_CUTOFF digits (this
# being an internal Python long digit, in base BASE).

USE_KARATSUBA = True # set to False for comparison
KARATSUBA_CUTOFF = 70
KARATSUBA_SQUARE_CUTOFF = 2 * KARATSUBA_CUTOFF

# For exponentiation, use the binary left-to-right algorithm
# unless the exponent contains more than FIVEARY_CUTOFF digits.
# In that case, do 5 bits at a time.  The potential drawback is that
# a table of 2**5 intermediate results is computed.

## FIVEARY_CUTOFF = 8   disabled for now


def _mask_digit(x):
    if not we_are_translated():
        assert type(x) is not long, "overflow occurred!"
    return intmask(x & MASK)
_mask_digit._annspecialcase_ = 'specialize:argtype(0)'

def _widen_digit(x):
    if not we_are_translated():
        assert type(x) is int, "widen_digit() takes an int, got a %r" % type(x)
    if SHIFT <= 15:
        return int(x)
    return r_longlong(x)

def _store_digit(x):
    if not we_are_translated():
        assert type(x) is int, "store_digit() takes an int, got a %r" % type(x)
    if SHIFT <= 15:
        return rffi.cast(rffi.SHORT, x)
    elif SHIFT <= 31:
        return rffi.cast(rffi.INT, x)
    else:
        raise ValueError("SHIFT too large!")

def _load_digit(x):
    return rffi.cast(lltype.Signed, x)

def _load_unsigned_digit(x):
    return rffi.cast(lltype.Unsigned, x)

NULLDIGIT = _store_digit(0)
ONEDIGIT  = _store_digit(1)

def _check_digits(l):
    for x in l:
        assert type(x) is type(NULLDIGIT)
        assert intmask(x) & MASK == intmask(x)
class Entry(extregistry.ExtRegistryEntry):
    _about_ = _check_digits
    def compute_result_annotation(self, s_list):
        from pypy.annotation import model as annmodel
        assert isinstance(s_list, annmodel.SomeList)
        s_DIGIT = self.bookkeeper.valueoftype(type(NULLDIGIT))
        assert s_DIGIT.contains(s_list.listdef.listitem.s_value)
    def specialize_call(self, hop):
        pass


class rbigint(object):
    """This is a reimplementation of longs using a list of digits."""

    def __init__(self, digits=[], sign=0):
        if len(digits) == 0:
            digits = [NULLDIGIT]
        _check_digits(digits)
        make_sure_not_resized(digits)
        self._digits = digits
        self.sign = sign

    def digit(self, x):
        """Return the x'th digit, as an int."""
        return _load_digit(self._digits[x])

    def widedigit(self, x):
        """Return the x'th digit, as a long long int if needed
        to have enough room to contain two digits."""
        return _widen_digit(_load_digit(self._digits[x]))

    def udigit(self, x):
        """Return the x'th digit, as an unsigned int."""
        return _load_unsigned_digit(self._digits[x])

    def setdigit(self, x, val):
        val = _mask_digit(val)
        assert val >= 0
        self._digits[x] = _store_digit(val)
    setdigit._annspecialcase_ = 'specialize:argtype(2)'

    def numdigits(self):
        return len(self._digits)

    @staticmethod
    @jit.elidable
    def fromint(intval):
        # This function is marked as pure, so you must not call it and
        # then modify the result.
        check_regular_int(intval)
        if intval < 0:
            sign = -1
            ival = r_uint(-intval)
        elif intval > 0:
            sign = 1
            ival = r_uint(intval)
        else:
            return rbigint()
        # Count the number of Python digits.
        # We used to pick 5 ("big enough for anything"), but that's a
        # waste of time and space given that 5*15 = 75 bits are rarely
        # needed.
        t = ival
        ndigits = 0
        while t:
            ndigits += 1
            t >>= SHIFT
        v = rbigint([NULLDIGIT] * ndigits, sign)
        t = ival
        p = 0
        while t:
            v.setdigit(p, t)
            t >>= SHIFT
            p += 1
        return v

    @staticmethod
    @jit.elidable
    def frombool(b):
        # This function is marked as pure, so you must not call it and
        # then modify the result.
        if b:
            return rbigint([ONEDIGIT], 1)
        return rbigint()

    @staticmethod
    def fromlong(l):
        "NOT_RPYTHON"
        return rbigint(*args_from_long(l))

    @staticmethod
    def fromfloat(dval):
        """ Create a new bigint object from a float """
        # This function is not marked as pure because it can raise
        if isfinite(dval):
            return rbigint._fromfloat_finite(dval)
        else:
            raise OverflowError

    @staticmethod
    @jit.elidable
    def _fromfloat_finite(dval):
        sign = 1
        if dval < 0.0:
            sign = -1
            dval = -dval
        frac, expo = math.frexp(dval) # dval = frac*2**expo; 0.0 <= frac < 1.0
        if expo <= 0:
            return rbigint()
        ndig = (expo-1) // SHIFT + 1 # Number of 'digits' in result
        v = rbigint([NULLDIGIT] * ndig, sign)
        frac = math.ldexp(frac, (expo-1) % SHIFT + 1)
        for i in range(ndig-1, -1, -1):
            # use int(int(frac)) as a workaround for a CPython bug:
            # with frac == 2147483647.0, int(frac) == 2147483647L
            bits = int(int(frac))
            v.setdigit(i, bits)
            frac -= float(bits)
            frac = math.ldexp(frac, SHIFT)
        return v

    @staticmethod
    @jit.elidable
    @specialize.argtype(0)
    def fromrarith_int(i):
        # This function is marked as pure, so you must not call it and
        # then modify the result.
        return rbigint(*args_from_rarith_int(i))

    @staticmethod
    @jit.elidable
    def fromdecimalstr(s):
        # This function is marked as pure, so you must not call it and
        # then modify the result.
        return _decimalstr_to_bigint(s)

    @jit.elidable
    def toint(self):
        """
        Get an integer from a bigint object.
        Raises OverflowError if overflow occurs.
        """
        x = self._touint_helper()
        # Haven't lost any bits, but if the sign bit is set we're in
        # trouble *unless* this is the min negative number.  So,
        # trouble iff sign bit set && (positive || some bit set other
        # than the sign bit).
        sign = self.sign
        if intmask(x) < 0 and (sign > 0 or (x << 1) != 0):
            raise OverflowError
        return intmask(x * sign)

    def tolonglong(self):
        return _AsLongLong(self)

    def tobool(self):
        return self.sign != 0

    def touint(self):
        if self.sign == -1:
            raise ValueError("cannot convert negative integer to unsigned int")
        return self._touint_helper()

    def _touint_helper(self):
        x = r_uint(0)
        i = self.numdigits() - 1
        while i >= 0:
            prev = x
            x = (x << SHIFT) + self.udigit(i)
            if (x >> SHIFT) != prev:
                raise OverflowError(
                        "long int too large to convert to unsigned int")
            i -= 1
        return x

    def toulonglong(self):
        if self.sign == -1:
            raise ValueError("cannot convert negative integer to unsigned int")
        return _AsULonglong_ignore_sign(self)

    def uintmask(self):
        return _AsUInt_mask(self)

    def ulonglongmask(self):
        """Return r_ulonglong(self), truncating."""
        return _AsULonglong_mask(self)

    def tofloat(self):
        return _AsDouble(self)

    def format(self, digits, prefix='', suffix=''):
        # 'digits' is a string whose length is the base to use,
        # and where each character is the corresponding digit.
        return _format(self, digits, prefix, suffix)

    def repr(self):
        return _format(self, BASE10, '', 'L')

    def str(self):
        return _format(self, BASE10)

    def eq(self, other):
        if (self.sign != other.sign or
            self.numdigits() != other.numdigits()):
            return False
        i = 0
        ld = self.numdigits()
        while i < ld:
            if self.digit(i) != other.digit(i):
                return False
            i += 1
        return True

    def ne(self, other):
        return not self.eq(other)

    @jit.elidable
    def lt(self, other):
        if self.sign > other.sign:
            return False
        if self.sign < other.sign:
            return True
        ld1 = self.numdigits()
        ld2 = other.numdigits()
        if ld1 > ld2:
            if other.sign > 0:
                return False
            else:
                return True
        elif ld1 < ld2:
            if other.sign > 0:
                return True
            else:
                return False
        i = ld1 - 1
        while i >= 0:
            d1 = self.digit(i)
            d2 = other.digit(i)
            if d1 < d2:
                if other.sign > 0:
                    return True
                else:
                    return False
            elif d1 > d2:
                if other.sign > 0:
                    return False
                else:
                    return True
            i -= 1
        return False

    def le(self, other):
        return not other.lt(self)

    def gt(self, other):
        return other.lt(self)

    def ge(self, other):
        return not self.lt(other)

    def hash(self):
        return _hash(self)

    def add(self, other):
        if self.sign == 0:
            return other
        if other.sign == 0:
            return self
        if self.sign == other.sign:
            result = _x_add(self, other)
        else:
            result = _x_sub(other, self)
        result.sign *= other.sign
        return result

    def sub(self, other):
        if other.sign == 0:
            return self
        if self.sign == 0:
            return rbigint(other._digits[:], -other.sign)
        if self.sign == other.sign:
            result = _x_sub(self, other)
        else:
            result = _x_add(self, other)
        result.sign *= self.sign
        result._normalize()
        return result

    def mul(self, other):
        if USE_KARATSUBA:
            result = _k_mul(self, other)
        else:
            result = _x_mul(self, other)
        result.sign = self.sign * other.sign
        return result

    def truediv(self, other):
        div = _bigint_true_divide(self, other)
        return div

    def floordiv(self, other):
        div, mod = self.divmod(other)
        return div

    def div(self, other):
        return self.floordiv(other)

    def mod(self, other):
        div, mod = self.divmod(other)
        return mod

    def divmod(v, w):
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
            mod = mod.add(w)
            div = div.sub(rbigint([_store_digit(1)], 1))
        return div, mod

    def pow(a, b, c=None):
        negativeOutput = False  # if x<0 return negative output

        # 5-ary values.  If the exponent is large enough, table is
        # precomputed so that table[i] == a**i % c for i in range(32).
        # python translation: the table is computed when needed.

        if b.sign < 0:  # if exponent is negative
            if c is not None:
                raise TypeError(
                    "pow() 2nd argument "
                    "cannot be negative when 3rd argument specified")
            # XXX failed to implement
            raise ValueError("bigint pow() too negative")

        if c is not None:
            if c.sign == 0:
                raise ValueError("pow() 3rd argument cannot be 0")

            # if modulus < 0:
            #     negativeOutput = True
            #     modulus = -modulus
            if c.sign < 0:
                negativeOutput = True
                c = c.neg()

            # if modulus == 1:
            #     return 0
            if c.numdigits() == 1 and c.digit(0) == 1:
                return rbigint()

            # if base < 0:
            #     base = base % modulus
            # Having the base positive just makes things easier.
            if a.sign < 0:
                a, temp = a.divmod(c)
                a = temp

        # At this point a, b, and c are guaranteed non-negative UNLESS
        # c is NULL, in which case a may be negative. */

        z = rbigint([_store_digit(1)], 1)

        # python adaptation: moved macros REDUCE(X) and MULT(X, Y, result)
        # into helper function result = _help_mult(x, y, c)
        if 1:   ## b.numdigits() <= FIVEARY_CUTOFF:
            # Left-to-right binary exponentiation (HAC Algorithm 14.79)
            # http://www.cacr.math.uwaterloo.ca/hac/about/chap14.pdf
            i = b.numdigits() - 1
            while i >= 0:
                bi = b.digit(i)
                j = 1 << (SHIFT-1)
                while j != 0:
                    z = _help_mult(z, z, c)
                    if bi & j:
                        z = _help_mult(z, a, c)
                    j >>= 1
                i -= 1
##        else:
##            This code is disabled for now, because it assumes that
##            SHIFT is a multiple of 5.  It could be fixed but it looks
##            like it's more troubles than benefits...
##
##            # Left-to-right 5-ary exponentiation (HAC Algorithm 14.82)
##            # This is only useful in the case where c != None.
##            # z still holds 1L
##            table = [z] * 32
##            table[0] = z
##            for i in range(1, 32):
##                table[i] = _help_mult(table[i-1], a, c)
##            i = b.numdigits() - 1
##            while i >= 0:
##                bi = b.digit(i)
##                j = SHIFT - 5
##                while j >= 0:
##                    index = (bi >> j) & 0x1f
##                    for k in range(5):
##                        z = _help_mult(z, z, c)
##                    if index:
##                        z = _help_mult(z, table[index], c)
##                    j -= 5
##                i -= 1

        if negativeOutput and z.sign != 0:
            z = z.sub(c)
        return z

    def neg(self):
        return rbigint(self._digits, -self.sign)

    def abs(self):
        return rbigint(self._digits, abs(self.sign))

    def invert(self): #Implement ~x as -(x + 1)
        return self.add(rbigint([_store_digit(1)], 1)).neg()

    def lshift(self, int_other):
        if int_other < 0:
            raise ValueError("negative shift count")
        elif int_other == 0:
            return self

        # wordshift, remshift = divmod(int_other, SHIFT)
        wordshift = int_other // SHIFT
        remshift  = int_other - wordshift * SHIFT

        oldsize = self.numdigits()
        newsize = oldsize + wordshift
        if remshift:
            newsize += 1
        z = rbigint([NULLDIGIT] * newsize, self.sign)
        accum = _widen_digit(0)
        i = wordshift
        j = 0
        while j < oldsize:
            accum |= self.widedigit(j) << remshift
            z.setdigit(i, accum)
            accum >>= SHIFT
            i += 1
            j += 1
        if remshift:
            z.setdigit(newsize - 1, accum)
        else:
            assert not accum
        z._normalize()
        return z

    def rshift(self, int_other, dont_invert=False):
        if int_other < 0:
            raise ValueError("negative shift count")
        elif int_other == 0:
            return self
        if self.sign == -1 and not dont_invert:
            a1 = self.invert()
            a2 = a1.rshift(int_other)
            return a2.invert()

        wordshift = int_other // SHIFT
        newsize = self.numdigits() - wordshift
        if newsize <= 0:
            return rbigint()

        loshift = int_other % SHIFT
        hishift = SHIFT - loshift
        lomask = intmask((r_uint(1) << hishift) - 1)
        himask = MASK ^ lomask
        z = rbigint([NULLDIGIT] * newsize, self.sign)
        i = 0
        j = wordshift
        while i < newsize:
            newdigit = (self.digit(j) >> loshift) & lomask
            if i+1 < newsize:
                newdigit |= intmask(self.digit(j+1) << hishift) & himask
            z.setdigit(i, newdigit)
            i += 1
            j += 1
        z._normalize()
        return z

    def and_(self, other):
        return _bitwise(self, '&', other)

    def xor(self, other):
        return _bitwise(self, '^', other)

    def or_(self, other):
        return _bitwise(self, '|', other)

    def oct(self):
        if self.sign == 0:
            return '0L'
        else:
            return _format(self, BASE8, '0', 'L')

    def hex(self):
        return _format(self, BASE16, '0x', 'L')

    def log(self, base):
        # base is supposed to be positive or 0.0, which means we use e
        if base == 10.0:
            return _loghelper(math.log10, self)
        ret = _loghelper(math.log, self)
        if base != 0.0:
            ret /= math.log(base)
        return ret

    def tolong(self):
        "NOT_RPYTHON"
        l = 0L
        digits = list(self._digits)
        digits.reverse()
        for d in digits:
            l = l << SHIFT
            l += intmask(d)
        return l * self.sign

    def _normalize(self):
        if self.numdigits() == 0:
            self.sign = 0
            self._digits = [NULLDIGIT]
            return
        i = self.numdigits()
        while i > 1 and self.digit(i - 1) == 0:
            i -= 1
        assert i >= 1
        if i != self.numdigits():
            self._digits = self._digits[:i]
        if self.numdigits() == 1 and self.digit(0) == 0:
            self.sign = 0

    def bit_length(self):
        i = self.numdigits()
        if i == 1 and self.digit(0) == 0:
            return 0
        msd = self.digit(i - 1)
        msd_bits = 0
        while msd >= 32:
            msd_bits += 6
            msd >>= 6
        msd_bits += [
            0, 1, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4,
            5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5
            ][msd]
        # yes, this can overflow: a huge number which fits 3 gigabytes of
        # memory has around 24 gigabits!
        bits = ovfcheck((i-1) * SHIFT) + msd_bits
        return bits

    def __repr__(self):
        return "<rbigint digits=%s, sign=%s, %s>" % (self._digits,
                                                     self.sign, self.str())

#_________________________________________________________________

# Helper Functions


def _help_mult(x, y, c):
    """
    Multiply two values, then reduce the result:
    result = X*Y % c.  If c is None, skip the mod.
    """
    res = x.mul(y)
    # Perform a modular reduction, X = X % c, but leave X alone if c
    # is NULL.
    if c is not None:
        res, temp = res.divmod(c)
        res = temp
    return res



def digits_from_nonneg_long(l):
    digits = []
    while True:
        digits.append(_store_digit(intmask(l & MASK)))
        l = l >> SHIFT
        if not l:
            return digits[:] # to make it non-resizable
digits_from_nonneg_long._annspecialcase_ = "specialize:argtype(0)"

def digits_for_most_neg_long(l):
    # This helper only works if 'l' is the most negative integer of its
    # type, which in base 2 looks like: 1000000..0000
    digits = []
    while _mask_digit(l) == 0:
        digits.append(NULLDIGIT)
        l = l >> SHIFT
    # now 'l' looks like: ...111100000
    # turn it into:       ...000100000
    # to drop the extra unwanted 1's introduced by the signed right shift
    l = -intmask(l)
    assert l & MASK == l
    digits.append(_store_digit(l))
    return digits[:] # to make it non-resizable
digits_for_most_neg_long._annspecialcase_ = "specialize:argtype(0)"

def args_from_rarith_int1(x):
    if x > 0:
        return digits_from_nonneg_long(x), 1
    elif x == 0:
        return [NULLDIGIT], 0
    elif x != most_neg_value_of_same_type(x):
        # normal case
        return digits_from_nonneg_long(-x), -1
    else:
        # the most negative integer! hacks needed...
        return digits_for_most_neg_long(x), -1
args_from_rarith_int1._annspecialcase_ = "specialize:argtype(0)"

def args_from_rarith_int(x):
    return args_from_rarith_int1(widen(x))
args_from_rarith_int._annspecialcase_ = "specialize:argtype(0)"
# ^^^ specialized by the precise type of 'x', which is typically a r_xxx
#     instance from rlib.rarithmetic

def args_from_long(x):
    "NOT_RPYTHON"
    if x >= 0:
        if x == 0:
            return [NULLDIGIT], 0
        else:
            return digits_from_nonneg_long(x), 1
    else:
        return digits_from_nonneg_long(-x), -1

def _x_add(a, b):
    """ Add the absolute values of two bigint integers. """
    size_a = a.numdigits()
    size_b = b.numdigits()

    # Ensure a is the larger of the two:
    if size_a < size_b:
        a, b = b, a
        size_a, size_b = size_b, size_a
    z = rbigint([NULLDIGIT] * (a.numdigits() + 1), 1)
    i = 0
    carry = r_uint(0)
    while i < size_b:
        carry += a.udigit(i) + b.udigit(i)
        z.setdigit(i, carry)
        carry >>= SHIFT
        i += 1
    while i < size_a:
        carry += a.udigit(i)
        z.setdigit(i, carry)
        carry >>= SHIFT
        i += 1
    z.setdigit(i, carry)
    z._normalize()
    return z

def _x_sub(a, b):
    """ Subtract the absolute values of two integers. """
    size_a = a.numdigits()
    size_b = b.numdigits()
    sign = 1

    # Ensure a is the larger of the two:
    if size_a < size_b:
        sign = -1
        a, b = b, a
        size_a, size_b = size_b, size_a
    elif size_a == size_b:
        # Find highest digit where a and b differ:
        i = size_a - 1
        while i >= 0 and a.digit(i) == b.digit(i):
            i -= 1
        if i < 0:
            return rbigint()
        if a.digit(i) < b.digit(i):
            sign = -1
            a, b = b, a
        size_a = size_b = i+1
    z = rbigint([NULLDIGIT] * size_a, sign)
    borrow = r_uint(0)
    i = 0
    while i < size_b:
        # The following assumes unsigned arithmetic
        # works modulo 2**N for some N>SHIFT.
        borrow = a.udigit(i) - b.udigit(i) - borrow
        z.setdigit(i, borrow)
        borrow >>= SHIFT
        borrow &= 1 # Keep only one sign bit
        i += 1
    while i < size_a:
        borrow = a.udigit(i) - borrow
        z.setdigit(i, borrow)
        borrow >>= SHIFT
        borrow &= 1 # Keep only one sign bit
        i += 1
    assert borrow == 0
    z._normalize()
    return z


def _x_mul(a, b):
    """
    Grade school multiplication, ignoring the signs.
    Returns the absolute value of the product, or None if error.
    """

    size_a = a.numdigits()
    size_b = b.numdigits()
    z = rbigint([NULLDIGIT] * (size_a + size_b), 1)
    if a is b:
        # Efficient squaring per HAC, Algorithm 14.16:
        # http://www.cacr.math.uwaterloo.ca/hac/about/chap14.pdf
        # Gives slightly less than a 2x speedup when a == b,
        # via exploiting that each entry in the multiplication
        # pyramid appears twice (except for the size_a squares).
        i = 0
        while i < size_a:
            f = a.widedigit(i)
            pz = i << 1
            pa = i + 1
            paend = size_a

            carry = z.widedigit(pz) + f * f
            z.setdigit(pz, carry)
            pz += 1
            carry >>= SHIFT
            assert carry <= MASK

            # Now f is added in twice in each column of the
            # pyramid it appears.  Same as adding f<<1 once.
            f <<= 1
            while pa < paend:
                carry += z.widedigit(pz) + a.widedigit(pa) * f
                pa += 1
                z.setdigit(pz, carry)
                pz += 1
                carry >>= SHIFT
                assert carry <= (_widen_digit(MASK) << 1)
            if carry:
                carry += z.widedigit(pz)
                z.setdigit(pz, carry)
                pz += 1
                carry >>= SHIFT
            if carry:
                z.setdigit(pz, z.widedigit(pz) + carry)
            assert (carry >> SHIFT) == 0
            i += 1
    else:
        # a is not the same as b -- gradeschool long mult
        i = 0
        while i < size_a:
            carry = 0
            f = a.widedigit(i)
            pz = i
            pb = 0
            pbend = size_b
            while pb < pbend:
                carry += z.widedigit(pz) + b.widedigit(pb) * f
                pb += 1
                z.setdigit(pz, carry)
                pz += 1
                carry >>= SHIFT
                assert carry <= MASK
            if carry:
                z.setdigit(pz, z.widedigit(pz) + carry)
            assert (carry >> SHIFT) == 0
            i += 1
    z._normalize()
    return z


def _kmul_split(n, size):
    """
    A helper for Karatsuba multiplication (k_mul).
    Takes a bigint "n" and an integer "size" representing the place to
    split, and sets low and high such that abs(n) == (high << size) + low,
    viewing the shift as being by digits.  The sign bit is ignored, and
    the return values are >= 0.
    """
    size_n = n.numdigits()
    size_lo = min(size_n, size)

    lo = rbigint(n._digits[:size_lo], 1)
    hi = rbigint(n._digits[size_lo:], 1)
    lo._normalize()
    hi._normalize()
    return hi, lo

def _k_mul(a, b):
    """
    Karatsuba multiplication.  Ignores the input signs, and returns the
    absolute value of the product (or raises if error).
    See Knuth Vol. 2 Chapter 4.3.3 (Pp. 294-295).
    """
    asize = a.numdigits()
    bsize = b.numdigits()
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
    if a is b:
        i = KARATSUBA_SQUARE_CUTOFF
    else:
        i = KARATSUBA_CUTOFF
    if asize <= i:
        if a.sign == 0:
            return rbigint()     # zero
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
    ret = rbigint([NULLDIGIT] * (asize + bsize), 1)

    # 2. t1 <- ah*bh, and copy into high digits of result.
    t1 = _k_mul(ah, bh)
    assert t1.sign >= 0
    assert 2*shift + t1.numdigits() <= ret.numdigits()
    ret._digits[2*shift : 2*shift + t1.numdigits()] = t1._digits

    # Zero-out the digits higher than the ah*bh copy. */
    ## ignored, assuming that we initialize to zero
    ##i = ret->ob_size - 2*shift - t1->ob_size;
    ##if (i)
    ##    memset(ret->ob_digit + 2*shift + t1->ob_size, 0,
    ##           i * sizeof(digit));

    # 3. t2 <- al*bl, and copy into the low digits.
    t2 = _k_mul(al, bl)
    assert t2.sign >= 0
    assert t2.numdigits() <= 2*shift # no overlap with high digits
    ret._digits[:t2.numdigits()] = t2._digits

    # Zero out remaining digits.
    ## ignored, assuming that we initialize to zero
    ##i = 2*shift - t2->ob_size;  /* number of uninitialized digits */
    ##if (i)
    ##    memset(ret->ob_digit + t2->ob_size, 0, i * sizeof(digit));

    # 4 & 5. Subtract ah*bh (t1) and al*bl (t2).  We do al*bl first
    # because it's fresher in cache.
    i = ret.numdigits() - shift  # # digits after shift
    _v_isub(ret, shift, i, t2, t2.numdigits())
    _v_isub(ret, shift, i, t1, t1.numdigits())
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
    assert t3.sign >=0

    # Add t3.  It's not obvious why we can't run out of room here.
    # See the (*) comment after this function.
    _v_iadd(ret, shift, i, t3, t3.numdigits())
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
    asize = a.numdigits()
    bsize = b.numdigits()
    # nbdone is # of b digits already multiplied

    assert asize > KARATSUBA_CUTOFF
    assert 2 * asize <= bsize

    # Allocate result space, and zero it out.
    ret = rbigint([NULLDIGIT] * (asize + bsize), 1)

    # Successive slices of b are copied into bslice.
    #bslice = rbigint([0] * asize, 1)
    # XXX we cannot pre-allocate, see comments below!
    bslice = rbigint([NULLDIGIT], 1)

    nbdone = 0;
    while bsize > 0:
        nbtouse = min(bsize, asize)

        # Multiply the next slice of b by a.

        #bslice.digits[:nbtouse] = b.digits[nbdone : nbdone + nbtouse]
        # XXX: this would be more efficient if we adopted CPython's
        # way to store the size, instead of resizing the list!
        # XXX change the implementation, encoding length via the sign.
        bslice._digits = b._digits[nbdone : nbdone + nbtouse]
        product = _k_mul(a, bslice)

        # Add into result.
        _v_iadd(ret, nbdone, ret.numdigits() - nbdone,
                 product, product.numdigits())
        del product

        bsize -= nbtouse
        nbdone += nbtouse

    ret._normalize()
    return ret


def _inplace_divrem1(pout, pin, n, size=0):
    """
    Divide bigint pin by non-zero digit n, storing quotient
    in pout, and returning the remainder. It's OK for pin == pout on entry.
    """
    rem = _widen_digit(0)
    assert n > 0 and n <= MASK
    if not size:
        size = pin.numdigits()
    size -= 1
    while size >= 0:
        rem = (rem << SHIFT) + pin.widedigit(size)
        hi = rem // n
        pout.setdigit(size, hi)
        rem -= hi * n
        size -= 1
    return _mask_digit(rem)

def _divrem1(a, n):
    """
    Divide a bigint integer by a digit, returning both the quotient
    and the remainder as a tuple.
    The sign of a is ignored; n should not be zero.
    """
    assert n > 0 and n <= MASK
    size = a.numdigits()
    z = rbigint([NULLDIGIT] * size, 1)
    rem = _inplace_divrem1(z, a, n)
    z._normalize()
    return z, rem

def _v_iadd(x, xofs, m, y, n):
    """
    x and y are rbigints, m >= n required.  x.digits[0:n] is modified in place,
    by adding y.digits[0:m] to it.  Carries are propagated as far as
    x[m-1], and the remaining carry (0 or 1) is returned.
    Python adaptation: x is addressed relative to xofs!
    """
    carry = r_uint(0)

    assert m >= n
    i = xofs
    iend = xofs + n
    while i < iend:
        carry += x.udigit(i) + y.udigit(i-xofs)
        x.setdigit(i, carry)
        carry >>= SHIFT
        assert (carry & 1) == carry
        i += 1
    iend = xofs + m
    while carry and i < iend:
        carry += x.udigit(i)
        x.setdigit(i, carry)
        carry >>= SHIFT
        assert (carry & 1) == carry
        i += 1
    return carry

def _v_isub(x, xofs, m, y, n):
    """
    x and y are rbigints, m >= n required.  x.digits[0:n] is modified in place,
    by substracting y.digits[0:m] to it. Borrows are propagated as
    far as x[m-1], and the remaining borrow (0 or 1) is returned.
    Python adaptation: x is addressed relative to xofs!
    """
    borrow = r_uint(0)

    assert m >= n
    i = xofs
    iend = xofs + n
    while i < iend:
        borrow = x.udigit(i) - y.udigit(i-xofs) - borrow
        x.setdigit(i, borrow)
        borrow >>= SHIFT
        borrow &= 1    # keep only 1 sign bit
        i += 1
    iend = xofs + m
    while borrow and i < iend:
        borrow = x.udigit(i) - borrow
        x.setdigit(i, borrow)
        borrow >>= SHIFT
        borrow &= 1
        i += 1
    return borrow


def _muladd1(a, n, extra=0):
    """Multiply by a single digit and add a single digit, ignoring the sign.
    """
    size_a = a.numdigits()
    z = rbigint([NULLDIGIT] * (size_a+1), 1)
    assert extra & MASK == extra
    carry = _widen_digit(extra)
    i = 0
    while i < size_a:
        carry += a.widedigit(i) * n
        z.setdigit(i, carry)
        carry >>= SHIFT
        i += 1
    z.setdigit(i, carry)
    z._normalize()
    return z


def _x_divrem(v1, w1):
    """ Unsigned bigint division with remainder -- the algorithm """
    size_w = w1.numdigits()
    d = (r_uint(MASK)+1) // (w1.udigit(size_w-1) + 1)
    assert d <= MASK    # because the first digit of w1 is not zero
    d = intmask(d)
    v = _muladd1(v1, d)
    w = _muladd1(w1, d)
    size_v = v.numdigits()
    size_w = w.numdigits()
    assert size_v >= size_w and size_w > 1 # Assert checks by div()

    size_a = size_v - size_w + 1
    a = rbigint([NULLDIGIT] * size_a, 1)

    j = size_v
    k = size_a - 1
    while k >= 0:
        if j >= size_v:
            vj = 0
        else:
            vj = v.widedigit(j)
        carry = 0

        if vj == w.widedigit(size_w-1):
            q = MASK
        else:
            q = ((vj << SHIFT) + v.widedigit(j-1)) // w.widedigit(size_w-1)

        while (w.widedigit(size_w-2) * q >
                ((
                    (vj << SHIFT)
                    + v.widedigit(j-1)
                    - q * w.widedigit(size_w-1)
                                ) << SHIFT)
                + v.widedigit(j-2)):
            q -= 1
        i = 0
        while i < size_w and i+k < size_v:
            z = w.widedigit(i) * q
            zz = z >> SHIFT
            carry += v.widedigit(i+k) - z + (zz << SHIFT)
            v.setdigit(i+k, carry)
            carry >>= SHIFT
            carry -= zz
            i += 1

        if i+k < size_v:
            carry += v.widedigit(i+k)
            v.setdigit(i+k, 0)

        if carry == 0:
            a.setdigit(k, q)
            assert not q >> SHIFT
        else:
            assert carry == -1
            q -= 1
            a.setdigit(k, q)
            assert not q >> SHIFT

            carry = 0
            i = 0
            while i < size_w and i+k < size_v:
                carry += v.udigit(i+k) + w.udigit(i)
                v.setdigit(i+k, carry)
                carry >>= SHIFT
                i += 1
        j -= 1
        k -= 1

    a._normalize()
    rem, _ = _divrem1(v, d)
    return a, rem


def _divrem(a, b):
    """ Long division with remainder, top-level routine """
    size_a = a.numdigits()
    size_b = b.numdigits()

    if b.sign == 0:
        raise ZeroDivisionError("long division or modulo by zero")

    if (size_a < size_b or
        (size_a == size_b and
         a.digit(size_a-1) < b.digit(size_b-1))):
        # |a| < |b|
        z = rbigint()   # result is 0
        rem = a
        return z, rem
    if size_b == 1:
        z, urem = _divrem1(a, b.digit(0))
        rem = rbigint([_store_digit(urem)], int(urem != 0))
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
    if v.sign == 0:
        return 0.0, 0
    i = v.numdigits() - 1
    sign = v.sign
    x = float(v.digit(i))
    nbitsneeded = NBITS_WANTED - 1
    # Invariant:  i Python digits remain unaccounted for.
    while i > 0 and nbitsneeded > 0:
        i -= 1
        x = x * FLOAT_MULTIPLIER + float(v.digit(i))
        nbitsneeded -= SHIFT
    # There are i digits we didn't shift in.  Pretending they're all
    # zeroes, the true value is x * 2**(i*SHIFT).
    exponent = i
    assert x > 0.0
    return x * sign, exponent

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
# YYY no, we decided to do ignore this!

@jit.dont_look_inside
def _AsDouble(n):
    """ Get a C double from a bigint object. """
    # This is a "correctly-rounded" version from Python 2.7.
    #
    from pypy.rlib import rfloat
    DBL_MANT_DIG = rfloat.DBL_MANT_DIG  # 53 for IEEE 754 binary64
    DBL_MAX_EXP = rfloat.DBL_MAX_EXP    # 1024 for IEEE 754 binary64
    assert DBL_MANT_DIG < r_ulonglong.BITS

    # Reduce to case n positive.
    sign = n.sign
    if sign == 0:
        return 0.0
    elif sign < 0:
        n = n.neg()

    # Find exponent: 2**(exp - 1) <= n < 2**exp
    exp = n.bit_length()

    # Get top DBL_MANT_DIG + 2 significant bits of n, with a 'sticky'
    # last bit: that is, the least significant bit of the result is 1
    # iff any of the shifted-out bits is set.
    shift = DBL_MANT_DIG + 2 - exp
    if shift >= 0:
        q = _AsULonglong_mask(n) << shift
        if not we_are_translated():
            assert q == n.tolong() << shift   # no masking actually done
    else:
        shift = -shift
        n2 = n.rshift(shift)
        q = _AsULonglong_mask(n2)
        if not we_are_translated():
            assert q == n2.tolong()           # no masking actually done
        if not n.eq(n2.lshift(shift)):
            q |= 1

    # Now remove the excess 2 bits, rounding to nearest integer (with
    # ties rounded to even).
    q = (q >> 2) + (bool(q & 2) and bool(q & 5))

    if exp > DBL_MAX_EXP or (exp == DBL_MAX_EXP and
                             q == r_ulonglong(1) << DBL_MANT_DIG):
        raise OverflowError("integer too large to convert to float")

    ad = math.ldexp(float(q), exp - DBL_MANT_DIG)
    if sign < 0:
        ad = -ad
    return ad

def _loghelper(func, arg):
    """
    A decent logarithm is easy to compute even for huge bigints, but libm can't
    do that by itself -- loghelper can.  func is log or log10.
    Note that overflow isn't possible:  a bigint can contain
    no more than INT_MAX * SHIFT bits, so has value certainly less than
    2**(2**64 * 2**16) == 2**2**80, and log2 of that is 2**80, which is
    small enough to fit in an IEEE single.  log and log10 are even smaller.
    """
    x, e = _AsScaledDouble(arg)
    if x <= 0.0:
        raise ValueError
    # Value is ~= x * 2**(e*SHIFT), so the log ~=
    # log(x) + log(2) * e * SHIFT.
    # CAUTION:  e*SHIFT may overflow using int arithmetic,
    # so force use of double. */
    return func(x) + (e * float(SHIFT) * func(2.0))
_loghelper._annspecialcase_ = 'specialize:arg(0)'

# ____________________________________________________________

BASE_AS_FLOAT = float(1 << SHIFT)     # note that it may not fit an int

BitLengthTable = ''.join(map(chr, [
    0, 1, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]))

def bits_in_digit(d):
    # returns the unique integer k such that 2**(k-1) <= d <
    # 2**k if d is nonzero, else 0.
    d_bits = 0
    while d >= 32:
        d_bits += 6
        d >>= 6
    d_bits += ord(BitLengthTable[d])
    return d_bits

def _truediv_result(result, negate):
    if negate:
        result = -result
    return result

def _truediv_overflow():
    raise OverflowError("integer division result too large for a float")

def _bigint_true_divide(a, b):
    # A longish method to obtain the floating-point result with as much
    # precision as theoretically possible.  The code is almost directly
    # copied from CPython.  See there (Objects/longobject.c,
    # long_true_divide) for detailled comments.  Method in a nutshell:
    #
    #    0. reduce to case a, b > 0; filter out obvious underflow/overflow
    #    1. choose a suitable integer 'shift'
    #    2. use integer arithmetic to compute x = floor(2**-shift*a/b)
    #    3. adjust x for correct rounding
    #    4. convert x to a double dx with the same value
    #    5. return ldexp(dx, shift).

    from pypy.rlib import rfloat
    DBL_MANT_DIG = rfloat.DBL_MANT_DIG  # 53 for IEEE 754 binary64
    DBL_MAX_EXP = rfloat.DBL_MAX_EXP    # 1024 for IEEE 754 binary64
    DBL_MIN_EXP = rfloat.DBL_MIN_EXP
    MANT_DIG_DIGITS = DBL_MANT_DIG // SHIFT
    MANT_DIG_BITS = DBL_MANT_DIG % SHIFT

    # Reduce to case where a and b are both positive.
    negate = (a.sign < 0) ^ (b.sign < 0)
    if not b.tobool():
        raise ZeroDivisionError("long division or modulo by zero")
    if not a.tobool():
        return _truediv_result(0.0, negate)

    a_size = a.numdigits()
    b_size = b.numdigits()

    # Fast path for a and b small (exactly representable in a double).
    # Relies on floating-point division being correctly rounded; results
    # may be subject to double rounding on x86 machines that operate with
    # the x87 FPU set to 64-bit precision.
    a_is_small = (a_size <= MANT_DIG_DIGITS or
                  (a_size == MANT_DIG_DIGITS+1 and
                   a.digit(MANT_DIG_DIGITS) >> MANT_DIG_BITS == 0))
    b_is_small = (b_size <= MANT_DIG_DIGITS or
                  (b_size == MANT_DIG_DIGITS+1 and
                   b.digit(MANT_DIG_DIGITS) >> MANT_DIG_BITS == 0))
    if a_is_small and b_is_small:
        a_size -= 1
        da = float(a.digit(a_size))
        while True:
            a_size -= 1
            if a_size < 0: break
            da = da * BASE_AS_FLOAT + a.digit(a_size)

        b_size -= 1
        db = float(b.digit(b_size))
        while True:
            b_size -= 1
            if b_size < 0: break
            db = db * BASE_AS_FLOAT + b.digit(b_size)

        return _truediv_result(da / db, negate)

    # Catch obvious cases of underflow and overflow
    diff = a_size - b_size
    if diff > sys.maxint/SHIFT - 1:
        return _truediv_overflow()           # Extreme overflow
    elif diff < 1 - sys.maxint/SHIFT:
        return _truediv_result(0.0, negate)  # Extreme underflow
    # Next line is now safe from overflowing integers
    diff = (diff * SHIFT + bits_in_digit(a.digit(a_size - 1)) -
                           bits_in_digit(b.digit(b_size - 1)))
    # Now diff = a_bits - b_bits.
    if diff > DBL_MAX_EXP:
        return _truediv_overflow()
    elif diff < DBL_MIN_EXP - DBL_MANT_DIG - 1:
        return _truediv_result(0.0, negate)

    # Choose value for shift; see comments for step 1 in CPython.
    shift = max(diff, DBL_MIN_EXP) - DBL_MANT_DIG - 2

    inexact = False

    # x = abs(a * 2**-shift)
    if shift <= 0:
        x = a.lshift(-shift)
    else:
        x = a.rshift(shift, dont_invert=True)
        # set inexact if any of the bits shifted out is nonzero
        if not a.eq(x.lshift(shift)):
            inexact = True

    # x //= b. If the remainder is nonzero, set inexact.
    x, rem = _divrem(x, b)
    if rem.tobool():
        inexact = True

    assert x.tobool()    # result of division is never zero
    x_size = x.numdigits()
    x_bits = (x_size-1)*SHIFT + bits_in_digit(x.digit(x_size-1))

    # The number of extra bits that have to be rounded away.
    extra_bits = max(x_bits, DBL_MIN_EXP - shift) - DBL_MANT_DIG
    assert extra_bits == 2 or extra_bits == 3

    # Round by remembering a modified copy of the low digit of x
    mask = 1 << (extra_bits - 1)
    low = x.udigit(0) | inexact
    if (low & mask) != 0 and (low & (3*mask-1)) != 0:
        low += mask
    x_digit_0 = low & ~(mask-1)

    # Convert x to a double dx; the conversion is exact.
    x_size -= 1
    dx = 0.0
    while x_size > 0:
        dx += x.digit(x_size)
        dx *= BASE_AS_FLOAT
        x_size -= 1
    dx += x_digit_0

    # Check whether ldexp result will overflow a double.
    if (shift + x_bits >= DBL_MAX_EXP and
        (shift + x_bits > DBL_MAX_EXP or dx == math.ldexp(1.0, x_bits))):
        return _truediv_overflow()

    return _truediv_result(math.ldexp(dx, shift), negate)

# ____________________________________________________________

BASE8  = '01234567'
BASE10 = '0123456789'
BASE16 = '0123456789abcdef'

def _format(a, digits, prefix='', suffix=''):
    """
    Convert a bigint object to a string, using a given conversion base.
    Return a string object.
    """
    size_a = a.numdigits()

    base = len(digits)
    assert base >= 2 and base <= 36

    # Compute a rough upper bound for the length of the string
    i = base
    bits = 0
    while i > 1:
        bits += 1
        i >>= 1
    i = 5 + len(prefix) + len(suffix) + (size_a*SHIFT + bits-1) // bits
    s = [chr(0)] * i
    p = i
    j = len(suffix)
    while j > 0:
        p -= 1
        j -= 1
        s[p] = suffix[j]

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
            accum |= a.widedigit(i) << accumbits
            accumbits += SHIFT
            assert accumbits >= basebits
            while 1:
                cdigit = intmask(accum & (base - 1))
                p -= 1
                assert p >= 0
                s[p] = digits[cdigit]
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
        powbase = _widen_digit(base)  # powbase == base ** power
        power = 1
        while 1:
            newpow = powbase * base
            if newpow >> SHIFT:  # doesn't fit in a digit
                break
            powbase = newpow
            power += 1

        # Get a scratch area for repeated division.
        scratch = rbigint([NULLDIGIT] * size, 1)

        # Repeatedly divide by powbase.
        while 1:
            ntostore = power
            rem = _inplace_divrem1(scratch, pin, powbase, size)
            pin = scratch  # no need to use a again
            if pin.digit(size - 1) == 0:
                size -= 1

            # Break rem into digits.
            assert ntostore > 0
            while 1:
                nextrem = rem // base
                c = rem - nextrem * base
                p -= 1
                assert p >= 0
                s[p] = digits[c]
                rem = nextrem
                ntostore -= 1
                # Termination is a bit delicate:  must not
                # store leading zeroes, so must get out if
                # remaining quotient and rem are both 0.
                if not (ntostore and (size or rem)):
                    break
            if size == 0:
                break

    j = len(prefix)
    while j > 0:
        p -= 1
        j -= 1
        s[p] = prefix[j]

    if a.sign < 0:
        p -= 1
        s[p] = '-'

    assert p >= 0    # otherwise, buffer overflow (this is also a
                     # hint for the annotator for the slice below)
    return ''.join(s[p:])


def _bitwise(a, op, b): # '&', '|', '^'
    """ Bitwise and/or/xor operations """

    if a.sign < 0:
        a = a.invert()
        maska = MASK
    else:
        maska = 0
    if b.sign < 0:
        b = b.invert()
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

    size_a = a.numdigits()
    size_b = b.numdigits()
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

    z = rbigint([NULLDIGIT] * size_z, 1)

    for i in range(size_z):
        if i < size_a:
            diga = a.digit(i) ^ maska
        else:
            diga = maska
        if i < size_b:
            digb = b.digit(i) ^ maskb
        else:
            digb = maskb
        if op == '&':
            z.setdigit(i, diga & digb)
        elif op == '|':
            z.setdigit(i, diga | digb)
        elif op == '^':
            z.setdigit(i, diga ^ digb)

    z._normalize()
    if negz == 0:
        return z
    return z.invert()
_bitwise._annspecialcase_ = "specialize:arg(1)"


ULONGLONG_BOUND = r_ulonglong(1L << (r_longlong.BITS-1))
LONGLONG_MIN = r_longlong(-(1L << (r_longlong.BITS-1)))

def _AsLongLong(v):
    """
    Get a r_longlong integer from a bigint object.
    Raises OverflowError if overflow occurs.
    """
    x = _AsULonglong_ignore_sign(v)
    # grr grr grr
    if x >= ULONGLONG_BOUND:
        if x == ULONGLONG_BOUND and v.sign < 0:
            x = LONGLONG_MIN
        else:
            raise OverflowError
    else:
        x = r_longlong(x)
        if v.sign < 0:
            x = -x
    return x

def _AsULonglong_ignore_sign(v):
    x = r_ulonglong(0)
    i = v.numdigits() - 1
    while i >= 0:
        prev = x
        x = (x << SHIFT) + v.widedigit(i)
        if (x >> SHIFT) != prev:
                raise OverflowError(
                    "long int too large to convert to unsigned long long int")
        i -= 1
    return x

def make_unsigned_mask_conversion(T):
    def _As_unsigned_mask(v):
        x = T(0)
        i = v.numdigits() - 1
        while i >= 0:
            x = (x << SHIFT) + T(v.digit(i))
            i -= 1
        if v.sign < 0:
            x = -x
        return x
    return _As_unsigned_mask

_AsULonglong_mask = make_unsigned_mask_conversion(r_ulonglong)
_AsUInt_mask = make_unsigned_mask_conversion(r_uint)

def _hash(v):
    # This is designed so that Python ints and longs with the
    # same value hash to the same value, otherwise comparisons
    # of mapping keys will turn out weird.  Moreover, purely
    # to please decimal.py, we return a hash that satisfies
    # hash(x) == hash(x % ULONG_MAX).  In particular, this
    # implies that hash(x) == hash(x % (2**64-1)).
    i = v.numdigits() - 1
    sign = v.sign
    x = r_uint(0)
    LONG_BIT_SHIFT = LONG_BIT - SHIFT
    while i >= 0:
        # Force a native long #-bits (32 or 64) circular shift
        x = (x << SHIFT) | (x >> LONG_BIT_SHIFT)
        x += v.udigit(i)
        # If the addition above overflowed we compensate by
        # incrementing.  This preserves the value modulo
        # ULONG_MAX.
        if x < v.udigit(i):
            x += 1
        i -= 1
    x = intmask(x * sign)
    return x

#_________________________________________________________________

# a few internal helpers

def digits_max_for_base(base):
    dec_per_digit = 1
    while base ** dec_per_digit < MASK:
        dec_per_digit += 1
    dec_per_digit -= 1
    return base ** dec_per_digit

BASE_MAX = [0, 0] + [digits_max_for_base(_base) for _base in range(2, 37)]
DEC_MAX = digits_max_for_base(10)
assert DEC_MAX == BASE_MAX[10]

def _decimalstr_to_bigint(s):
    # a string that has been already parsed to be decimal and valid,
    # is turned into a bigint
    p = 0
    lim = len(s)
    sign = False
    if s[p] == '-':
        sign = True
        p += 1
    elif s[p] == '+':
        p += 1

    a = rbigint()
    tens = 1
    dig = 0
    ord0 = ord('0')
    while p < lim:
        dig = dig * 10 + ord(s[p]) - ord0
        p += 1
        tens *= 10
        if tens == DEC_MAX or p == lim:
            a = _muladd1(a, tens, dig)
            tens = 1
            dig = 0
    if sign and a.sign == 1:
        a.sign = -1
    return a

def parse_digit_string(parser):
    # helper for objspace.std.strutil
    a = rbigint()
    base = parser.base
    digitmax = BASE_MAX[base]
    tens, dig = 1, 0
    while True:
        digit = parser.next_digit()
        if tens == digitmax or digit < 0:
            a = _muladd1(a, tens, dig)
            if digit < 0:
                break
            dig = digit
            tens = base
        else:
            dig = dig * base + digit
            tens *= base
    a.sign *= parser.sign
    return a

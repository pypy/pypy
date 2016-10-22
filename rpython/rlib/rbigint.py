from rpython.rlib.rarithmetic import LONG_BIT, intmask, longlongmask, r_uint, r_ulonglong
from rpython.rlib.rarithmetic import ovfcheck, r_longlong, widen
from rpython.rlib.rarithmetic import most_neg_value_of_same_type
from rpython.rlib.rfloat import isinf, isnan
from rpython.rlib.rstring import StringBuilder
from rpython.rlib.debug import make_sure_not_resized, check_regular_int
from rpython.rlib.objectmodel import we_are_translated, specialize
from rpython.rlib import jit
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper import extregistry

import math, sys

SUPPORT_INT128 = hasattr(rffi, '__INT128_T')
BYTEORDER = sys.byteorder

# note about digit sizes:
# In division, the native integer type must be able to hold
# a sign bit plus two digits plus 1 overflow bit.

#SHIFT = (LONG_BIT // 2) - 1
if SUPPORT_INT128:
    SHIFT = 63
    UDIGIT_TYPE = r_ulonglong
    if LONG_BIT >= 64:
        UDIGIT_MASK = intmask
    else:
        UDIGIT_MASK = longlongmask
    LONG_TYPE = rffi.__INT128_T
    if LONG_BIT > SHIFT:
        STORE_TYPE = lltype.Signed
        UNSIGNED_TYPE = lltype.Unsigned
    else:
        STORE_TYPE = rffi.LONGLONG
        UNSIGNED_TYPE = rffi.ULONGLONG
else:
    SHIFT = 31
    UDIGIT_TYPE = r_uint
    UDIGIT_MASK = intmask
    STORE_TYPE = lltype.Signed
    UNSIGNED_TYPE = lltype.Unsigned
    LONG_TYPE = rffi.LONGLONG

MASK = int((1 << SHIFT) - 1)
FLOAT_MULTIPLIER = float(1 << SHIFT)

# For BIGINT and INT mix.
#
# The VALID range of an int is different than a valid range of a bigint of length one.
# -1 << LONG_BIT is actually TWO digits, because they are stored without the sign.
if SHIFT == LONG_BIT - 1:
    MIN_INT_VALUE = -1 << SHIFT
    def int_in_valid_range(x):
        if x == MIN_INT_VALUE:
            return False
        return True
else:
    # Means we don't have INT128 on 64bit.
    def int_in_valid_range(x):
        if x > MASK or x < -MASK:
            return False
        return True

int_in_valid_range._always_inline_ = True

# Debugging digit array access.
#
# False == no checking at all
# True == check 0 <= value <= MASK


# For long multiplication, use the O(N**2) school algorithm unless
# both operands contain more than KARATSUBA_CUTOFF digits (this
# being an internal Python long digit, in base BASE).

# Karatsuba is O(N**1.585)
USE_KARATSUBA = True # set to False for comparison

if SHIFT > 31:
    KARATSUBA_CUTOFF = 19
else:
    KARATSUBA_CUTOFF = 38

KARATSUBA_SQUARE_CUTOFF = 2 * KARATSUBA_CUTOFF

# For exponentiation, use the binary left-to-right algorithm
# unless the exponent contains more than FIVEARY_CUTOFF digits.
# In that case, do 5 bits at a time.  The potential drawback is that
# a table of 2**5 intermediate results is computed.

FIVEARY_CUTOFF = 8

@specialize.argtype(0)
def _mask_digit(x):
    return UDIGIT_MASK(x & MASK)

def _widen_digit(x):
    return rffi.cast(LONG_TYPE, x)

@specialize.argtype(0)
def _store_digit(x):
    return rffi.cast(STORE_TYPE, x)

def _load_unsigned_digit(x):
    return rffi.cast(UNSIGNED_TYPE, x)

_load_unsigned_digit._always_inline_ = True

NULLDIGIT = _store_digit(0)
ONEDIGIT = _store_digit(1)

def _check_digits(l):
    for x in l:
        assert type(x) is type(NULLDIGIT)
        assert UDIGIT_MASK(x) & MASK == UDIGIT_MASK(x)

class InvalidEndiannessError(Exception):
    pass

class InvalidSignednessError(Exception):
    pass


class Entry(extregistry.ExtRegistryEntry):
    _about_ = _check_digits

    def compute_result_annotation(self, s_list):
        from rpython.annotator import model as annmodel
        assert isinstance(s_list, annmodel.SomeList)
        s_DIGIT = self.bookkeeper.valueoftype(type(NULLDIGIT))
        assert s_DIGIT.contains(s_list.listdef.listitem.s_value)

    def specialize_call(self, hop):
        hop.exception_cannot_occur()


class rbigint(object):
    """This is a reimplementation of longs using a list of digits."""
    _immutable_ = True
    _immutable_fields_ = ["_digits"]

    def __init__(self, digits=[NULLDIGIT], sign=0, size=0):
        if not we_are_translated():
            _check_digits(digits)
        make_sure_not_resized(digits)
        self._digits = digits
        assert size >= 0
        self.size = size or len(digits)
        self.sign = sign

    # __eq__ and __ne__ method exist for testingl only, they are not RPython!
    def __eq__(self, other):
        # NOT_RPYTHON
        if not isinstance(other, rbigint):
            return NotImplemented
        return self.eq(other)

    def __ne__(self, other):
        # NOT_RPYTHON
        return not (self == other)

    def digit(self, x):
        """Return the x'th digit, as an int."""
        return self._digits[x]
    digit._always_inline_ = True

    def widedigit(self, x):
        """Return the x'th digit, as a long long int if needed
        to have enough room to contain two digits."""
        return _widen_digit(self._digits[x])
    widedigit._always_inline_ = True

    def udigit(self, x):
        """Return the x'th digit, as an unsigned int."""
        return _load_unsigned_digit(self._digits[x])
    udigit._always_inline_ = True

    @specialize.argtype(2)
    def setdigit(self, x, val):
        val = _mask_digit(val)
        assert val >= 0
        self._digits[x] = _store_digit(val)
    setdigit._always_inline_ = True

    def numdigits(self):
        return self.size
    numdigits._always_inline_ = True

    @staticmethod
    @jit.elidable
    def fromint(intval):
        # This function is marked as pure, so you must not call it and
        # then modify the result.
        check_regular_int(intval)

        if intval < 0:
            sign = -1
            ival = -r_uint(intval)
        elif intval > 0:
            sign = 1
            ival = r_uint(intval)
        else:
            return NULLRBIGINT

        carry = ival >> SHIFT
        if carry:
            return rbigint([_store_digit(ival & MASK),
                _store_digit(carry)], sign, 2)
        else:
            return rbigint([_store_digit(ival & MASK)], sign, 1)

    @staticmethod
    @jit.elidable
    def frombool(b):
        # You must not call this function and then modify the result.
        if b:
            return ONERBIGINT
        return NULLRBIGINT

    @staticmethod
    def fromlong(l):
        "NOT_RPYTHON"
        return rbigint(*args_from_long(l))

    @staticmethod
    @jit.elidable
    def fromfloat(dval):
        """ Create a new bigint object from a float """
        # This function is not marked as pure because it can raise
        if isinf(dval):
            raise OverflowError("cannot convert float infinity to integer")
        if isnan(dval):
            raise ValueError("cannot convert float NaN to integer")
        return rbigint._fromfloat_finite(dval)

    @staticmethod
    @jit.elidable
    def _fromfloat_finite(dval):
        sign = 1
        if dval < 0.0:
            sign = -1
            dval = -dval
        frac, expo = math.frexp(dval) # dval = frac*2**expo; 0.0 <= frac < 1.0
        if expo <= 0:
            return NULLRBIGINT
        ndig = (expo-1) // SHIFT + 1 # Number of 'digits' in result
        v = rbigint([NULLDIGIT] * ndig, sign, ndig)
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
        # This function is marked as elidable, so you must not call it and
        # then modify the result.
        return _decimalstr_to_bigint(s)

    @staticmethod
    @jit.elidable
    def fromstr(s, base=0):
        """As string_to_int(), but ignores an optional 'l' or 'L' suffix
        and returns an rbigint."""
        from rpython.rlib.rstring import NumberStringParser, \
            strip_spaces
        s = literal = strip_spaces(s)
        if (s.endswith('l') or s.endswith('L')) and base < 22:
            # in base 22 and above, 'L' is a valid digit!  try: long('L',22)
            s = s[:-1]
        parser = NumberStringParser(s, literal, base, 'long')
        return rbigint._from_numberstring_parser(parser)

    @staticmethod
    def _from_numberstring_parser(parser):
        return parse_digit_string(parser)

    @staticmethod
    @jit.elidable
    def frombytes(s, byteorder, signed):
        if byteorder not in ('big', 'little'):
            raise InvalidEndiannessError()
        if not s:
            return NULLRBIGINT

        if byteorder == 'big':
            msb = ord(s[0])
            itr = range(len(s)-1, -1, -1)
        else:
            msb = ord(s[-1])
            itr = range(0, len(s))

        sign = -1 if msb >= 0x80 and signed else 1
        accum = _widen_digit(0)
        accumbits = 0
        digits = []
        carry = 1

        for i in itr:
            c = _widen_digit(ord(s[i]))
            if sign == -1:
                c = (0xFF ^ c) + carry
                carry = c >> 8
                c &= 0xFF

            accum |= c << accumbits
            accumbits += 8
            if accumbits >= SHIFT:
                digits.append(_store_digit(intmask(accum & MASK)))
                accum >>= SHIFT
                accumbits -= SHIFT

        if accumbits:
            digits.append(_store_digit(intmask(accum)))
        result = rbigint(digits[:], sign)
        result._normalize()
        return result

    @jit.elidable
    def tobytes(self, nbytes, byteorder, signed):
        if byteorder not in ('big', 'little'):
            raise InvalidEndiannessError()
        if not signed and self.sign == -1:
            raise InvalidSignednessError()

        bswap = byteorder == 'big'
        d = _widen_digit(0)
        j = 0
        imax = self.numdigits()
        accum = _widen_digit(0)
        accumbits = 0
        result = StringBuilder(nbytes)
        carry = 1

        for i in range(0, imax):
            d = self.widedigit(i)
            if self.sign == -1:
                d = (d ^ MASK) + carry
                carry = d >> SHIFT
                d &= MASK

            accum |= d << accumbits
            if i == imax - 1:
                # Avoid bogus 0's
                s = d ^ MASK if self.sign == -1 else d
                while s:
                    s >>= 1
                    accumbits += 1
            else:
                accumbits += SHIFT

            while accumbits >= 8:
                if j >= nbytes:
                    raise OverflowError()
                j += 1

                result.append(chr(accum & 0xFF))
                accum >>= 8
                accumbits -= 8

        if accumbits:
            if j >= nbytes:
                raise OverflowError()
            j += 1

            if self.sign == -1:
                # Add a sign bit
                accum |= (~_widen_digit(0)) << accumbits

            result.append(chr(accum & 0xFF))

        if j < nbytes:
            signbyte = 0xFF if self.sign == -1 else 0
            result.append_multiple_char(chr(signbyte), nbytes - j)

        digits = result.build()

        if j == nbytes and nbytes > 0 and signed:
            # If not already set, we cannot contain the sign bit
            msb = digits[-1]
            if (self.sign == -1) != (ord(msb) >= 0x80):
                raise OverflowError()

        if bswap:
            # Bah, this is very inefficient. At least it's not
            # quadratic.
            length = len(digits)
            if length >= 0:
                digits = ''.join([digits[i] for i in range(length-1, -1, -1)])
        return digits

    def toint(self):
        """
        Get an integer from a bigint object.
        Raises OverflowError if overflow occurs.
        """
        if self.numdigits() > MAX_DIGITS_THAT_CAN_FIT_IN_INT:
            raise OverflowError
        return self._toint_helper()

    @jit.elidable
    def _toint_helper(self):
        x = self._touint_helper()
        # Haven't lost any bits so far
        if self.sign >= 0:
            res = intmask(x)
            if res < 0:
                raise OverflowError
        else:
            # Use "-" on the unsigned number, not on the signed number.
            # This is needed to produce valid C code.
            res = intmask(-x)
            if res >= 0:
                raise OverflowError
        return res

    @jit.elidable
    def tolonglong(self):
        return _AsLongLong(self)

    def tobool(self):
        return self.sign != 0

    @jit.elidable
    def touint(self):
        if self.sign == -1:
            raise ValueError("cannot convert negative integer to unsigned int")
        return self._touint_helper()

    @jit.elidable
    def _touint_helper(self):
        x = r_uint(0)
        i = self.numdigits() - 1
        while i >= 0:
            prev = x
            x = (x << SHIFT) + self.udigit(i)
            if (x >> SHIFT) != prev:
                raise OverflowError("long int too large to convert to unsigned int")
            i -= 1
        return x

    @jit.elidable
    def toulonglong(self):
        if self.sign == -1:
            raise ValueError("cannot convert negative integer to unsigned int")
        return _AsULonglong_ignore_sign(self)

    @jit.elidable
    def uintmask(self):
        return _AsUInt_mask(self)

    @jit.elidable
    def ulonglongmask(self):
        """Return r_ulonglong(self), truncating."""
        return _AsULonglong_mask(self)

    @jit.elidable
    def tofloat(self):
        return _AsDouble(self)

    @jit.elidable
    def format(self, digits, prefix='', suffix=''):
        # 'digits' is a string whose length is the base to use,
        # and where each character is the corresponding digit.
        return _format(self, digits, prefix, suffix)

    @jit.elidable
    def repr(self):
        try:
            x = self.toint()
        except OverflowError:
            return self.format(BASE10, suffix="L")
        return str(x) + "L"

    @jit.elidable
    def str(self):
        try:
            x = self.toint()
        except OverflowError:
            return self.format(BASE10)
        return str(x)

    @jit.elidable
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

    @jit.elidable
    def int_eq(self, other):
        """ eq with int """
        
        if not int_in_valid_range(other):
            # Fallback to Long. 
            return self.eq(rbigint.fromint(other))

        if self.numdigits() > 1:
            return False

        return (self.sign * self.digit(0)) == other

    def ne(self, other):
        return not self.eq(other)

    def int_ne(self, other):
        return not self.int_eq(other)

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

    @jit.elidable
    def int_lt(self, other):
        """ lt where other is an int """

        if not int_in_valid_range(other):
            # Fallback to Long.
            return self.lt(rbigint.fromint(other))

        osign = 1
        if other == 0:
            osign = 0
        elif other < 0:
            osign = -1
 
        if self.sign > osign:
            return False
        elif self.sign < osign:
            return True

        digits = self.numdigits()
        
        if digits > 1:
            if osign == 1:
                return False
            else:
                return True

        d1 = self.sign * self.digit(0)
        if d1 < other:
            return True
        return False

    def le(self, other):
        return not other.lt(self)

    def int_le(self, other):
        # Alternative that might be faster, reimplant this. as a check with other + 1. But we got to check for overflow
        # or reduce valid range.

        if self.int_eq(other):
            return True
        return self.int_lt(other)

    def gt(self, other):
        return other.lt(self)

    def int_gt(self, other):
        return not self.int_le(other)

    def ge(self, other):
        return not self.lt(other)

    def int_ge(self, other):
        return not self.int_lt(other)

    @jit.elidable
    def hash(self):
        return _hash(self)

    @jit.elidable
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

    @jit.elidable
    def int_add(self, other):
        if not int_in_valid_range(other):
            # Fallback to long.
            return self.add(rbigint.fromint(other))
        elif self.sign == 0:
            return rbigint.fromint(other)
        elif other == 0:
            return self

        sign = -1 if other < 0 else 1
        if self.sign == sign:
            result = _x_int_add(self, other)
        else:
            result = _x_int_sub(self, other)
            result.sign *= -1
        result.sign *= sign
        return result

    @jit.elidable
    def sub(self, other):
        if other.sign == 0:
            return self
        elif self.sign == 0:
            return rbigint(other._digits[:other.size], -other.sign, other.size)
        elif self.sign == other.sign:
            result = _x_sub(self, other)
        else:
            result = _x_add(self, other)
        result.sign *= self.sign
        return result

    @jit.elidable
    def int_sub(self, other):
        if not int_in_valid_range(other):
            # Fallback to long.
            return self.sub(rbigint.fromint(other))
        elif other == 0:
            return self
        elif self.sign == 0:
            return rbigint.fromint(-other)
        elif self.sign == (-1 if other < 0 else 1):
            result = _x_int_sub(self, other)
        else:
            result = _x_int_add(self, other)
        result.sign *= self.sign
        return result

    @jit.elidable
    def mul(self, b):
        asize = self.numdigits()
        bsize = b.numdigits()

        a = self

        if asize > bsize:
            a, b, asize, bsize = b, a, bsize, asize

        if a.sign == 0 or b.sign == 0:
            return NULLRBIGINT

        if asize == 1:
            if a._digits[0] == NULLDIGIT:
                return NULLRBIGINT
            elif a._digits[0] == ONEDIGIT:
                return rbigint(b._digits[:b.size], a.sign * b.sign, b.size)
            elif bsize == 1:
                res = b.widedigit(0) * a.widedigit(0)
                carry = res >> SHIFT
                if carry:
                    return rbigint([_store_digit(res & MASK), _store_digit(carry)], a.sign * b.sign, 2)
                else:
                    return rbigint([_store_digit(res & MASK)], a.sign * b.sign, 1)

            result = _x_mul(a, b, a.digit(0))
        elif USE_KARATSUBA:
            if a is b:
                i = KARATSUBA_SQUARE_CUTOFF
            else:
                i = KARATSUBA_CUTOFF

            if asize <= i:
                result = _x_mul(a, b)
                """elif 2 * asize <= bsize:
                    result = _k_lopsided_mul(a, b)"""
            else:
                result = _k_mul(a, b)
        else:
            result = _x_mul(a, b)

        result.sign = a.sign * b.sign
        return result

    @jit.elidable
    def int_mul(self, b):
        if not int_in_valid_range(b):
            # Fallback to long.
            return self.mul(rbigint.fromint(b))

        if self.sign == 0 or b == 0:
            return NULLRBIGINT

        asize = self.numdigits()
        digit = abs(b)
        bsign = -1 if b < 0 else 1

        if digit == 1:
            return rbigint(self._digits[:self.size], self.sign * bsign, asize)
        elif asize == 1:
            res = self.widedigit(0) * digit
            carry = res >> SHIFT
            if carry:
                return rbigint([_store_digit(res & MASK), _store_digit(carry)], self.sign * bsign, 2)
            else:
                return rbigint([_store_digit(res & MASK)], self.sign * bsign, 1)

        elif digit & (digit - 1) == 0:
            result = self.lqshift(ptwotable[digit])
        else:
            result = _muladd1(self, digit)

        result.sign = self.sign * bsign
        return result

    @jit.elidable
    def truediv(self, other):
        div = _bigint_true_divide(self, other)
        return div

    @jit.elidable
    def floordiv(self, other):
        if self.sign == 1 and other.numdigits() == 1 and other.sign == 1:
            digit = other.digit(0)
            if digit == 1:
                return rbigint(self._digits[:self.size], 1, self.size)
            elif digit and digit & (digit - 1) == 0:
                return self.rshift(ptwotable[digit])

        div, mod = _divrem(self, other)
        if mod.sign * other.sign == -1:
            if div.sign == 0:
                return ONENEGATIVERBIGINT
            div = div.int_sub(1)

        return div

    def div(self, other):
        return self.floordiv(other)

    @jit.elidable
    def mod(self, other):
        if self.sign == 0:
            return NULLRBIGINT

        if other.sign != 0 and other.numdigits() == 1:
            digit = other.digit(0)
            if digit == 1:
                return NULLRBIGINT
            elif digit == 2:
                modm = self.digit(0) & 1
                if modm:
                    return ONENEGATIVERBIGINT if other.sign == -1 else ONERBIGINT
                return NULLRBIGINT
            elif digit & (digit - 1) == 0:
                mod = self.int_and_(digit - 1)
            else:
                # Perform
                size = self.numdigits() - 1
                if size > 0:
                    rem = self.widedigit(size)
                    size -= 1
                    while size >= 0:
                        rem = ((rem << SHIFT) + self.widedigit(size)) % digit
                        size -= 1
                else:
                    rem = self.digit(0) % digit

                if rem == 0:
                    return NULLRBIGINT
                mod = rbigint([_store_digit(rem)], -1 if self.sign < 0 else 1, 1)
        else:
            div, mod = _divrem(self, other)
        if mod.sign * other.sign == -1:
            mod = mod.add(other)
        return mod

    @jit.elidable
    def int_mod(self, other):
        if self.sign == 0:
            return NULLRBIGINT

        elif not int_in_valid_range(other):
            # Fallback to long.
            return self.mod(rbigint.fromint(other))

        elif other != 0:
            digit = abs(other)
            if digit == 1:
                return NULLRBIGINT
            elif digit == 2:
                modm = self.digit(0) & 1
                if modm:
                    return ONENEGATIVERBIGINT if other < 0 else ONERBIGINT
                return NULLRBIGINT
            elif digit & (digit - 1) == 0:
                mod = self.int_and_(digit - 1)
            else:
                # Perform
                size = self.numdigits() - 1
                if size > 0:
                    rem = self.widedigit(size)
                    size -= 1
                    while size >= 0:
                        rem = ((rem << SHIFT) + self.widedigit(size)) % digit
                        size -= 1
                else:
                    rem = self.digit(0) % digit

                if rem == 0:
                    return NULLRBIGINT
                mod = rbigint([_store_digit(rem)], -1 if self.sign < 0 else 1, 1)
        else:
            raise ZeroDivisionError("long division or modulo by zero")

        if mod.sign * (-1 if other < 0 else 1) == -1:
            mod = mod.int_add(other)
        return mod

    @jit.elidable
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
            if div.sign == 0:
                return ONENEGATIVERBIGINT, mod
            div = div.int_sub(1)
        return div, mod

    @jit.elidable
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

        size_b = b.numdigits()

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
            if c.numdigits() == 1 and c._digits[0] == ONEDIGIT:
                return NULLRBIGINT

            # Reduce base by modulus in some cases:
            # 1. If base < 0.  Forcing the base non-neg makes things easier.
            # 2. If base is obviously larger than the modulus.  The "small
            #    exponent" case later can multiply directly by base repeatedly,
            #    while the "large exponent" case multiplies directly by base 31
            #    times.  It can be unboundedly faster to multiply by
            #    base % modulus instead.
            # We could _always_ do this reduction, but mod() isn't cheap,
            # so we only do it when it buys something.
            if a.sign < 0 or a.numdigits() > c.numdigits():
                a = a.mod(c)

        elif b.sign == 0:
            return ONERBIGINT
        elif a.sign == 0:
            return NULLRBIGINT
        elif size_b == 1:
            if b._digits[0] == NULLDIGIT:
                return ONERBIGINT if a.sign == 1 else ONENEGATIVERBIGINT
            elif b._digits[0] == ONEDIGIT:
                return a
            elif a.numdigits() == 1:
                adigit = a.digit(0)
                digit = b.digit(0)
                if adigit == 1:
                    if a.sign == -1 and digit % 2:
                        return ONENEGATIVERBIGINT
                    return ONERBIGINT
                elif adigit & (adigit - 1) == 0:
                    ret = a.lshift(((digit-1)*(ptwotable[adigit]-1)) + digit-1)
                    if a.sign == -1 and not digit % 2:
                        ret.sign = 1
                    return ret

        # At this point a, b, and c are guaranteed non-negative UNLESS
        # c is NULL, in which case a may be negative. */

        z = rbigint([ONEDIGIT], 1, 1)

        # python adaptation: moved macros REDUCE(X) and MULT(X, Y, result)
        # into helper function result = _help_mult(x, y, c)
        if size_b <= FIVEARY_CUTOFF:
            # Left-to-right binary exponentiation (HAC Algorithm 14.79)
            # http://www.cacr.math.uwaterloo.ca/hac/about/chap14.pdf
            size_b -= 1
            while size_b >= 0:
                bi = b.digit(size_b)
                j = 1 << (SHIFT-1)
                while j != 0:
                    z = _help_mult(z, z, c)
                    if bi & j:
                        z = _help_mult(z, a, c)
                    j >>= 1
                size_b -= 1

        else:
            # Left-to-right 5-ary exponentiation (HAC Algorithm 14.82)
            # This is only useful in the case where c != None.
            # z still holds 1L
            table = [z] * 32
            table[0] = z
            for i in range(1, 32):
                table[i] = _help_mult(table[i-1], a, c)

            # Note that here SHIFT is not a multiple of 5.  The difficulty
            # is to extract 5 bits at a time from 'b', starting from the
            # most significant digits, so that at the end of the algorithm
            # it falls exactly to zero.
            # m  = max number of bits = i * SHIFT
            # m+ = m rounded up to the next multiple of 5
            # j  = (m+) % SHIFT = (m+) - (i * SHIFT)
            # (computed without doing "i * SHIFT", which might overflow)
            j = size_b % 5
            j = _jmapping[j]
            if not we_are_translated():
                assert j == (size_b*SHIFT+4)//5*5 - size_b*SHIFT
            #
            accum = r_uint(0)
            while True:
                j -= 5
                if j >= 0:
                    index = (accum >> j) & 0x1f
                else:
                    # 'accum' does not have enough digit.
                    # must get the next digit from 'b' in order to complete
                    if size_b == 0:
                        break # Done

                    size_b -= 1
                    assert size_b >= 0
                    bi = b.udigit(size_b)
                    index = ((accum << (-j)) | (bi >> (j+SHIFT))) & 0x1f
                    accum = bi
                    j += SHIFT
                #
                for k in range(5):
                    z = _help_mult(z, z, c)
                if index:
                    z = _help_mult(z, table[index], c)
            #
            assert j == -5

        if negativeOutput and z.sign != 0:
            z = z.sub(c)
        return z

    @jit.elidable
    def neg(self):
        return rbigint(self._digits, -self.sign, self.size)

    @jit.elidable
    def abs(self):
        if self.sign != -1:
            return self
        return rbigint(self._digits, 1, self.size)

    @jit.elidable
    def invert(self): #Implement ~x as -(x + 1)
        if self.sign == 0:
            return ONENEGATIVERBIGINT

        ret = self.int_add(1)
        ret.sign = -ret.sign
        return ret

    @jit.elidable
    def lshift(self, int_other):
        if int_other < 0:
            raise ValueError("negative shift count")
        elif int_other == 0:
            return self

        # wordshift, remshift = divmod(int_other, SHIFT)
        wordshift = int_other // SHIFT
        remshift = int_other - wordshift * SHIFT

        if not remshift:
            # So we can avoid problems with eq, AND avoid the need for normalize.
            if self.sign == 0:
                return self
            return rbigint([NULLDIGIT] * wordshift + self._digits, self.sign, self.size + wordshift)

        oldsize = self.numdigits()
        newsize = oldsize + wordshift + 1
        z = rbigint([NULLDIGIT] * newsize, self.sign, newsize)
        accum = _widen_digit(0)
        j = 0
        while j < oldsize:
            accum += self.widedigit(j) << remshift
            z.setdigit(wordshift, accum)
            accum >>= SHIFT
            wordshift += 1
            j += 1

        newsize -= 1
        assert newsize >= 0
        z.setdigit(newsize, accum)

        z._normalize()
        return z
    lshift._always_inline_ = True # It's so fast that it's always benefitial.

    @jit.elidable
    def lqshift(self, int_other):
        " A quicker one with much less checks, int_other is valid and for the most part constant."
        assert int_other > 0

        oldsize = self.numdigits()

        z = rbigint([NULLDIGIT] * (oldsize + 1), self.sign, (oldsize + 1))
        accum = _widen_digit(0)
        i = 0
        while i < oldsize:
            accum += self.widedigit(i) << int_other
            z.setdigit(i, accum)
            accum >>= SHIFT
            i += 1
        z.setdigit(oldsize, accum)
        z._normalize()
        return z
    lqshift._always_inline_ = True # It's so fast that it's always benefitial.

    @jit.elidable
    def rshift(self, int_other, dont_invert=False):
        if int_other < 0:
            raise ValueError("negative shift count")
        elif int_other == 0:
            return self
        if self.sign == -1 and not dont_invert:
            a = self.invert().rshift(int_other)
            return a.invert()

        wordshift = int_other / SHIFT
        newsize = self.numdigits() - wordshift
        if newsize <= 0:
            return NULLRBIGINT

        loshift = int_other % SHIFT
        hishift = SHIFT - loshift
        z = rbigint([NULLDIGIT] * newsize, self.sign, newsize)
        i = 0
        while i < newsize:
            newdigit = (self.digit(wordshift) >> loshift)
            if i+1 < newsize:
                newdigit |= (self.digit(wordshift+1) << hishift)
            z.setdigit(i, newdigit)
            i += 1
            wordshift += 1
        z._normalize()
        return z
    rshift._always_inline_ = 'try' # It's so fast that it's always benefitial.

    @jit.elidable
    def abs_rshift_and_mask(self, bigshiftcount, mask):
        assert isinstance(bigshiftcount, r_ulonglong)
        assert mask >= 0
        wordshift = bigshiftcount / SHIFT
        numdigits = self.numdigits()
        if wordshift >= numdigits:
            return 0
        wordshift = intmask(wordshift)
        loshift = intmask(intmask(bigshiftcount) - intmask(wordshift * SHIFT))
        lastdigit = self.digit(wordshift) >> loshift
        if mask > (MASK >> loshift) and wordshift + 1 < numdigits:
            hishift = SHIFT - loshift
            lastdigit |= self.digit(wordshift+1) << hishift
        return lastdigit & mask

    @staticmethod
    def from_list_n_bits(list, nbits):
        if len(list) == 0:
            return NULLRBIGINT

        if nbits == SHIFT:
            z = rbigint(list, 1)
        else:
            if not (1 <= nbits < SHIFT):
                raise ValueError

            lllength = (r_ulonglong(len(list)) * nbits) // SHIFT
            length = intmask(lllength) + 1
            z = rbigint([NULLDIGIT] * length, 1)

            out = 0
            i = 0
            accum = 0
            for input in list:
                accum |= (input << i)
                original_i = i
                i += nbits
                if i > SHIFT:
                    z.setdigit(out, accum)
                    out += 1
                    accum = input >> (SHIFT - original_i)
                    i -= SHIFT
            assert out < length
            z.setdigit(out, accum)

        z._normalize()
        return z

    @jit.elidable
    def and_(self, other):
        return _bitwise(self, '&', other)

    @jit.elidable
    def int_and_(self, other):
        return _int_bitwise(self, '&', other)

    @jit.elidable
    def xor(self, other):
        return _bitwise(self, '^', other)

    @jit.elidable
    def int_xor(self, other):
        return _int_bitwise(self, '^', other)

    @jit.elidable
    def or_(self, other):
        return _bitwise(self, '|', other)

    @jit.elidable
    def int_or_(self, other):
        return _int_bitwise(self, '|', other)

    @jit.elidable
    def oct(self):
        if self.sign == 0:
            return '0L'
        else:
            return _format(self, BASE8, '0', 'L')

    @jit.elidable
    def hex(self):
        return _format(self, BASE16, '0x', 'L')

    @jit.elidable
    def log(self, base):
        # base is supposed to be positive or 0.0, which means we use e
        if base == 10.0:
            return _loghelper(math.log10, self)
        if base == 2.0:
            from rpython.rlib import rfloat
            return _loghelper(rfloat.log2, self)
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
        i = self.numdigits()

        while i > 1 and self._digits[i - 1] == NULLDIGIT:
            i -= 1
        assert i > 0

        if i != self.numdigits():
            self.size = i
        if self.numdigits() == 1 and self._digits[0] == NULLDIGIT:
            self.sign = 0
            self._digits = [NULLDIGIT]

    _normalize._always_inline_ = True

    @jit.elidable
    def bit_length(self):
        i = self.numdigits()
        if i == 1 and self._digits[0] == NULLDIGIT:
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
        return "<rbigint digits=%s, sign=%s, size=%d, len=%d, %s>" % (self._digits,
                                            self.sign, self.size, len(self._digits),
                                            self.str())

ONERBIGINT = rbigint([ONEDIGIT], 1, 1)
ONENEGATIVERBIGINT = rbigint([ONEDIGIT], -1, 1)
NULLRBIGINT = rbigint()

_jmapping = [(5 * SHIFT) % 5,
             (4 * SHIFT) % 5,
             (3 * SHIFT) % 5,
             (2 * SHIFT) % 5,
             (1 * SHIFT) % 5]


# if the bigint has more digits than this, it cannot fit into an int
MAX_DIGITS_THAT_CAN_FIT_IN_INT = rbigint.fromint(-sys.maxint - 1).numdigits()


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
        res = res.mod(c)

    return res

@specialize.argtype(0)
def digits_from_nonneg_long(l):
    digits = []
    while True:
        digits.append(_store_digit(_mask_digit(l & MASK)))
        l = l >> SHIFT
        if not l:
            return digits[:] # to make it non-resizable

@specialize.argtype(0)
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

@specialize.argtype(0)
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

@specialize.argtype(0)
def args_from_rarith_int(x):
    return args_from_rarith_int1(widen(x))
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
    z = rbigint([NULLDIGIT] * (size_a + 1), 1)
    i = UDIGIT_TYPE(0)
    carry = UDIGIT_TYPE(0)
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

def _x_int_add(a, b):
    """ Add the absolute values of one bigint and one integer. """
    size_a = a.numdigits()

    z = rbigint([NULLDIGIT] * (size_a + 1), 1)
    i = UDIGIT_TYPE(1)
    carry = a.udigit(0) + abs(b)
    z.setdigit(0, carry)
    carry >>= SHIFT

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
            return NULLRBIGINT
        if a.digit(i) < b.digit(i):
            sign = -1
            a, b = b, a
        size_a = size_b = i+1

    z = rbigint([NULLDIGIT] * size_a, sign, size_a)
    borrow = UDIGIT_TYPE(0)
    i = _load_unsigned_digit(0)
    while i < size_b:
        # The following assumes unsigned arithmetic
        # works modulo 2**N for some N>SHIFT.
        borrow = a.udigit(i) - b.udigit(i) - borrow
        z.setdigit(i, borrow)
        borrow >>= SHIFT
        #borrow &= 1 # Keep only one sign bit
        i += 1
    while i < size_a:
        borrow = a.udigit(i) - borrow
        z.setdigit(i, borrow)
        borrow >>= SHIFT
        #borrow &= 1
        i += 1

    assert borrow == 0
    z._normalize()
    return z

def _x_int_sub(a, b):
    """ Subtract the absolute values of two integers. """

    size_a = a.numdigits()

    bdigit = abs(b)

    if size_a == 1:
        # Find highest digit where a and b differ:
        adigit = a.digit(0)

        if adigit == bdigit:
            return NULLRBIGINT
    
        return rbigint.fromint(adigit - bdigit)

    z = rbigint([NULLDIGIT] * size_a, 1, size_a)
    i = _load_unsigned_digit(1)
    # The following assumes unsigned arithmetic
    # works modulo 2**N for some N>SHIFT.
    borrow = a.udigit(0) - bdigit
    z.setdigit(0, borrow)
    borrow >>= SHIFT
    #borrow &= 1 # Keep only one sign bit

    while i < size_a:
        borrow = a.udigit(i) - borrow
        z.setdigit(i, borrow)
        borrow >>= SHIFT
        #borrow &= 1
        i += 1

    assert borrow == 0
    z._normalize()
    return z

# A neat little table of power of twos.
ptwotable = {}
for x in range(SHIFT-1):
    ptwotable[r_longlong(2 << x)] = x+1
    ptwotable[r_longlong(-2 << x)] = x+1

def _x_mul(a, b, digit=0):
    """
    Grade school multiplication, ignoring the signs.
    Returns the absolute value of the product, or None if error.
    """

    size_a = a.numdigits()
    size_b = b.numdigits()

    if a is b:
        # Efficient squaring per HAC, Algorithm 14.16:
        # http://www.cacr.math.uwaterloo.ca/hac/about/chap14.pdf
        # Gives slightly less than a 2x speedup when a == b,
        # via exploiting that each entry in the multiplication
        # pyramid appears twice (except for the size_a squares).
        z = rbigint([NULLDIGIT] * (size_a + size_b), 1)
        i = UDIGIT_TYPE(0)
        while i < size_a:
            f = a.widedigit(i)
            pz = i << 1
            pa = i + 1

            carry = z.widedigit(pz) + f * f
            z.setdigit(pz, carry)
            pz += 1
            carry >>= SHIFT
            assert carry <= MASK

            # Now f is added in twice in each column of the
            # pyramid it appears.  Same as adding f<<1 once.
            f <<= 1
            while pa < size_a:
                carry += z.widedigit(pz) + a.widedigit(pa) * f
                pa += 1
                z.setdigit(pz, carry)
                pz += 1
                carry >>= SHIFT
            if carry:
                carry += z.widedigit(pz)
                z.setdigit(pz, carry)
                pz += 1
                carry >>= SHIFT
            if carry:
                z.setdigit(pz, z.widedigit(pz) + carry)
            assert (carry >> SHIFT) == 0
            i += 1
        z._normalize()
        return z

    elif digit:
        if digit & (digit - 1) == 0:
            return b.lqshift(ptwotable[digit])

        # Even if it's not power of two it can still be useful.
        return _muladd1(b, digit)

    # a is not b
    # use the following identity to reduce the number of operations
    # a * b = a_0*b_0 + sum_{i=1}^n(a_0*b_i + a_1*b_{i-1}) + a_1*b_n
    z = rbigint([NULLDIGIT] * (size_a + size_b), 1)
    i = UDIGIT_TYPE(0)
    size_a1 = UDIGIT_TYPE(size_a - 1)
    size_b1 = UDIGIT_TYPE(size_b - 1)
    while i < size_a1:
        f0 = a.widedigit(i)
        f1 = a.widedigit(i + 1)
        pz = i
        carry = z.widedigit(pz) + b.widedigit(0) * f0
        z.setdigit(pz, carry)
        pz += 1
        carry >>= SHIFT
        j = UDIGIT_TYPE(0)
        while j < size_b1:
            # this operation does not overflow using 
            # SHIFT = (LONG_BIT // 2) - 1 = B - 1; in fact before it
            # carry and z.widedigit(pz) are less than 2**(B - 1);
            # b.widedigit(j + 1) * f0 < (2**(B-1) - 1)**2; so
            # carry + z.widedigit(pz) + b.widedigit(j + 1) * f0 +
            # b.widedigit(j) * f1 < 2**(2*B - 1) - 2**B < 2**LONG)BIT - 1
            carry += z.widedigit(pz) + b.widedigit(j + 1) * f0 + \
                     b.widedigit(j) * f1
            z.setdigit(pz, carry)
            pz += 1
            carry >>= SHIFT
            j += 1
        # carry < 2**(B + 1) - 2
        carry += z.widedigit(pz) + b.widedigit(size_b1) * f1
        z.setdigit(pz, carry)
        pz += 1
        carry >>= SHIFT
        # carry < 4
        if carry:
            z.setdigit(pz, carry)
        assert (carry >> SHIFT) == 0
        i += 2
    if size_a & 1:
        pz = size_a1
        f = a.widedigit(pz)
        pb = 0
        carry = _widen_digit(0)
        while pb < size_b:
            carry += z.widedigit(pz) + b.widedigit(pb) * f
            pb += 1
            z.setdigit(pz, carry)
            pz += 1
            carry >>= SHIFT
        if carry:
            z.setdigit(pz, z.widedigit(pz) + carry)
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

    # We use "or" her to avoid having a check where list can be empty in _normalize.
    lo = rbigint(n._digits[:size_lo] or [NULLDIGIT], 1)
    hi = rbigint(n._digits[size_lo:n.size] or [NULLDIGIT], 1)
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

    # Split a & b into hi & lo pieces.
    shift = bsize >> 1
    ah, al = _kmul_split(a, shift)
    if ah.sign == 0:
        # This may happen now that _k_lopsided_mul ain't catching it.
        return _x_mul(a, b)
    #assert ah.sign == 1    # the split isn't degenerate

    if a is b:
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
    t1 = ah.mul(bh)

    assert t1.sign >= 0
    assert 2*shift + t1.numdigits() <= ret.numdigits()
    for i in range(t1.numdigits()):
        ret._digits[2*shift + i] = t1._digits[i]

    # Zero-out the digits higher than the ah*bh copy. */
    ## ignored, assuming that we initialize to zero
    ##i = ret->ob_size - 2*shift - t1->ob_size;
    ##if (i)
    ##    memset(ret->ob_digit + 2*shift + t1->ob_size, 0,
    ##           i * sizeof(digit));

    # 3. t2 <- al*bl, and copy into the low digits.
    t2 = al.mul(bl)
    assert t2.sign >= 0
    assert t2.numdigits() <= 2*shift # no overlap with high digits
    for i in range(t2.numdigits()):
        ret._digits[i] = t2._digits[i]

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

    # 6. t3 <- (ah+al)(bh+bl), and add into result.
    t1 = _x_add(ah, al)

    if a is b:
        t2 = t1
    else:
        t2 = _x_add(bh, bl)

    t3 = t1.mul(t2)
    assert t3.sign >= 0

    # Add t3.  It's not obvious why we can't run out of room here.
    # See the (*) comment after this function.
    _v_iadd(ret, shift, i, t3, t3.numdigits())

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
    # Not in use anymore, only account for like 1% performance. Perhaps if we
    # Got rid of the extra list allocation this would be more effective.
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
    # XXX prevent one list from being created.
    bslice = rbigint(sign=1)

    nbdone = 0
    while bsize > 0:
        nbtouse = min(bsize, asize)

        # Multiply the next slice of b by a.

        #bslice.digits[:nbtouse] = b.digits[nbdone : nbdone + nbtouse]
        # XXX: this would be more efficient if we adopted CPython's
        # way to store the size, instead of resizing the list!
        # XXX change the implementation, encoding length via the sign.
        bslice._digits = b._digits[nbdone : nbdone + nbtouse]
        bslice.size = nbtouse
        product = _k_mul(a, bslice)

        # Add into result.
        _v_iadd(ret, nbdone, ret.numdigits() - nbdone,
                product, product.numdigits())

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
        rem = (rem << SHIFT) | pin.widedigit(size)
        hi = rem // n
        pout.setdigit(size, hi)
        rem -= hi * n
        size -= 1
    return rffi.cast(lltype.Signed, rem)

def _divrem1(a, n):
    """
    Divide a bigint integer by a digit, returning both the quotient
    and the remainder as a tuple.
    The sign of a is ignored; n should not be zero.
    """
    assert n > 0 and n <= MASK

    size = a.numdigits()
    z = rbigint([NULLDIGIT] * size, 1, size)
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
    carry = UDIGIT_TYPE(0)

    assert m >= n
    i = _load_unsigned_digit(xofs)
    iend = xofs + n
    while i < iend:
        carry += x.udigit(i) + y.udigit(i-xofs)
        x.setdigit(i, carry)
        carry >>= SHIFT
        i += 1
    iend = xofs + m
    while carry and i < iend:
        carry += x.udigit(i)
        x.setdigit(i, carry)
        carry >>= SHIFT
        i += 1
    return carry

def _v_isub(x, xofs, m, y, n):
    """
    x and y are rbigints, m >= n required.  x.digits[0:n] is modified in place,
    by substracting y.digits[0:m] to it. Borrows are propagated as
    far as x[m-1], and the remaining borrow (0 or 1) is returned.
    Python adaptation: x is addressed relative to xofs!
    """
    borrow = UDIGIT_TYPE(0)

    assert m >= n
    i = _load_unsigned_digit(xofs)
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

@specialize.argtype(2)
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

def _v_lshift(z, a, m, d):
    """ Shift digit vector a[0:m] d bits left, with 0 <= d < SHIFT. Put
        * result in z[0:m], and return the d bits shifted out of the top.
    """

    carry = 0
    assert 0 <= d and d < SHIFT
    i = 0
    while i < m:
        acc = a.widedigit(i) << d | carry
        z.setdigit(i, acc)
        carry = acc >> SHIFT
        i += 1

    return carry

def _v_rshift(z, a, m, d):
    """ Shift digit vector a[0:m] d bits right, with 0 <= d < PyLong_SHIFT. Put
        * result in z[0:m], and return the d bits shifted out of the bottom.
    """

    carry = _widen_digit(0)
    acc = _widen_digit(0)
    mask = (1 << d) - 1

    assert 0 <= d and d < SHIFT
    i = m-1
    while i >= 0:
        acc = (carry << SHIFT) | a.widedigit(i)
        carry = acc & mask
        z.setdigit(i, acc >> d)
        i -= 1

    return carry

def _x_divrem(v1, w1):
    """ Unsigned bigint division with remainder -- the algorithm """
    size_v = v1.numdigits()
    size_w = w1.numdigits()
    assert size_v >= size_w and size_w > 1

    v = rbigint([NULLDIGIT] * (size_v + 1), 1, size_v + 1)
    w = rbigint([NULLDIGIT] * size_w, 1, size_w)

    """ normalize: shift w1 left so that its top digit is >= PyLong_BASE/2.
        shift v1 left by the same amount. Results go into w and v. """

    d = SHIFT - bits_in_digit(w1.digit(abs(size_w-1)))
    carry = _v_lshift(w, w1, size_w, d)
    assert carry == 0
    carry = _v_lshift(v, v1, size_v, d)
    if carry != 0 or v.digit(abs(size_v-1)) >= w.digit(abs(size_w-1)):
        v.setdigit(size_v, carry)
        size_v += 1

    """ Now v->ob_digit[size_v-1] < w->ob_digit[size_w-1], so quotient has
        at most (and usually exactly) k = size_v - size_w digits. """
    k = size_v - size_w
    if k == 0:
        # We can't use v1, nor NULLRBIGINT here as some function modify the result.
        assert _v_rshift(w, v, size_w, d) == 0
        w._normalize()
        return rbigint([NULLDIGIT]), w

    assert k > 0
    a = rbigint([NULLDIGIT] * k, 1, k)

    wm1 = w.widedigit(abs(size_w-1))
    wm2 = w.widedigit(abs(size_w-2))

    j = size_v - 1
    k -= 1
    while k >= 0:
        assert j >= 0
        """ inner loop: divide vk[0:size_w+1] by w0[0:size_w], giving
            single-digit quotient q, remainder in vk[0:size_w]. """

        # estimate quotient digit q; may overestimate by 1 (rare)
        if j >= size_v:
            vtop = 0
        else:
            vtop = v.widedigit(j)
        assert vtop <= wm1
        vv = (vtop << SHIFT) | v.widedigit(abs(j-1))
        q = vv / wm1
        r = vv - wm1 * q
        while wm2 * q > ((r << SHIFT) | v.widedigit(abs(j-2))):
            q -= 1
            r += wm1

        #assert q <= MASK+1, We need to compare to BASE <=, but ehm, it gives a buildin long error. So we ignore this.

        # subtract q*w0[0:size_w] from vk[0:size_w+1]
        zhi = 0
        i = 0
        while i < size_w:
            z = v.widedigit(k+i) + zhi - q * w.widedigit(i)
            v.setdigit(k+i, z)
            zhi = z >> SHIFT
            i += 1

        # add w back if q was too large (this branch taken rarely)
        if vtop + zhi < 0:
            carry = UDIGIT_TYPE(0)
            i = 0
            while i < size_w:
                carry += v.udigit(k+i) + w.udigit(i)
                v.setdigit(k+i, carry)
                carry >>= SHIFT
                i += 1
            q -= 1

        # store quotient digit
        a.setdigit(k, q)
        k -= 1
        j -= 1

    carry = _v_rshift(w, v, size_w, d)
    assert carry == 0

    a._normalize()
    w._normalize()

    return a, w

def _divrem(a, b):
    """ Long division with remainder, top-level routine """
    size_a = a.numdigits()
    size_b = b.numdigits()

    if b.sign == 0:
        raise ZeroDivisionError("long division or modulo by zero")

    if (size_a < size_b or
        (size_a == size_b and
         a.digit(abs(size_a-1)) < b.digit(abs(size_b-1)))):
        # |a| < |b|
        return NULLRBIGINT, a# result is 0
    if size_b == 1:
        z, urem = _divrem1(a, b.digit(0))
        rem = rbigint([_store_digit(urem)], int(urem != 0), 1)
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
    from rpython.rlib import rfloat
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
    q = (q >> 2) + r_uint((bool(q & 2) and bool(q & 5)))

    if exp > DBL_MAX_EXP or (exp == DBL_MAX_EXP and
                             q == r_ulonglong(1) << DBL_MANT_DIG):
        raise OverflowError("integer too large to convert to float")

    ad = math.ldexp(float(q), exp - DBL_MANT_DIG)
    if sign < 0:
        ad = -ad
    return ad

@specialize.arg(0)
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

    from rpython.rlib import rfloat
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
            if a_size < 0:
                break
            da = da * BASE_AS_FLOAT + a.digit(a_size)

        b_size -= 1
        db = float(b.digit(b_size))
        while True:
            b_size -= 1
            if b_size < 0:
                break
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
    mask = r_uint(1 << (extra_bits - 1))
    low = x.udigit(0) | r_uint(inexact)
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

def _format_base2_notzero(a, digits, prefix='', suffix=''):
        base = len(digits)
        # JRH: special case for power-of-2 bases
        accum = 0
        accumbits = 0  # # of bits in accum
        basebits = 0
        i = base
        while i > 1:
            basebits += 1
            i >>= 1

        # Compute a rough upper bound for the length of the string
        size_a = a.numdigits()
        i = 5 + len(prefix) + len(suffix) + (size_a*SHIFT + basebits-1) // basebits
        result = [chr(0)] * i
        next_char_index = i
        j = len(suffix)
        while j > 0:
            next_char_index -= 1
            j -= 1
            result[next_char_index] = suffix[j]

        i = 0
        while i < size_a:
            accum |= a.widedigit(i) << accumbits
            accumbits += SHIFT
            assert accumbits >= basebits
            while 1:
                cdigit = intmask(accum & (base - 1))
                next_char_index -= 1
                assert next_char_index >= 0
                result[next_char_index] = digits[cdigit]
                accumbits -= basebits
                accum >>= basebits
                if i < size_a - 1:
                    if accumbits < basebits:
                        break
                else:
                    if accum <= 0:
                        break
            i += 1
        j = len(prefix)
        while j > 0:
            next_char_index -= 1
            j -= 1
            result[next_char_index] = prefix[j]

        if a.sign < 0:
            next_char_index -= 1
            result[next_char_index] = '-'

        assert next_char_index >= 0    # otherwise, buffer overflow (this is also a
                         # hint for the annotator for the slice below)
        return ''.join(result[next_char_index:])


class _PartsCache(object):
    def __init__(self):
        # 36 - 3, because bases 0, 1 make no sense
        # and 2 is handled differently
        self.parts_cache = [None] * 34
        self.mindigits = [0] * 34

        for i in range(34):
            base = i + 3
            mindigits = 1
            while base ** mindigits < sys.maxint:
                mindigits += 1
            mindigits -= 1
            self.mindigits[i] = mindigits

    def get_cached_parts(self, base):
        index = base - 3
        res = self.parts_cache[index]
        if res is None:
            rbase = rbigint.fromint(base)
            part = rbase.pow(rbigint.fromint(self.mindigits[index]))
            res = [part]
            self.parts_cache[base - 3] = res
        return res

    def get_mindigits(self, base):
        return self.mindigits[base - 3]

_parts_cache = _PartsCache()

def _format_int_general(val, digits):
    base = len(digits)
    out = []
    while val:
        out.append(digits[val % base])
        val //= base
    out.reverse()
    return "".join(out)

def _format_int10(val, digits):
    return str(val)

@specialize.arg(7)
def _format_recursive(x, i, output, pts, digits, size_prefix, mindigits, _format_int):
    # bottomed out with min_digit sized pieces
    # use str of ints
    if i < 0:
        # this checks whether any digit has been appended yet
        if output.getlength() == size_prefix:
            if x.sign != 0:
                s = _format_int(x.toint(), digits)
                output.append(s)
        else:
            s = _format_int(x.toint(), digits)
            output.append_multiple_char(digits[0], mindigits - len(s))
            output.append(s)
    else:
        top, bot = x.divmod(pts[i]) # split the number
        _format_recursive(top, i-1, output, pts, digits, size_prefix, mindigits, _format_int)
        _format_recursive(bot, i-1, output, pts, digits, size_prefix, mindigits, _format_int)

def _format(x, digits, prefix='', suffix=''):
    if x.sign == 0:
        return prefix + "0" + suffix
    base = len(digits)
    assert base >= 2 and base <= 36
    if (base & (base - 1)) == 0:
        return _format_base2_notzero(x, digits, prefix, suffix)
    negative = x.sign < 0
    if negative:
        x = x.neg()
    rbase = rbigint.fromint(base)
    two = rbigint.fromint(2)

    pts = _parts_cache.get_cached_parts(base)
    mindigits = _parts_cache.get_mindigits(base)
    stringsize = mindigits
    startindex = 0
    for startindex, part in enumerate(pts):
        if not part.lt(x):
            break
        stringsize *= 2 # XXX can this overflow on 32 bit?
    else:
        # not enough parts computed yet
        while pts[-1].lt(x):
            pts.append(pts[-1].pow(two))
            stringsize *= 2

        startindex = len(pts) - 1

    # remove first base**2**i greater than x
    startindex -= 1

    output = StringBuilder(stringsize)
    if negative:
        output.append('-')
    output.append(prefix)
    if digits == BASE10:
        _format_recursive(
            x, startindex, output, pts, digits, output.getlength(), mindigits,
            _format_int10)
    else:
        _format_recursive(
            x, startindex, output, pts, digits, output.getlength(), mindigits,
            _format_int_general)

    output.append(suffix)
    return output.build()


@specialize.arg(1)
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

    z = rbigint([NULLDIGIT] * size_z, 1, size_z)
    i = 0
    while i < size_z:
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
        i += 1

    z._normalize()
    if negz == 0:
        return z

    return z.invert()

@specialize.arg(1)
def _int_bitwise(a, op, b): # '&', '|', '^'
    """ Bitwise and/or/xor operations """

    if not int_in_valid_range(b):
        # Fallback to long.
        return _bitwise(a, op, rbigint.fromint(b))

    if a.sign < 0:
        a = a.invert()
        maska = MASK
    else:
        maska = 0
    if b < 0:
        b = ~b
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
    if op == '&':
        if maska:
            size_z = 1
        else:
            if maskb:
                size_z = size_a
            else:
                size_z = 1
    else:
        size_z = size_a

    z = rbigint([NULLDIGIT] * size_z, 1, size_z)
    i = 0
    while i < size_z:
        if i < size_a:
            diga = a.digit(i) ^ maska
        else:
            diga = maska
        if i == 0:
            digb = b ^ maskb
        else:
            digb = maskb

        if op == '&':
            z.setdigit(i, diga & digb)
        elif op == '|':
            z.setdigit(i, diga | digb)
        elif op == '^':
            z.setdigit(i, diga ^ digb)
        i += 1

    z._normalize()
    if negz == 0:
        return z

    return z.invert()

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
        x = (x << SHIFT) + r_ulonglong(v.widedigit(i))
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
    res = intmask(intmask(x) * sign)
    return res

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
    # helper for fromstr
    base = parser.base
    if (base & (base - 1)) == 0:
        return parse_string_from_binary_base(parser)
    a = rbigint()
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

def parse_string_from_binary_base(parser):
    # The point to this routine is that it takes time linear in the number of
    # string characters.
    from rpython.rlib.rstring import ParseStringError

    base = parser.base
    if   base ==  2: bits_per_char = 1
    elif base ==  4: bits_per_char = 2
    elif base ==  8: bits_per_char = 3
    elif base == 16: bits_per_char = 4
    elif base == 32: bits_per_char = 5
    else:
        raise AssertionError

    # n <- total number of bits needed, while moving 'parser' to the end
    n = 0
    while parser.next_digit() >= 0:
        n += 1

    # b <- number of Python digits needed, = ceiling(n/SHIFT). */
    try:
        b = ovfcheck(n * bits_per_char)
        b = ovfcheck(b + (SHIFT - 1))
    except OverflowError:
        raise ParseStringError("long string too large to convert")
    b = (b // SHIFT) or 1
    z = rbigint([NULLDIGIT] * b, sign=parser.sign)

    # Read string from right, and fill in long from left; i.e.,
    # from least to most significant in both.
    accum = _widen_digit(0)
    bits_in_accum = 0
    pdigit = 0
    for _ in range(n):
        k = parser.prev_digit()
        accum |= _widen_digit(k) << bits_in_accum
        bits_in_accum += bits_per_char
        if bits_in_accum >= SHIFT:
            z.setdigit(pdigit, accum)
            pdigit += 1
            assert pdigit <= b
            accum >>= SHIFT
            bits_in_accum -= SHIFT

    if bits_in_accum:
        z.setdigit(pdigit, accum)
    z._normalize()
    return z

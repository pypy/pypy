import sys, operator
from pypy.objspace.std.objspace import *
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.floatobject import W_FloatObject
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.rpython.rarithmetic import intmask, r_uint, LONG_MASK
from pypy.rpython.rarithmetic import LONG_BIT

import math

SHORT_BIT = int(LONG_BIT // 2)
SHORT_MASK = int((1 << SHORT_BIT) - 1)

SIGN_BIT = LONG_BIT-1
SIGN_MASK = r_uint(1) << SIGN_BIT
NONSIGN_MASK = ~SIGN_MASK

# XXX some operations below return one of their input arguments
#     without checking that it's really of type long (and not a subclass).

class W_LongObject(W_Object):
    """This is a reimplementation of longs using a list of r_uints."""
    #All functions that still rely on the underlying Python's longs are marked
    #with YYYYYY
    from pypy.objspace.std.longtype import long_typedef as typedef
    
    def __init__(w_self, space, digits, sign=0):
        W_Object.__init__(w_self, space)
        if isinstance(digits, long):  #YYYYYY
            digits, sign = args_from_long(digits)
        w_self.digits = digits
        w_self.sign = sign
        assert len(w_self.digits)

    def longval(self): #YYYYYY
        l = 0
        for d in self.digits[::-1]:
            l = l << LONG_BIT
            l += long(d)
        return l * self.sign

    def unwrap(w_self): #YYYYYY
        return w_self.longval()

    def _normalize(self):
        if len(self.digits) == 0:
            self.sign = 0
            self.digits = [r_uint(0)]
            return
        i = len(self.digits) - 1
        while i != 0 and self.digits[i] == 0:
            self.digits.pop(-1)
            i -= 1
        if len(self.digits) == 1 and self.digits[0] == 0:
            self.sign = 0

    def _getshort(self, index):
        a = self.digits[index // 2]
        if index % 2 == 0:
            return a & SHORT_MASK
        else:
            return a >> SHORT_BIT

    def _setshort(self, index, short):
        a = self.digits[index // 2]
        ##!!assert isinstance(short, r_uint)
        assert short & SHORT_MASK == short
        if index % 2 == 0:
            self.digits[index // 2] = ((a >> SHORT_BIT) << SHORT_BIT) + short
        else:
            self.digits[index // 2] = (a & SHORT_MASK) + (short << SHORT_BIT)




registerimplementation(W_LongObject)

# bool-to-long
def delegate_Bool2Long(w_bool):
    return W_LongObject(w_bool.space, [r_uint(w_bool.boolval)],
                        int(w_bool.boolval))

# int-to-long delegation
def delegate_Int2Long(w_intobj):
    if w_intobj.intval < 0:
        sign = -1
    elif w_intobj.intval > 0:
        sign = 1
    else:
        sign = 0
    digits = [r_uint(abs(w_intobj.intval))]
    return W_LongObject(w_intobj.space, digits, sign)

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
    elif w_intobj.intval > 0:
        sign = 1
    else:
        sign = 0
    return W_LongObject(space, [r_uint(abs(w_intobj.intval))], sign)

def int__Long(space, w_value):
    if len(w_value.digits) == 1:
        if w_value.digits[0] & SIGN_MASK == 0:
            return space.newint(int(w_value.digits[0]) * w_value.sign)
        elif w_value.sign == -1 and w_value.digits[0] & NONSIGN_MASK == 0:
            return space.newint(intmask(w_value.digits[0]))
    #subtypes of long are converted to long!
    return long__Long(space, w_value)

def float__Long(space, w_longobj):
    try:
        return space.newfloat(_AsDouble(w_longobj))
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("long int too large to convert to float"))

def long__Float(space, w_floatobj): #YYYYYY
    return W_LongObject(space, *args_from_long(long(w_floatobj.floatval)))

def int_w__Long(space, w_value):
    if len(w_value.digits) == 1:
        if  w_value.digits[0] & SIGN_MASK == 0:
            return int(w_value.digits[0]) * w_value.sign
        elif w_value.sign == -1 and w_value.digits[0] & NONSIGN_MASK == 0:
            return intmask(w_value.digits[0])
    raise OperationError(space.w_OverflowError,
                         space.wrap("long int too large to convert to int"))

def uint_w__Long(space, w_value):
    if w_value.sign == -1:
        raise OperationError(space.w_ValueError,
                             space.wrap("cannot convert negative integer to unsigned"))
    if len(w_value.digits) == 1:
        return w_value.digits[0]
    raise OperationError(space.w_OverflowError,
                         space.wrap("long int too large to convert to unsigned int"))    

def repr__Long(space, w_long): #YYYYYY
    return space.wrap(repr(w_long.longval()))

def str__Long(space, w_long): #YYYYYY
    return space.wrap(str(w_long.longval()))

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

def hash__Long(space,w_value): #YYYYYY
    ## %reimplement%
    # real Implementation should be taken from _Py_HashDouble in object.c
    return space.wrap(hash(w_value.longval()))

# coerce
def coerce__Long_Long(space, w_long1, w_long2):
    return space.newtuple([w_long1, w_long2])


def add__Long_Long(space, w_long1, w_long2):
    if w_long1.sign < 0:
        if w_long2.sign < 0:
            result = _x_add(w_long1, w_long2, space)
            if result.sign != 0:
                result.sign = -result.sign
        else:
            result = _x_sub(w_long2, w_long1, space)
    else:
        if w_long2.sign < 0:
            result = _x_sub(w_long1, w_long2, space)
        else:
            result = _x_add(w_long1, w_long2, space)
    result._normalize()
    return result

def sub__Long_Long(space, w_long1, w_long2):
    if w_long1.sign < 0:
        if w_long2.sign < 0:
            result = _x_sub(w_long1, w_long2, space)
        else:
            result = _x_add(w_long1, w_long2, space)
        result.sign = -result.sign
    else:
        if w_long2.sign < 0:
            result = _x_add(w_long1, w_long2, space)
        else:
            result = _x_sub(w_long1, w_long2, space)
    result._normalize()
    return result

def mul__Long_Long(space, w_long1, w_long2):
    result = _x_mul(w_long1, w_long2, space)
    result.sign = w_long1.sign * w_long2.sign
    return result

def truediv__Long_Long(space, w_long1, w_long2):
    div = _long_true_divide(space, w_long1, w_long2)
    return space.newfloat(div)

def floordiv__Long_Long(space, w_long1, w_long2):
    div, mod = _l_divmod(space, w_long1, w_long2)
    return div

def div__Long_Long(space, w_long1, w_long2):
    return floordiv__Long_Long(space, w_long1, w_long2)

def mod__Long_Long(space, w_long1, w_long2):
    div, mod = _l_divmod(space, w_long1, w_long2)
    return mod

def divmod__Long_Long(space, w_long1, w_long2):
    div, mod = _l_divmod(space, w_long1, w_long2)
    return space.newtuple([div, mod])

# helper for pow()  #YYYYYY: still needs longval if second argument is negative
def _impl_long_long_pow(space, lv, lw, lz=None):
    if lw.sign < 0:
        if lz is not None:
            raise OperationError(space.w_TypeError,
                             space.wrap("pow() 2nd argument "
                 "cannot be negative when 3rd argument specified"))
        return space.pow(space.newfloat(float(lv.longval())),
                         space.newfloat(float(lw.longval())),
                         space.w_None)
    if lz is not None:
        if lz.sign == 0:
            raise OperationError(space.w_ValueError,
                                    space.wrap("pow() 3rd argument cannot be 0"))
    result = W_LongObject(space, [r_uint(1)], 1)
    if lw.sign == 0:
        if lz is not None:
            result = mod__Long_Long(space, result, lz)
        return result
    if lz is not None:
        temp = mod__Long_Long(space, lv, lz)
    else:
        temp = lv
    i = 0
    #Treat the most significant digit specially to reduce multiplications
    while i < len(lw.digits) - 1:
        j = 0
        m = r_uint(1)
        di = lw.digits[i]
        while j < LONG_BIT:
            if di & m:
                result = mul__Long_Long(space, result, temp)
            temp = mul__Long_Long(space, temp, temp)
            if lz is not None:
                result = mod__Long_Long(space, result, lz)
                temp = mod__Long_Long(space, temp, lz)
            m = m << 1
            j += 1
        i += 1
    m = r_uint(1) << (LONG_BIT - 1)
    highest_set_bit = LONG_BIT
    j = LONG_BIT - 1
    di = lw.digits[i]
    while j >= 0:
        if di & m:
            highest_set_bit = j
            break
        m = m >> 1
        j -= 1
    assert highest_set_bit != LONG_BIT, "long not normalized"
    j = 0
    m = r_uint(1)
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
    w_lpp = add__Long_Long(space, w_long, W_LongObject(space, [r_uint(1)], 1))
    return neg__Long(space, w_lpp)

def lshift__Long_Long(space, w_long1, w_long2):
    if w_long2.sign < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("negative shift count"))
    elif w_long2.sign == 0:
        return w_long1
    try:
        b = int_w__Long(space, w_long2)
    except OverflowError:   # b too big
        raise OperationError(space.w_OverflowError,
                             space.wrap("shift count too large"))
    wordshift = b // LONG_BIT
    remshift = r_uint(b) % LONG_BIT
    oldsize = len(w_long1.digits)
    newsize = oldsize + wordshift
    if remshift != 0:
        newsize += 1
    w_result = W_LongObject(space, [r_uint(0)] * newsize, w_long1.sign)
    rightshift = LONG_BIT - remshift
    LOWER_MASK = (r_uint(1) << r_uint(rightshift)) - 1
    UPPER_MASK = ~LOWER_MASK
    accum = r_uint(0)
    i = wordshift
    j = 0
    while j < oldsize:
        digit = w_long1.digits[j]
        w_result.digits[i] = (accum | (digit << remshift))
        accum = (digit & UPPER_MASK) >> rightshift
        i += 1
        j += 1
    if remshift:
        w_result.digits[i] = accum
    else:
        assert not accum
    w_result._normalize()
    return w_result

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
        b = int_w__Long(space, w_long2)
    except OverflowError:   # b too big # XXX maybe just return 0L instead?
        raise OperationError(space.w_OverflowError,
                             space.wrap("shift count too large"))
    wordshift = b // LONG_BIT
    remshift = r_uint(b) % LONG_BIT
    oldsize = len(w_long1.digits)
    newsize = oldsize - wordshift
    if newsize <= 0:
        return W_LongObject(space, [r_uint(0)], 0)
    w_result = W_LongObject(space, [r_uint(0)] * newsize, 1)
    leftshift = LONG_BIT - remshift
    LOWER_MASK = (r_uint(1) << r_uint(remshift)) - 1
    UPPER_MASK = ~LOWER_MASK
    accum = r_uint(0)
    i = newsize - 1
    j = oldsize - 1
    while i >= 0:
        digit = w_long1.digits[j]
        w_result.digits[i] = (accum | (digit >> remshift))
        accum = (digit & LOWER_MASK) << leftshift
        i -= 1
        j -= 1
    w_result._normalize()
    return w_result

def and__Long_Long(space, w_long1, w_long2): #YYYYYY
    a = w_long1.longval()
    b = w_long2.longval()
    res = a & b
    return W_LongObject(space, *args_from_long(res))

def xor__Long_Long(space, w_long1, w_long2): #YYYYYY
    a = w_long1.longval()
    b = w_long2.longval()
    res = a ^ b
    return W_LongObject(space, *args_from_long(res))

def or__Long_Long(space, w_long1, w_long2): #YYYYYY
    a = w_long1.longval()
    b = w_long2.longval()
    res = a | b
    return W_LongObject(space, *args_from_long(res))

def oct__Long(space, w_long1): #YYYYYY
    x = w_long1.longval()
    return space.wrap(oct(x))

def hex__Long(space, w_long1): #YYYYYY
    x = w_long1.longval()
    return space.wrap(hex(x))

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


#Helper Functions
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
        digits.append(r_uint(l & LONG_MASK))
        l = l >> LONG_BIT
    if sign == 0:
        digits = [r_uint(0)]
    return digits, sign


#Add the absolute values of two longs
def _x_add(a, b, space):
    size_a = len(a.digits)
    size_b = len(b.digits)
    if size_a < size_b:
        a, b = b, a
        size_a, size_b = size_b, size_a
    z = W_LongObject(space, [r_uint(0)] * (len(a.digits) + 1), 1)
    i = 0
    carry = r_uint(0)
    while i < size_b:
        ad = a.digits[i]
        s = ad + b.digits[i]
        res = s + carry
        carry = r_uint(res < s) + r_uint(s < ad)
        z.digits[i] = res
        i += 1
    while i < size_a:
        s = a.digits[i]
        carry = s + carry
        z.digits[i] = carry
        carry = r_uint(s > carry)
        i += 1
    z.digits[i] = carry
    return z


# Substract the absolute values of two longs
def _x_sub(a, b, space):
    size_a = len(a.digits)
    size_b = len(b.digits)
    sign = 1
    i = 0
    if size_a < size_b:
        sign = -1
        a, b = b, a
        size_a, size_b = size_b, size_a
    elif size_a == size_b:
        i = size_a - 1;
        while i > 0 and a.digits[i] == b.digits[i]:
            i -= 1
        if (i == -1):
            return W_LongObject(space, [r_uint(0)])
        if a.digits[i] < b.digits[i]:
            sign = -1
            a, b = b, a
        size_a = size_b = i + 1
    z = W_LongObject(space, [r_uint(0)] * len(a.digits), 1)
    i = 0
    borrow = r_uint(0)
    while i < size_b:
        ad = a.digits[i]
        s = ad - b.digits[i]
        res = s - borrow
        z.digits[i] = res
        borrow = r_uint(res > s) + r_uint(s > ad)
        i += 1
    while i < size_a:
        ad = a.digits[i]
        res = ad - borrow
        borrow = r_uint(res > ad)
        z.digits[i] = res
        i += 1
    assert borrow == 0
    z.sign = sign
    return z


#Multiply the absolute values of two longs
def _x_mul(a, b, space):
    size_a = len(a.digits) * 2
    size_b = len(b.digits) * 2
    z = W_LongObject(space, [r_uint(0)] * ((size_a + size_b) // 2), 1)
    i = 0
    while i < size_a:
        carry = r_uint(0)
        f = a._getshort(i)
        j = 0
        while j < size_b:
            carry += z._getshort(i + j) + b._getshort(j) * f
            z._setshort(i + j, carry & SHORT_MASK)
            carry = carry >> SHORT_BIT
            j += 1
        while carry != 0:
            assert i + j < size_a + size_b
            carry += z._getshort(i + j)
            z._setshort(i + j, carry & SHORT_MASK)
            carry = carry >> SHORT_BIT
            j += 1
        i += 1
    z._normalize()
    return z

def _inplace_divrem1(pout, pin, n):
    """
    Divide long pin by non-zero digit n, storing quotient
    in pout, and returning the remainder. It's OK for pin == pout on entry.
    """
    rem = r_uint(0)
    assert n > 0 and n <= SHORT_MASK
    size = len(pin.digits) * 2 - 1
    while size >= 0:
        rem = (rem << SHORT_BIT) + pin._getshort(size)
        hi = rem // n
        pout._setshort(size, hi)
        rem -= hi * n
        size -= 1
    return rem

def _divrem1(space, a, n):
    """
    Divide a long integer by a digit, returning both the quotient
    and the remainder as a tuple.
    The sign of a is ignored; n should not be zero.
    """
    assert n > 0 and n <= SHORT_MASK
    size = len(a.digits)
    z = W_LongObject(space, [r_uint(0)] * size, 1)
    rem = _inplace_divrem1(z, a, n)
    z._normalize()
    return z, rem

def _muladd1(space, a, n, extra):
    """Multiply by a single digit and add a single digit, ignoring the sign.
    """
    digitpairs = len(a.digits)
    size_a = digitpairs * 2
    if a._getshort(size_a-1) == 0:
        size_a -= 1
    z = W_LongObject(space, [r_uint(0)] * (digitpairs+1), 1)
    carry = extra
    for i in range(size_a):
        carry += a._getshort(i) * n
        z._setshort(i, carry & SHORT_MASK)
        carry >>= SHORT_BIT
    i += 1
    z._setshort(i, carry)
    z._normalize()
    return z

# for the carry in _x_divrem, we need something that can hold
# two digits plus a sign.
# for the time being, we here implement such a 33 bit number just
# for the purpose of the division.
# In the long term, it might be considered to implement the
# notation of a "double anything" unsigned type, which could
# be used recursively to implement longs of any size.

class r_suint(object):
    # we do not inherit from r_uint, because we only
    # support a few operations for our purpose
    def __init__(self, value=0):
        if isinstance(value, r_suint):
            self.value = value.value
            self.sign = value.sign
        else:
            self.value = r_uint(value)
            self.sign = -(value < 0)

    def longval(self):
        if self.sign:
            return -long(-self.value)
        else:
            return long(self.value)
        
    def __repr__(self):
        return repr(self.longval())

    def __str__(self):
        return str(self.longval())

    def __iadd__(self, other):
        hold = self.value
        self.value += other
        self.sign ^= - ( (other < 0) != (self.value < hold) )
        return self

    def __add__(self, other):
        res = r_suint(self)
        res += other
        return res

    def __isub__(self, other):
        hold = self.value
        self.value -= other
        self.sign ^= - ( (other < 0) != (self.value > hold) )
        return self

    def __sub__(self, other):
        res = r_suint(self)
        res -= other
        return res

    def __irshift__(self, n):
        self.value >>= n
        if self.sign:
            self.value += LONG_MASK << (LONG_BIT - n)
        return self

    def __rshift__(self, n):
        res = r_suint(self)
        res >>= n
        return res

    def __ilshift__(self, n):
        self.value <<= n
        return self

    def __lshift__(self, n):
        res = r_suint(self)
        res <<= n
        return res

    def __and__(self, mask):
        # only used to get bits from the value
        return self.value & mask

    def __eq__(self, other):
        if not isinstance(other,r_suint):
            other = r_suint(other)
        return self.sign == other.sign and self.value == other.value

def _x_divrem(space, v1, w1):
    size_w = len(w1.digits) * 2
    # hack for the moment:
    # find where w1 is really nonzero
    if w1._getshort(size_w-1) == 0:
        size_w -= 1
    d = (SHORT_MASK+1) // (w1._getshort(size_w-1) + 1)
    v = _muladd1(space, v1, d, r_uint(0))
    w = _muladd1(space, w1, d, r_uint(0))
    size_v = len(v.digits) * 2
    if v._getshort(size_v-1) == 0:
        size_v -= 1
    size_w = len(w.digits) * 2
    if w._getshort(size_w-1) == 0:
        size_w -= 1
    assert size_v >= size_w and size_w > 1 # Assert checks by div()

    size_a = size_v - size_w + 1
    digitpairs = (size_a + 1) // 2
    a = W_LongObject(space, [r_uint(0)] * digitpairs, 1)

    j = size_v
    k = size_a - 1
    while k >= 0:
        if j >= size_v:
            vj = r_uint(0)
        else:
            vj = v._getshort(j)
        carry = r_suint(0) # note: this must hold two digits and sign!

        if vj == w._getshort(size_w-1):
            q = r_uint(SHORT_MASK)
        else:
            q = ((vj << SHORT_BIT) + v._getshort(j-1)) // w._getshort(size_w-1)

        # notabene!
        # this check needs a signed two digits result
        # or we get an overflow.
        while (w._getshort(size_w-2) * q >
                ((
                    r_suint(vj << SHORT_BIT) # this one dominates
                    + v._getshort(j-1)
                    - q * w._getshort(size_w-1)
                                ) << SHORT_BIT)
                + v._getshort(j-2)):
            q -= 1

        i = 0
        while i < size_w and i+k < size_v:
            z = w._getshort(i) * q
            zz = z >> SHORT_BIT
            carry += v._getshort(i+k) + (zz << SHORT_BIT)
            carry -= z
            v._setshort(i+k, r_uint(carry.value & SHORT_MASK))
            carry >>= SHORT_BIT
            carry -= zz
            i += 1

        if i+k < size_v:
            carry += v._getshort(i+k)
            v._setshort(i+k, r_uint(0))

        if carry == 0:
            a._setshort(k, q)
        else:
            assert carry == -1
            a._setshort(k, q-1)

            carry = r_suint(0)
            i = 0
            while i < size_w and i+k < size_v:
                carry += v._getshort(i+k) + w._getshort(i)
                v._setshort(i+k, r_uint(carry.value) & SHORT_MASK)
                carry >>= SHORT_BIT
                i += 1
        j -= 1
        k -= 1

    a._normalize()
    rem, _ = _divrem1(space, v, d)
    return a, rem


def _divrem(space, a, b):
    """ Long division with remainder, top-level routine """
    size_a = len(a.digits) * 2
    size_b = len(b.digits) * 2
    if a._getshort(size_a-1) == 0:
        size_a -= 1
    if b._getshort(size_b-1) == 0:
        size_b -= 1

    if b.sign == 0:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("long division or modulo by zero"))

    if (size_a < size_b or
        (size_a == size_b and
         a._getshort(size_a-1) < b._getshort(size_b-1))):
        # |a| < |b|
        z = W_LongObject(space, [r_uint(0)], 0)
        rem = a
        return z, rem
    if size_b == 1:
        z, urem = _divrem1(space, a, b._getshort(0))
        rem = W_LongObject(space, [urem], int(urem != 0))
    else:
        z, rem = _x_divrem(space, a, b)
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
    multiplier = float(1 << SHORT_BIT)
    if v.sign == 0:
        return 0.0, 0
    i = len(v.digits) * 2 - 1
    if v._getshort(i) == 0:
        i -= 1
    sign = v.sign
    x = float(v._getshort(i))
    nbitsneeded = NBITS_WANTED - 1
    # Invariant:  i Python digits remain unaccounted for.
    while i > 0 and nbitsneeded > 0:
        i -= 1
        x = x * multiplier + float(v._getshort(i))
        nbitsneeded -= SHORT_BIT
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
##    multiplier = float(r_uint(1) << lb1)
##    while exp >= lb1:
##        x *= multiplier
##        exp -= lb1
##    if exp:
##        x *= float(r_uint(1) << exp)
##    return x

# note that math.ldexp checks for overflows,
# while the C ldexp is not guaranteed to.

def _AsDouble(v):
    """ Get a C double from a long int object. """
    x, e = _AsScaledDouble(v)
    if e <= sys.maxint / SHORT_BIT:
        x = math.ldexp(x, e * SHORT_BIT)
        #if not isinf(x):
        # this is checked by math.ldexp
        return x
    raise OverflowError# sorry, "long int too large to convert to float"

def _long_true_divide(space, a, b):
    try:
        ad, aexp = _AsScaledDouble(a)
        bd, bexp = _AsScaledDouble(b)
        if bd == 0.0:
            raise OperationError(space.w_ZeroDivisionError,
                                 space.wrap("long division or modulo by zero"))

        # True value is very close to ad/bd * 2**(SHIFT*(aexp-bexp))
        ad /= bd   # overflow/underflow impossible here
        aexp -= bexp
        if aexp > sys.maxint / SHORT_BIT:
            raise OverflowError
        elif aexp < -(sys.maxint / SHORT_BIT):
            return 0.0 # underflow to 0
        ad = math.ldexp(ad, aexp * SHORT_BIT)
        #if isinf(ad):   # ignore underflow to 0.0
        #    raise OverflowError
        # math.ldexp checks and raises
        return ad
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("long/long too large for a float"))


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
        return W_LongObject(space, [r_uint(0)], 0)
    ndig = (expo-1) // SHORT_BIT + 1 # Number of 'digits' in result
    digitpairs = (ndig + 1) // 2
    v = W_LongObject(space, [r_uint(0)] * digitpairs, 1)
    frac = math.ldexp(frac, (expo-1) % SHORT_BIT + 1)
    for i in range(ndig-1, -1, -1):
        bits = int(frac)
        v._setshort(i, r_uint(bits))
        frac -= float(bits)
        frac = math.ldexp(frac, SHORT_BIT)
    if neg:
        v.sign = -1
    return v

def _l_divmod(space, v, w):
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
    div, mod = _divrem(space, v, w)
    if mod.sign * w.sign == -1:
        mod = add__Long_Long(space, mod, w)
        one = W_LongObject(space, [r_uint(1)], 1)
        div = sub__Long_Long(space, div, one)
    return div, mod

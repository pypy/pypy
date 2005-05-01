import sys, operator
from pypy.objspace.std.objspace import *
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.floatobject import W_FloatObject
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.tool.rarithmetic import intmask, r_uint, LONG_MASK
from pypy.tool.rarithmetic import LONG_BIT

import math

SHORT_BIT = int(LONG_BIT // 2)
SHORT_MASK = int(LONG_MASK >> SHORT_BIT)

SIGN_BIT = LONG_BIT-1
SIGN_MASK = r_uint(1) << SIGN_BIT
NONSIGN_MASK = ~SIGN_MASK

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
        assert isinstance(short, r_uint)
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
def delegate_Long2Float(w_longobj): #YYYYYY
    try:
        return W_FloatObject(w_longobj.space, float(w_longobj.longval()))
    except OverflowError:
        raise OperationError(w_longobj.space.w_OverflowError,
                             w_longobj.space.wrap("long int too large to convert to float"))


# long__Long is supposed to do nothing, unless it has
# a derived long object, where it should return
# an exact one.
def long__Long(space, w_long1):
    if space.is_true(space.is_(space.type(w_long1), space.w_long)):
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

def float__Long(space, w_longobj): #YYYYYY
    try:
        return space.newfloat(float(w_longobj.longval()))
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

def truediv__Long_Long(space, w_long1, w_long2): #YYYYYY
    x = w_long1.longval()
    y = w_long2.longval()
    if not y:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("long division"))
    try:
        z = operator.truediv(x, y)
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("long/long too large for a float"))
    return space.newfloat(float(z))

def floordiv__Long_Long(space, w_long1, w_long2): #YYYYYY
    x = w_long1.longval()
    y = w_long2.longval()
    if not y:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("long division"))
    z = x // y
    return W_LongObject(space, *args_from_long(z))

div__Long_Long = floordiv__Long_Long #YYYYYY


def mod__Long_Long(space, w_long1, w_long2): #YYYYYY
    x = w_long1.longval()
    y = w_long2.longval()
    if not y:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("long modulo"))
    z = x % y
    return W_LongObject(space, *args_from_long(z))

def divmod__Long_Long(space, w_long1, w_long2): #YYYYYY
    x = w_long1.longval()
    y = w_long2.longval()
    if not y:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("long modulo"))
    z1, z2 = divmod(x, y)
    w_result1 = W_LongObject(space, *args_from_long(z1))
    w_result2 = W_LongObject(space, *args_from_long(z2))
    return space.newtuple([w_result1, w_result2])

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

def rshift__Long_Long(space, w_long1, w_long2): #YYYYYY
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
    while j >= 0:
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


#Substract the absolute values of two longs
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
    rem = r_uint(0, space)
    assert n > 0 and n <= SHORT_MASK
    size = len(pin.digits) * 2 - 1
    while size >= 0:
        rem = (rem << SHORT_BIT) + pin._getshort(size)

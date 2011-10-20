"""
Implementation of 'small' longs, stored as a r_longlong.
Useful for 32-bit applications manipulating values a bit larger than
fits in an 'int'.
"""
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.multimethod import FailedToImplementArgs
from pypy.rlib.rarithmetic import r_longlong, r_int, r_uint
from pypy.rlib.rarithmetic import intmask, LONGLONG_BIT
from pypy.rlib.rbigint import rbigint
from pypy.objspace.std.longobject import W_LongObject
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.interpreter.error import OperationError

LONGLONG_MIN = r_longlong((-1) << (LONGLONG_BIT-1))


class W_SmallLongObject(W_Object):
    from pypy.objspace.std.longtype import long_typedef as typedef
    _immutable_fields_ = ['longlong']

    def __init__(w_self, value):
        assert isinstance(value, r_longlong)
        w_self.longlong = value

    @staticmethod
    def fromint(value):
        return W_SmallLongObject(r_longlong(value))

    @staticmethod
    def frombigint(bigint):
        return W_SmallLongObject(bigint.tolonglong())

    def asbigint(w_self):
        return rbigint.fromrarith_int(w_self.longlong)

    def __repr__(w_self):
        return '<W_SmallLongObject(%d)>' % w_self.longlong

    def int_w(w_self, space):
        a = w_self.longlong
        b = intmask(a)
        if b == a:
            return b
        else:
            raise OperationError(space.w_OverflowError, space.wrap(
                "long int too large to convert to int"))

    def uint_w(w_self, space):
        a = w_self.longlong
        if a < 0:
            raise OperationError(space.w_ValueError, space.wrap(
                "cannot convert negative integer to unsigned int"))
        b = r_uint(a)
        if r_longlong(b) == a:
            return b
        else:
            raise OperationError(space.w_OverflowError, space.wrap(
                "long int too large to convert to unsigned int"))

    def bigint_w(w_self, space):
        return w_self.asbigint()

registerimplementation(W_SmallLongObject)

# ____________________________________________________________

def llong_mul_ovf(a, b):
    # xxx duplication of the logic from translator/c/src/int.h
    longprod = a * b
    doubleprod = float(a) * float(b)
    doubled_longprod = float(longprod)

    # Fast path for normal case:  small multiplicands, and no info
    # is lost in either method.
    if doubled_longprod == doubleprod:
        return longprod

    # Somebody somewhere lost info.  Close enough, or way off?  Note
    # that a != 0 and b != 0 (else doubled_longprod == doubleprod == 0).
    # The difference either is or isn't significant compared to the
    # true value (of which doubleprod is a good approximation).
    diff = doubled_longprod - doubleprod
    absdiff = abs(diff)
    absprod = abs(doubleprod)
    # absdiff/absprod <= 1/32 iff
    # 32 * absdiff <= absprod -- 5 good bits is "close enough"
    if 32.0 * absdiff <= absprod:
        return longprod
    raise OverflowError("integer multiplication")

# ____________________________________________________________

def delegate_Bool2SmallLong(space, w_bool):
    return W_SmallLongObject(r_longlong(space.is_true(w_bool)))

def delegate_Int2SmallLong(space, w_int):
    return W_SmallLongObject(r_longlong(w_int.intval))

def delegate_SmallLong2Long(space, w_small):
    return W_LongObject(w_small.asbigint())

def delegate_SmallLong2Float(space, w_small):
    return space.newfloat(float(w_small.longlong))

def delegate_SmallLong2Complex(space, w_small):
    return space.newcomplex(float(w_small.longlong), 0.0)


def long__SmallLong(space, w_value):
    return w_value

def int__SmallLong(space, w_value):
    a = w_value.longlong
    b = intmask(a)
    if b == a:
        return space.newint(b)
    else:
        return w_value

def index__SmallLong(space, w_value):
    return w_value

def float__SmallLong(space, w_value):
    return space.newfloat(float(w_value.longlong))

def lt__SmallLong_SmallLong(space, w_small1, w_small2):
    return space.newbool(w_small1.longlong <  w_small2.longlong)
def le__SmallLong_SmallLong(space, w_small1, w_small2):
    return space.newbool(w_small1.longlong <= w_small2.longlong)
def eq__SmallLong_SmallLong(space, w_small1, w_small2):
    return space.newbool(w_small1.longlong == w_small2.longlong)
def ne__SmallLong_SmallLong(space, w_small1, w_small2):
    return space.newbool(w_small1.longlong != w_small2.longlong)
def gt__SmallLong_SmallLong(space, w_small1, w_small2):
    return space.newbool(w_small1.longlong >  w_small2.longlong)
def ge__SmallLong_SmallLong(space, w_small1, w_small2):
    return space.newbool(w_small1.longlong >= w_small2.longlong)

def lt__SmallLong_Long(space, w_small1, w_long2):
    return space.newbool(w_small1.asbigint().lt(w_long2.num))
def le__SmallLong_Long(space, w_small1, w_long2):
    return space.newbool(w_small1.asbigint().le(w_long2.num))
def eq__SmallLong_Long(space, w_small1, w_long2):
    return space.newbool(w_small1.asbigint().eq(w_long2.num))
def ne__SmallLong_Long(space, w_small1, w_long2):
    return space.newbool(w_small1.asbigint().ne(w_long2.num))
def gt__SmallLong_Long(space, w_small1, w_long2):
    return space.newbool(w_small1.asbigint().gt(w_long2.num))
def ge__SmallLong_Long(space, w_small1, w_long2):
    return space.newbool(w_small1.asbigint().ge(w_long2.num))

def lt__Long_SmallLong(space, w_long1, w_small2):
    return space.newbool(w_long1.num.lt(w_small2.asbigint()))
def le__Long_SmallLong(space, w_long1, w_small2):
    return space.newbool(w_long1.num.le(w_small2.asbigint()))
def eq__Long_SmallLong(space, w_long1, w_small2):
    return space.newbool(w_long1.num.eq(w_small2.asbigint()))
def ne__Long_SmallLong(space, w_long1, w_small2):
    return space.newbool(w_long1.num.ne(w_small2.asbigint()))
def gt__Long_SmallLong(space, w_long1, w_small2):
    return space.newbool(w_long1.num.gt(w_small2.asbigint()))
def ge__Long_SmallLong(space, w_long1, w_small2):
    return space.newbool(w_long1.num.ge(w_small2.asbigint()))

def lt__SmallLong_Int(space, w_small1, w_int2):
    return space.newbool(w_small1.longlong <  w_int2.intval)
def le__SmallLong_Int(space, w_small1, w_int2):
    return space.newbool(w_small1.longlong <= w_int2.intval)
def eq__SmallLong_Int(space, w_small1, w_int2):
    return space.newbool(w_small1.longlong == w_int2.intval)
def ne__SmallLong_Int(space, w_small1, w_int2):
    return space.newbool(w_small1.longlong != w_int2.intval)
def gt__SmallLong_Int(space, w_small1, w_int2):
    return space.newbool(w_small1.longlong >  w_int2.intval)
def ge__SmallLong_Int(space, w_small1, w_int2):
    return space.newbool(w_small1.longlong >= w_int2.intval)

def lt__Int_SmallLong(space, w_int1, w_small2):
    return space.newbool(w_int1.intval <  w_small2.longlong)
def le__Int_SmallLong(space, w_int1, w_small2):
    return space.newbool(w_int1.intval <= w_small2.longlong)
def eq__Int_SmallLong(space, w_int1, w_small2):
    return space.newbool(w_int1.intval == w_small2.longlong)
def ne__Int_SmallLong(space, w_int1, w_small2):
    return space.newbool(w_int1.intval != w_small2.longlong)
def gt__Int_SmallLong(space, w_int1, w_small2):
    return space.newbool(w_int1.intval >  w_small2.longlong)
def ge__Int_SmallLong(space, w_int1, w_small2):
    return space.newbool(w_int1.intval >= w_small2.longlong)


#hash: default implementation via Longs  (a bit messy)

def add__SmallLong_SmallLong(space, w_small1, w_small2):
    x = w_small1.longlong
    y = w_small2.longlong
    try:
        z = x + y
        if ((z^x)&(z^y)) < 0:
            raise OverflowError
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                    space.wrap("integer addition"))
    return W_SmallLongObject(z)

def add_ovr(space, w_int1, w_int2):
    x = r_longlong(w_int1.intval)
    y = r_longlong(w_int2.intval)
    return W_SmallLongObject(x + y)

def sub__SmallLong_SmallLong(space, w_small1, w_small2):
    x = w_small1.longlong
    y = w_small2.longlong
    try:
        z = x - y
        if ((z^x)&(z^~y)) < 0:
            raise OverflowError
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                    space.wrap("integer subtraction"))
    return W_SmallLongObject(z)

def sub_ovr(space, w_int1, w_int2):
    x = r_longlong(w_int1.intval)
    y = r_longlong(w_int2.intval)
    return W_SmallLongObject(x - y)

def mul__SmallLong_SmallLong(space, w_small1, w_small2):
    x = w_small1.longlong
    y = w_small2.longlong
    try:
        z = llong_mul_ovf(x, y)
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                    space.wrap("integer multiplication"))
    return W_SmallLongObject(z)

def mul_ovr(space, w_int1, w_int2):
    x = r_longlong(w_int1.intval)
    y = r_longlong(w_int2.intval)
    return W_SmallLongObject(x * y)

#truediv: default implementation via Longs

def floordiv__SmallLong_SmallLong(space, w_small1, w_small2):
    x = w_small1.longlong
    y = w_small2.longlong
    try:
        if y == -1 and x == LONGLONG_MIN:
            raise OverflowError
        z = x // y
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer division by zero"))
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer division"))
    return W_SmallLongObject(z)
div__SmallLong_SmallLong = floordiv__SmallLong_SmallLong

def floordiv_ovr(space, w_int1, w_int2):
    x = r_longlong(w_int1.intval)
    y = r_longlong(w_int2.intval)
    return W_SmallLongObject(x // y)
div_ovr = floordiv_ovr

def mod__SmallLong_SmallLong(space, w_small1, w_small2):
    x = w_small1.longlong
    y = w_small2.longlong
    try:
        if y == -1 and x == LONGLONG_MIN:
            raise OverflowError
        z = x % y
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer modulo by zero"))
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer modulo"))
    return W_SmallLongObject(z)

def mod_ovr(space, w_int1, w_int2):
    x = r_longlong(w_int1.intval)
    y = r_longlong(w_int2.intval)
    return W_SmallLongObject(x % y)

def divmod__SmallLong_SmallLong(space, w_small1, w_small2):
    x = w_small1.longlong
    y = w_small2.longlong
    try:
        if y == -1 and x == LONGLONG_MIN:
            raise OverflowError
        z = x // y
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer divmod by zero"))
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer modulo"))
    # no overflow possible
    m = x % y
    return space.newtuple([W_SmallLongObject(z), W_SmallLongObject(m)])

def divmod_ovr(space, w_int1, w_int2):
    return space.newtuple([div_ovr(space, w_int1, w_int2),
                           mod_ovr(space, w_int1, w_int2)])

def _impl_pow(space, iv, w_int2, iz=r_longlong(0)):
    iw = w_int2.intval
    if iw < 0:
        if iz != 0:
            raise OperationError(space.w_TypeError,
                             space.wrap("pow() 2nd argument "
                 "cannot be negative when 3rd argument specified"))
        ## bounce it, since it always returns float
        raise FailedToImplementArgs(space.w_ValueError,
                                space.wrap("integer exponentiation"))
    temp = iv
    ix = r_longlong(1)
    try:
        while iw > 0:
            if iw & 1:
                ix = llong_mul_ovf(ix, temp)
            iw >>= 1   #/* Shift exponent down by 1 bit */
            if iw==0:
                break
            temp = llong_mul_ovf(temp, temp) #/* Square the value of temp */
            if iz:
                #/* If we did a multiplication, perform a modulo */
                ix = ix % iz
                temp = temp % iz
        if iz:
            ix = ix % iz
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer exponentiation"))
    return W_SmallLongObject(ix)

def pow__SmallLong_Int_SmallLong(space, w_small1, w_int2, w_small3):
    z = w_small3.longlong
    if z == 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("pow() 3rd argument cannot be 0"))
    return _impl_pow(space, w_small1.longlong, w_int2, z)

def pow__SmallLong_Int_None(space, w_small1, w_int2, _):
    return _impl_pow(space, w_small1.longlong, w_int2)

def pow_ovr(space, w_int1, w_int2):
    try:
        return _impl_pow(space, r_longlong(w_int1.intval), w_int2)
    except FailedToImplementArgs:
        from pypy.objspace.std import longobject
        w_a = W_LongObject.fromint(space, w_int1.intval)
        w_b = W_LongObject.fromint(space, w_int2.intval)
        return longobject.pow__Long_Long_None(space, w_a, w_b, space.w_None)

def neg__SmallLong(space, w_small):
    a = w_small.longlong
    try:
        if a == LONGLONG_MIN:
            raise OverflowError
        x = -a
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer negation"))
    return W_SmallLongObject(x)
get_negint = neg__SmallLong

def neg_ovr(space, w_int):
    a = r_longlong(w_int.intval)
    return W_SmallLongObject(-a)


def pos__SmallLong(space, w_small):
    return w_small

def abs__SmallLong(space, w_small):
    if w_small.longlong >= 0:
        return w_small
    else:
        return get_negint(space, w_small)

def abs_ovr(space, w_int):
    a = r_longlong(w_int.intval)
    if a < 0: a = -a
    return W_SmallLongObject(a)

def nonzero__SmallLong(space, w_small):
    return space.newbool(bool(w_small.longlong))

def invert__SmallLong(space, w_small):
    x = w_small.longlong
    a = ~x
    return W_SmallLongObject(a)

def lshift__SmallLong_Int(space, w_small1, w_int2):
    a = w_small1.longlong
    b = w_int2.intval
    if r_uint(b) < LONGLONG_BIT: # 0 <= b < LONGLONG_BIT
        try:
            c = a << b
            if a != (c >> b):
                raise OverflowError
        except OverflowError:
            raise FailedToImplementArgs(space.w_OverflowError,
                                    space.wrap("integer left shift"))
        return W_SmallLongObject(c)
    if b < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("negative shift count"))
    else: #b >= LONGLONG_BIT
        if a == 0:
            return w_small1
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer left shift"))

def lshift_ovr(space, w_int1, w_int2):
    a = r_longlong(w_int1.intval)
    try:
        return lshift__SmallLong_Int(space, W_SmallLongObject(a), w_int2)
    except FailedToImplementArgs:
        from pypy.objspace.std import longobject
        w_a = W_LongObject.fromint(space, w_int1.intval)
        w_b = W_LongObject.fromint(space, w_int2.intval)
        return longobject.lshift__Long_Long(space, w_a, w_b)

def rshift__SmallLong_Int(space, w_small1, w_int2):
    a = w_small1.longlong
    b = w_int2.intval
    if r_uint(b) >= LONGLONG_BIT: # not (0 <= b < LONGLONG_BIT)
        if b < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("negative shift count"))
        else: # b >= LONGLONG_BIT
            if a == 0:
                return w_small1
            if a < 0:
                a = -1
            else:
                a = 0
    else:
        a = a >> b
    return W_SmallLongObject(a)

def and__SmallLong_SmallLong(space, w_small1, w_small2):
    a = w_small1.longlong
    b = w_small2.longlong
    res = a & b
    return W_SmallLongObject(res)

def xor__SmallLong_SmallLong(space, w_small1, w_small2):
    a = w_small1.longlong
    b = w_small2.longlong
    res = a ^ b
    return W_SmallLongObject(res)

def or__SmallLong_SmallLong(space, w_small1, w_small2):
    a = w_small1.longlong
    b = w_small2.longlong
    res = a | b
    return W_SmallLongObject(res)

#oct: default implementation via Longs
#hex: default implementation via Longs
#getnewargs: default implementation via Longs

register_all(vars())

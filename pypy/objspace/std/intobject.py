from pypy.objspace.std.objspace import *
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.rlib.rarithmetic import ovfcheck, ovfcheck_lshift, LONG_BIT, r_uint
from pypy.rlib.rbigint import rbigint
from pypy.objspace.std.inttype import wrapint

"""
In order to have the same behavior running
on CPython, and after RPython translation we use ovfcheck
from rarithmetic to explicitly check for overflows,
something CPython does not do anymore.
"""

class W_IntObject(W_Object):
    __slots__ = 'intval'

    _immutable_ = True
    
    from pypy.objspace.std.inttype import int_typedef as typedef
    
    def __init__(w_self, intval):
        w_self.intval = intval

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%d)" % (w_self.__class__.__name__, w_self.intval)

    def unwrap(w_self, space):
        return int(w_self.intval)


registerimplementation(W_IntObject)


def int_w__Int(space, w_int1):
    return int(w_int1.intval)

def uint_w__Int(space, w_int1):
    intval = w_int1.intval
    if intval < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("cannot convert negative integer to unsigned"))
    else:
        return r_uint(intval)

def bigint_w__Int(space, w_int1):
    return rbigint.fromint(w_int1.intval)

def repr__Int(space, w_int1):
    a = w_int1.intval
    res = str(a)
    return space.wrap(res)

str__Int = repr__Int

def declare_new_int_comparison(opname, clsname):
    # also used by smallintobject.py
    import operator
    from pypy.tool.sourcetools import func_with_new_name
    op = getattr(operator, opname)
    def f(space, w_int1, w_int2):
        i = w_int1.intval
        j = w_int2.intval
        return space.newbool(op(i, j))
    name = "%s__%s_%s" % (opname, clsname, clsname)
    return func_with_new_name(f, name), name

for op in ['lt', 'le', 'eq', 'ne', 'gt', 'ge']:
    func, name = declare_new_int_comparison(op, "Int")
    globals()[name] = func

def hash__Int(space, w_int1):
    # unlike CPython, we don't special-case the value -1 in most of our
    # hash functions, so there is not much sense special-casing it here either.
    # Make sure this is consistent with the hash of floats and longs.
    return int__Int(space, w_int1)

# coerce
def coerce__Int_Int(space, w_int1, w_int2):
    return space.newtuple([w_int1, w_int2])


def add__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x + y)
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer addition"))
    return wrapint(space, z)

def sub__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x - y)
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer substraction"))
    return wrapint(space, z)

def mul__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x * y)
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer multiplication"))
    return wrapint(space, z)

def floordiv__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x // y)
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer division by zero"))
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer division"))
    return wrapint(space, z)
div__Int_Int = floordiv__Int_Int

def truediv__Int_Int(space, w_int1, w_int2):
    x = float(w_int1.intval)
    y = float(w_int2.intval)
    if y == 0.0:
        raise FailedToImplementArgs(space.w_ZeroDivisionError, space.wrap("float division"))    
    return space.wrap(x / y)

def mod__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x % y)
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer modulo by zero"))
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer modulo"))
    return wrapint(space, z)

def divmod__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x // y)
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer divmod by zero"))
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer modulo"))
    # no overflow possible
    m = x % y
    w = space.wrap
    return space.newtuple([w(z), w(m)])


# helper for pow()
def _impl_int_int_pow(space, iv, iw, iz=0):
    if iw < 0:
        if iz != 0:
            raise OperationError(space.w_TypeError,
                             space.wrap("pow() 2nd argument "
                 "cannot be negative when 3rd argument specified"))
        ## bounce it, since it always returns float
        raise FailedToImplementArgs(space.w_ValueError,
                                space.wrap("integer exponentiation"))
    temp = iv
    ix = 1
    try:
        while iw > 0:
            if iw & 1:
                ix = ovfcheck(ix*temp)
            iw >>= 1   #/* Shift exponent down by 1 bit */
            if iw==0:
                break
            temp = ovfcheck(temp*temp) #/* Square the value of temp */
            if iz:
                #/* If we did a multiplication, perform a modulo */
                ix = ix % iz;
                temp = temp % iz;
        if iz:
            ix = ix % iz
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer exponentiation"))
    return wrapint(space, ix)

def pow__Int_Int_Int(space, w_int1, w_int2, w_int3):
    x = w_int1.intval
    y = w_int2.intval
    z = w_int3.intval
    if z == 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("pow() 3rd argument cannot be 0"))
    return _impl_int_int_pow(space, x, y, z)

def pow__Int_Int_None(space, w_int1, w_int2, w_int3):
    x = w_int1.intval
    y = w_int2.intval
    return _impl_int_int_pow(space, x, y)

def neg__Int(space, w_int1):
    a = w_int1.intval
    try:
        x = ovfcheck(-a)
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer negation"))
    return wrapint(space, x)


def abs__Int(space, w_int1):
    if w_int1.intval >= 0:
        return pos__Int(space, w_int1)
    else:
        return neg__Int(space, w_int1)

def nonzero__Int(space, w_int1):
    return space.newbool(w_int1.intval != 0)

def invert__Int(space, w_int1):
    x = w_int1.intval
    a = ~x
    return wrapint(space, a)

def lshift__Int_Int(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    if b < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("negative shift count"))
    if a == 0 or b == 0:
        return int__Int(space, w_int1)
    if b >= LONG_BIT:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer left shift"))
    try:
        c = ovfcheck_lshift(a, b)
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer left shift"))
    return wrapint(space, c)

def rshift__Int_Int(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    if b < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("negative shift count"))
    if a == 0 or b == 0:
        return int__Int(space, w_int1)
    if b >= LONG_BIT:
        if a < 0:
            a = -1
        else:
            a = 0
    else:
        a = a >> b
    return wrapint(space, a)

def and__Int_Int(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    res = a & b
    return wrapint(space, res)

def xor__Int_Int(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    res = a ^ b
    return wrapint(space, res)

def or__Int_Int(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    res = a | b
    return wrapint(space, res)

# int__Int is supposed to do nothing, unless it has
# a derived integer object, where it should return
# an exact one.
def int__Int(space, w_int1):
    if space.is_w(space.type(w_int1), space.w_int):
        return w_int1
    a = w_int1.intval
    return wrapint(space, a)
pos__Int = int__Int

def index__Int(space, w_int1):
    return int__Int(space, w_int1)

def float__Int(space, w_int1):
    a = w_int1.intval
    x = float(a)
    return space.newfloat(x)

def oct__Int(space, w_int1):
    return space.wrap(oct(w_int1.intval))

def hex__Int(space, w_int1):
    return space.wrap(hex(w_int1.intval))

def getnewargs__Int(space, w_int1):
    return space.newtuple([wrapint(space, w_int1.intval)])


register_all(vars())

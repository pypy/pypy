"""
Implementation of small ints, stored as odd-valued pointers in the
translated PyPy.  To enable them, see inttype.py.
"""
from pypy.objspace.std.objspace import *
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.rlib.rarithmetic import ovfcheck, ovfcheck_lshift, LONG_BIT, r_uint
from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.intobject import W_IntObject, declare_new_int_comparison
from pypy.rlib.objectmodel import UnboxedValue

# XXX this is a complete copy of intobject.py.  Find a better but still
# XXX annotator-friendly way to share code...


class W_SmallIntObject(W_Object, UnboxedValue):
    __slots__ = 'intval'
    from pypy.objspace.std.inttype import int_typedef as typedef

    def unwrap(w_self, space):
        return int(w_self.intval)


registerimplementation(W_SmallIntObject)


def delegate_SmallInt2Int(space, w_small):
    return W_IntObject(w_small.intval)

def delegate_SmallInt2Long(space, w_small):
    return space.newlong(w_small.intval)

def delegate_SmallInt2Float(space, w_small):
    return space.newfloat(float(w_small.intval))

def delegate_SmallInt2Complex(space, w_small):
    return space.newcomplex(float(w_small.intval), 0.0)


def int_w__SmallInt(space, w_int1):
    return int(w_int1.intval)

def uint_w__SmallInt(space, w_int1):
    intval = w_int1.intval
    if intval < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("cannot convert negative integer to unsigned"))
    else:
        return r_uint(intval)

def repr__SmallInt(space, w_int1):
    a = w_int1.intval
    res = str(a)
    return space.wrap(res)

str__SmallInt = repr__SmallInt

for op in ['lt', 'le', 'eq', 'ne', 'gt', 'ge']:
    func, name = declare_new_int_comparison(op, "SmallInt")
    globals()[name] = func

def hash__SmallInt(space, w_int1):
    # unlike CPython, we don't special-case the value -1 in most of our
    # hash functions, so there is not much sense special-casing it here either.
    # Make sure this is consistent with the hash of floats and longs.
    return int__SmallInt(space, w_int1)

# coerce
def coerce__SmallInt_SmallInt(space, w_int1, w_int2):
    return space.newtuple([w_int1, w_int2])


def add__SmallInt_SmallInt(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    # note that no overflow checking is necessary here: x and y fit into 31
    # bits (or 63 bits respectively), so their sum fits into 32 (or 64) bits.
    # wrapint then makes sure that either a tagged int or a normal int is
    # created
    return wrapint(space, x + y)

def sub__SmallInt_SmallInt(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    # see comment in add__SmallInt_SmallInt
    return wrapint(space, x - y)

def mul__SmallInt_SmallInt(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x * y)
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer multiplication"))
    return wrapint(space, z)

def div__SmallInt_SmallInt(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    if y == 0:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer division by zero"))
    # no overflow possible
    return wrapint(space, x // y)

floordiv__SmallInt_SmallInt = div__SmallInt_SmallInt

def truediv__SmallInt_SmallInt(space, w_int1, w_int2):
    x = float(w_int1.intval)
    y = float(w_int2.intval)
    if y == 0.0:
        raise FailedToImplementArgs(space.w_ZeroDivisionError, space.wrap("float division"))    
    return space.wrap(x / y)

def mod__SmallInt_SmallInt(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    if y == 0:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer modulo by zero"))
    # no overflow possible
    return wrapint(space, x % y)

def divmod__SmallInt_SmallInt(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    if y == 0:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer divmod by zero"))
    # no overflow possible
    z = x // y
    m = x % y
    return space.newtuple([space.wrap(z), space.wrap(m)])

def pow__SmallInt_SmallInt_SmallInt(space, w_int1, w_int2, w_int3):
    from pypy.objspace.std.intobject import _impl_int_int_pow
    x = w_int1.intval
    y = w_int2.intval
    z = w_int3.intval
    if z == 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("pow() 3rd argument cannot be 0"))
    return _impl_int_int_pow(space, x, y, z)

def pow__SmallInt_SmallInt_None(space, w_int1, w_int2, w_int3):
    from pypy.objspace.std.intobject import _impl_int_int_pow
    x = w_int1.intval
    y = w_int2.intval
    return _impl_int_int_pow(space, x, y)

def neg__SmallInt(space, w_int1):
    a = w_int1.intval
    # no overflow possible since a fits into 31/63 bits
    return wrapint(space, -a)


def abs__SmallInt(space, w_int1):
    if w_int1.intval >= 0:
        return pos__SmallInt(space, w_int1)
    else:
        return neg__SmallInt(space, w_int1)

def nonzero__SmallInt(space, w_int1):
    return space.newbool(w_int1.intval != 0)

def invert__SmallInt(space, w_int1):
    x = w_int1.intval
    a = ~x
    return wrapint(space, a)

def lshift__SmallInt_SmallInt(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    if b < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("negative shift count"))
    if a == 0 or b == 0:
        return int__SmallInt(space, w_int1)
    if b >= LONG_BIT:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer left shift"))
    try:
        c = ovfcheck_lshift(a, b)
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer left shift"))
    return wrapint(space, c)

def rshift__SmallInt_SmallInt(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    if b < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("negative shift count"))
    if a == 0 or b == 0:
        return int__SmallInt(space, w_int1)
    if b >= LONG_BIT:
        if a < 0:
            a = -1
        else:
            a = 0
    else:
        a = a >> b
    return wrapint(space, a)

def and__SmallInt_SmallInt(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    res = a & b
    return wrapint(space, res)

def xor__SmallInt_SmallInt(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    res = a ^ b
    return wrapint(space, res)

def or__SmallInt_SmallInt(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    res = a | b
    return wrapint(space, res)

# int__SmallInt is supposed to do nothing, unless it has
# a derived integer object, where it should return
# an exact one.
def int__SmallInt(space, w_int1):
    if space.is_w(space.type(w_int1), space.w_int):
        return w_int1
    a = w_int1.intval
    return W_SmallIntObject(a)
pos__SmallInt = int__SmallInt

def float__SmallInt(space, w_int1):
    a = w_int1.intval
    x = float(a)
    return space.newfloat(x)

def oct__SmallInt(space, w_int1):
    return space.wrap(oct(w_int1.intval))

def hex__SmallInt(space, w_int1):
    return space.wrap(hex(w_int1.intval))

def getnewargs__SmallInt(space, w_int1):
    return space.newtuple([wrapint(space, w_int1.intval)])


register_all(vars())

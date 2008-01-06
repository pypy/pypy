"""
Implementation of small ints, stored as odd-valued pointers in the
translated PyPy.  To enable them, see inttype.py.
"""
from pypy.objspace.std.objspace import *
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.rlib.rarithmetic import ovfcheck, ovfcheck_lshift, LONG_BIT, r_uint
from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.intobject import W_IntObject
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


"""
XXX not implemented:
free list
FromString
FromUnicode
print
"""

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

def lt__SmallInt_SmallInt(space, w_int1, w_int2):
    i = w_int1.intval
    j = w_int2.intval
    return space.newbool( i < j )

def le__SmallInt_SmallInt(space, w_int1, w_int2):
    i = w_int1.intval
    j = w_int2.intval
    return space.newbool( i <= j )

def eq__SmallInt_SmallInt(space, w_int1, w_int2):
    i = w_int1.intval
    j = w_int2.intval
    return space.newbool( i == j )

def ne__SmallInt_SmallInt(space, w_int1, w_int2):
    i = w_int1.intval
    j = w_int2.intval
    return space.newbool( i != j )

def gt__SmallInt_SmallInt(space, w_int1, w_int2):
    i = w_int1.intval
    j = w_int2.intval
    return space.newbool( i > j )

def ge__SmallInt_SmallInt(space, w_int1, w_int2):
    i = w_int1.intval
    j = w_int2.intval
    return space.newbool( i >= j )

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
    try:
        z = ovfcheck(x + y)
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer addition"))
    return wrapint(space, z)

def sub__SmallInt_SmallInt(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x - y)
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer substraction"))
    return wrapint(space, z)

def mul__SmallInt_SmallInt(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x * y)
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer multiplication"))
    return wrapint(space, z)

def _floordiv(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x // y)
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer division by zero"))
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer division"))
    return wrapint(space, z)

def _truediv(space, w_int1, w_int2):
    # XXX how to do delegation to float elegantly?
    # avoiding a general space.div operation which pulls
    # the whole interpreter in.
    # Instead, we delegate to long for now.
    raise FailedToImplement(space.w_TypeError,
                            space.wrap("integer division"))

def mod__SmallInt_SmallInt(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x % y)
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer modulo by zero"))
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer modulo"))
    return wrapint(space, z)

def divmod__SmallInt_SmallInt(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x // y)
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer divmod by zero"))
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer modulo"))
    # no overflow possible
    m = x % y
    return space.newtuple([space.wrap(z), space.wrap(m)])

def div__SmallInt_SmallInt(space, w_int1, w_int2):
    return _floordiv(space, w_int1, w_int2)

floordiv__SmallInt_SmallInt = _floordiv
truediv__SmallInt_SmallInt = _truediv

# helper for pow()
def _impl_int_int_pow(space, iv, iw, iz=0):
    if iw < 0:
        if iz != 0:
            raise OperationError(space.w_TypeError,
                             space.wrap("pow() 2nd argument "
                 "cannot be negative when 3rd argument specified"))
        ## bounce it, since it always returns float
        raise FailedToImplement(space.w_ValueError,
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
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer exponentiation"))
    return wrapint(space, ix)

def pow__SmallInt_SmallInt_SmallInt(space, w_int1, w_int2, w_int3):
    x = w_int1.intval
    y = w_int2.intval
    z = w_int3.intval
    if z == 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("pow() 3rd argument cannot be 0"))
    return _impl_int_int_pow(space, x, y, z)

def pow__SmallInt_SmallInt_None(space, w_int1, w_int2, w_int3):
    x = w_int1.intval
    y = w_int2.intval
    return _impl_int_int_pow(space, x, y)

def neg__SmallInt(space, w_int1):
    a = w_int1.intval
    try:
        x = ovfcheck(-a)
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer negation"))
    return wrapint(space, x)

# pos__SmallInt is supposed to do nothing, unless it has
# a derived integer object, where it should return
# an exact one.
def pos__SmallInt(space, w_int1):
    return int__SmallInt(space, w_int1)

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
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer left shift"))
    ##
    ## XXX please! have a look into pyport.h and see how to implement
    ## the overflow checking, using macro Py_ARITHMETIC_RIGHT_SHIFT
    ## we *assume* that the overflow checking is done correctly
    ## in the code generator, which is not trivial!
    
    ## XXX also note that Python 2.3 returns a long and never raises
    ##     OverflowError.
    try:
        c = ovfcheck_lshift(a, b)
        ## the test in C code is
        ## if (a != Py_ARITHMETIC_RIGHT_SHIFT(long, c, b)) {
        ##     if (PyErr_Warn(PyExc_FutureWarning,
        # and so on
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError,
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
        ## please look into pyport.h, how >> should be implemented!
        ## a = Py_ARITHMETIC_RIGHT_SHIFT(long, a, b);
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

# coerce is not wanted
##
##static int
##coerce__Int(PyObject **pv, PyObject **pw)
##{
##    if (PyInt_Check(*pw)) {
##        Py_INCREF(*pv);
##        Py_INCREF(*pw);
##        return 0;
##    }
##    return 1; /* Can't do it */
##}

# int__SmallInt is supposed to do nothing, unless it has
# a derived integer object, where it should return
# an exact one.
def int__SmallInt(space, w_int1):
    if space.is_w(space.type(w_int1), space.w_int):
        return w_int1
    a = w_int1.intval
    return wrapint(space, a)

"""
# Not registered
def long__SmallInt(space, w_int1):
    a = w_int1.intval
    x = long(a)  ## XXX should this really be done so?
    return space.newlong(x)
"""

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

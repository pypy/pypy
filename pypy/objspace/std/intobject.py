from pypy.objspace.std.objspace import *
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.tool.rarithmetic import ovfcheck, ovfcheck_lshift, LONG_BIT, r_uint

"""
In order to have the same behavior running
on CPython, and after RPython translation we use ovfcheck
from rarithmetic to explicitly check for overflows,
something CPython does not do anymore.
"""

class W_IntObject(W_Object):
    from pypy.objspace.std.inttype import int_typedef as typedef
    
    def __init__(w_self, space, intval):
        W_Object.__init__(w_self, space)
        w_self.intval = intval

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%d)" % (w_self.__class__.__name__, w_self.intval)

    def unwrap(w_self):
        return int(w_self.intval)


registerimplementation(W_IntObject)


"""
XXX not implemented:
free list
FromString
FromUnicode
print
"""

def int_w__Int(space, w_int1):
    return int(w_int1.intval)

def uint_w__Int(space, w_int1):
    intval = w_int1.intval
    if intval < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("cannot convert negative integer to unsigned"))
    else:
        return r_uint(intval)

def repr__Int(space, w_int1):
    a = w_int1.intval
    res = str(a)
    return space.wrap(res)

str__Int = repr__Int

## deprecated
## we are going to support rich compare, only

##def int_int_cmp(space, w_int1, w_int2):
##    i = w_int1.intval
##    j = w_int2.intval
##    if i < j:
##        ret = -1
##    elif i > j:
##        ret = 1
##    else:
##        ret = 0
##    return W_IntObject(space, ret)
##
##StdObjSpace.cmp.register(int_int_cmp, W_IntObject, W_IntObject)

def lt__Int_Int(space, w_int1, w_int2):
    i = w_int1.intval
    j = w_int2.intval
    return space.newbool( i < j )

def le__Int_Int(space, w_int1, w_int2):
    i = w_int1.intval
    j = w_int2.intval
    return space.newbool( i <= j )

def eq__Int_Int(space, w_int1, w_int2):
    i = w_int1.intval
    j = w_int2.intval
    return space.newbool( i == j )

def ne__Int_Int(space, w_int1, w_int2):
    i = w_int1.intval
    j = w_int2.intval
    return space.newbool( i != j )

def gt__Int_Int(space, w_int1, w_int2):
    i = w_int1.intval
    j = w_int2.intval
    return space.newbool( i > j )

def ge__Int_Int(space, w_int1, w_int2):
    i = w_int1.intval
    j = w_int2.intval
    return space.newbool( i >= j )

STRICT_HASH = True # temporary, to be put elsewhere or removed

def _hash_strict(space, w_int1):
    #/* XXX If this is changed, you also need to change the way
    #   Python's long, float and complex types are hashed. */
    x = w_int1.intval
    if x == -1:
        x = -2
    return W_IntObject(space, x)

def _hash_liberal(space, w_int1):
    # Armin: unlike CPython we have no need to special-case the value -1
    return w_int1

# Chris: I'm not yet convinced that we want to make hash()
# return different values that CPython does.
# So for the moment, both versions are here,
# and we might think of some config options
# or decide to drop compatibility (using pypy-dev).

def hash__Int(space, w_int1):
    if STRICT_HASH:
        return _hash_strict(space, w_int1)
    else:
        return _hash_liberal(space, w_int1)

# coerce
def coerce__Int_Int(space, w_int1, w_int2):
    return space.newtuple([w_int1, w_int2])


def add__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x + y)
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer addition"))
    return W_IntObject(space, z)

def sub__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x - y)
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer substraction"))
    return W_IntObject(space, z)

def mul__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x * y)
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer multiplication"))
    return W_IntObject(space, z)

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
    return W_IntObject(space, z)

def _truediv(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x // y)
        t = ovfcheck(x % y)
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer division by zero"))
    except OverflowError:
        return space.div(space.newfloat(float(x)), w_int2)
    if t != 0:   # gives a float
        return space.div(space.newfloat(float(x)), w_int2)
    return W_IntObject(space, z)

def mod__Int_Int(space, w_int1, w_int2):
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
    return W_IntObject(space, z)

def divmod__Int_Int(space, w_int1, w_int2):
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
    return space.wrap((z,m))

old_style_div = 1 / 2 == 1 // 2
def div__Int_Int(space, w_int1, w_int2):
    # Select the proper div
    if old_style_div:
        return _floordiv(space, w_int1, w_int2)
    else:
        return _truediv(space, w_int1, w_int2)

floordiv__Int_Int = _floordiv
truediv__Int_Int = _truediv

# helper for pow()
def _impl_int_int_pow(space, iv, iw, iz=None):
    if iw < 0:
        if iz is not None:
            raise OperationError(space.w_TypeError,
                             space.wrap("pow() 2nd argument "
                 "cannot be negative when 3rd argument specified"))
        return space.pow(space.float(space.wrap(iv)),
                         space.float(space.wrap(iw)),
                         space.w_None)
        ## bounce it, since it always returns float
        raise FailedToImplement(space.w_ValueError,
                                space.wrap("integer exponentiation"))
    if iz is not None:
        if iz == 0:
            raise OperationError(space.w_ValueError,
                                    space.wrap("pow() 3rd argument cannot be 0"))
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
    return W_IntObject(space, ix)

"""
def pow__Int_Int_Int(space, w_int1, w_int2, w_int3):
    x = w_int1.intval
    y = w_int2.intval
    z = w_int3.intval
    ret = _impl_int_int_pow(space, x, y, z)
    return W_IntObject(space, ret)
"""

def pow__Int_Int_Int(space, w_int1, w_int2, w_int3):
    x = w_int1.intval
    y = w_int2.intval
    z = w_int3.intval
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
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer negation"))
    return W_IntObject(space, x)

# pos__Int is supposed to do nothing, unless it has
# a derived integer object, where it should return
# an exact one.
def pos__Int(space, w_int1):
    return int__Int(space, w_int1)

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
    return W_IntObject(space, a)

def lshift__Int_Int(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    if b < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("negative shift count"))
    if a == 0 or b == 0:
        return int__Int(space, w_int1)
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
    return W_IntObject(space, c)

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
        ## please look into pyport.h, how >> should be implemented!
        ## a = Py_ARITHMETIC_RIGHT_SHIFT(long, a, b);
        a = a >> b
    return W_IntObject(space, a)

def and__Int_Int(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    res = a & b
    return W_IntObject(space, res)

def xor__Int_Int(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    res = a ^ b
    return W_IntObject(space, res)

def or__Int_Int(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    res = a | b
    return W_IntObject(space, res)

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

# int__Int is supposed to do nothing, unless it has
# a derived integer object, where it should return
# an exact one.
def int__Int(space, w_int1):
    if space.is_true(space.is_(space.type(w_int1), space.w_int)):
        return w_int1
    a = w_int1.intval
    return W_IntObject(space, a)

"""
# Not registered
def long__Int(space, w_int1):
    a = w_int1.intval
    x = long(a)  ## XXX should this really be done so?
    return space.newlong(x)
"""

def float__Int(space, w_int1):
    a = w_int1.intval
    x = float(a)
    return space.newfloat(x)

def oct__Int(space, w_int1):
    x = w_int1.intval
    if x < 0:
        ## XXX what about this warning?
        #if (PyErr_Warn(PyExc_FutureWarning,
        #           "hex()/oct() of negative int will return "
        #           "a signed string in Python 2.4 and up") < 0)
        #    return NULL;
        pass
    if x == 0:
        ret = "0"
    else:
        ret = "0%lo" % x
    return space.wrap(ret)

def hex__Int(space, w_int1):
    x = w_int1.intval
    if x < 0:
        ## XXX what about this warning?
        #if (PyErr_Warn(PyExc_FutureWarning,
        #           "hex()/oct() of negative int will return "
        #           "a signed string in Python 2.4 and up") < 0)
        #    return NULL;
        pass
    ret = "0x%lx" % x
    return space.wrap(ret)

register_all(vars())

from pypy.objspace.std.objspace import *
from inttype import W_IntType
from noneobject import W_NoneObject
from restricted_int import r_int, LONG_BIT

applicationfile = StdObjSpace.AppFile(__name__)

"""
The implementation of integers is a bit difficult,
since integers are currently undergoing the change to turn
themselves into longs under overflow circumstances.
The restricted Python does not overflow or throws
exceptions.
The definitions in this file are fine, given that
restricted Python integers behave that way.
But for testing, the resticted stuff must be run
by CPython which has different behavior.
For that reason, I defined an r_int extension class
for native integers, which tries to behave as in
RPython, just for test purposes.
"""

class W_IntObject(W_Object):
    statictype = W_IntType
    
    def __init__(w_self, space, intval):
        W_Object.__init__(w_self, space)
        w_self.intval = r_int(intval)

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%d)" % (w_self.__class__.__name__, w_self.intval)


registerimplementation(W_IntObject)


"""
XXX not implemented:
free list
FromString
FromUnicode
print
"""

def int_unwrap(space, w_int1):
    return w_int1.intval

StdObjSpace.unwrap.register(int_unwrap, W_IntObject)

def int_repr(space, w_int1):
    a = w_int1.intval
    res = "%ld" % a
    return space.wrap(res)

StdObjSpace.repr.register(int_repr, W_IntObject)

int_str = int_repr

StdObjSpace.str.register(int_str, W_IntObject)

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

def int_int_lt(space, w_int1, w_int2):
    i = w_int1.intval
    j = w_int2.intval
    return space.newbool( i < j )
StdObjSpace.lt.register(int_int_lt, W_IntObject, W_IntObject)

def int_int_le(space, w_int1, w_int2):
    i = w_int1.intval
    j = w_int2.intval
    return space.newbool( i <= j )
StdObjSpace.le.register(int_int_le, W_IntObject, W_IntObject)

def int_int_eq(space, w_int1, w_int2):
    i = w_int1.intval
    j = w_int2.intval
    return space.newbool( i == j )
StdObjSpace.eq.register(int_int_eq, W_IntObject, W_IntObject)

def int_int_ne(space, w_int1, w_int2):
    i = w_int1.intval
    j = w_int2.intval
    return space.newbool( i != j )
StdObjSpace.ne.register(int_int_ne, W_IntObject, W_IntObject)

def int_int_gt(space, w_int1, w_int2):
    i = w_int1.intval
    j = w_int2.intval
    return space.newbool( i > j )
StdObjSpace.gt.register(int_int_gt, W_IntObject, W_IntObject)

def int_int_ge(space, w_int1, w_int2):
    i = w_int1.intval
    j = w_int2.intval
    return space.newbool( i >= j )
StdObjSpace.ge.register(int_int_ge, W_IntObject, W_IntObject)

STRICT_HASH = True # temporary, to be put elsewhere or removed

def int_hash_strict(space, w_int1):
    #/* XXX If this is changed, you also need to change the way
    #   Python's long, float and complex types are hashed. */
    x = w_int1.intval
    if x == -1:
        x = -2
    return W_IntObject(space, x)

def int_hash_liberal(space, w_int1):
    # Armin: unlike CPython we have no need to special-case the value -1
    return w_int1

# Chris: I'm not yet convinced that we want to make hash()
# return different values that CPython does.
# So for the moment, both versions are here,
# and we might think of some config options
# or decide to drop compatibility (using pypy-dev).

if STRICT_HASH:
    int_hash = int_hash_strict
else:
    int_hash = int_hash_liberal

StdObjSpace.hash.register(int_hash, W_IntObject)

def int_int_add(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = x + y
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer addition"))
    return W_IntObject(space, z)

StdObjSpace.add.register(int_int_add, W_IntObject, W_IntObject)

def int_int_sub(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = x - y
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer substraction"))
    return W_IntObject(space, z)

StdObjSpace.sub.register(int_int_sub, W_IntObject, W_IntObject)

def int_int_mul(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = x * y
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer multiplication"))
    return W_IntObject(space, z)

StdObjSpace.mul.register(int_int_mul, W_IntObject, W_IntObject)

def int_int_floordiv(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = x // y
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer division by zero"))
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer division"))
    return W_IntObject(space, z)

StdObjSpace.floordiv.register(int_int_floordiv, W_IntObject, W_IntObject)

def int_int_truediv(space, w_int1, w_int2):
    # cannot implement, since it gives floats
    raise FailedToImplement(space.w_OverflowError,
                            space.wrap("integer division"))

StdObjSpace.truediv.register(int_int_truediv, W_IntObject, W_IntObject)

def int_int_mod(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = x % y
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer modulo by zero"))
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer modulo"))
    return W_IntObject(space, z)

StdObjSpace.mod.register(int_int_mod, W_IntObject, W_IntObject)

def int_int_divmod(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = x // y
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer divmod by zero"))
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer modulo"))
    # no overflow possible
    m = x % y
    return space.wrap((z,m))

StdObjSpace.divmod.register(int_int_divmod, W_IntObject, W_IntObject)

## install the proper int_int_div
if 1 / 2 == 1 // 2:
    int_int_div = int_int_floordiv
else:
    int_int_div = int_int_truediv

StdObjSpace.div.register(int_int_div, W_IntObject, W_IntObject)

# helper for pow()

def _impl_int_int_pow(space, iv, iw, iz=None):
    if iw < 0:
        if iz is not None:
            raise OperationError(space.w_TypeError,
                             space.wrap("pow() 2nd argument "
                 "cannot be negative when 3rd argument specified"))
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
                ix = ix*temp
            iw >>= 1   #/* Shift exponent down by 1 bit */
            if iw==0:
                break
            temp *= temp   #/* Square the value of temp */
            if iz:
                #/* If we did a multiplication, perform a modulo */
                ix = ix % iz;
                temp = temp % iz;
        if iz:
            ix = ix % iz
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer exponentiation"))
    return ix

def int_int_int_pow(space, w_int1, w_int2, w_int3):
    x = w_int1.intval
    y = w_int2.intval
    z = w_int3.intval
    ret = _impl_int_int_pow(space, x, y, z)
    return W_IntObject(space, ret)

StdObjSpace.pow.register(int_int_int_pow, W_IntObject, W_IntObject, W_IntObject)

def int_int_none_pow(space, w_int1, w_int2, w_none=None):
    x = w_int1.intval
    y = w_int2.intval
    ret = _impl_int_int_pow(space, x, y)
    return W_IntObject(space, ret)

StdObjSpace.pow.register(int_int_none_pow, W_IntObject, W_IntObject, W_NoneObject)

def int_neg(space, w_int1):
    a = w_int1.intval
    try:
        x = -a
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer negation"))
    return W_IntObject(space, x)

StdObjSpace.neg.register(int_neg, W_IntObject)

# int_pos is supposed to do nothing, unless it has
# a derived integer object, where it should return
# an exact one.
def int_pos(space, w_int1):
    #not sure if this should be done this way:
    if w_int1.__class__ is W_IntObject:
        return w_int1
    a = w_int1.intval
    return W_IntObject(space, a)

StdObjSpace.pos.register(int_pos, W_IntObject)

def int_abs(space, w_int1):
    if w_int1.intval >= 0:
        return int_pos(space, w_int1)
    else:
        return int_neg(space, w_int1)

StdObjSpace.abs.register(int_abs, W_IntObject)

def int_is_true(space, w_int1):
    return space.newbool(w_int1.intval != 0)

StdObjSpace.is_true.register(int_is_true, W_IntObject)

def int_invert(space, w_int1):
    x = w_int1.intval
    a = ~x
    return W_IntObject(space, a)

StdObjSpace.invert.register(int_invert, W_IntObject)

def int_int_lshift(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    if b < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("negative shift count"))
    if a == 0 or b == 0:
        return int_pos(w_int1)
    if b >= LONG_BIT:
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer left shift"))
    ##
    ## XXX please! have a look into pyport.h and see how to implement
    ## the overflow checking, using macro Py_ARITHMETIC_RIGHT_SHIFT
    ## we *assume* that the overflow checking is done correctly
    ## in the code generator, which is not trivial!
    try:
        c = a << b
        ## the test in C code is
        ## if (a != Py_ARITHMETIC_RIGHT_SHIFT(long, c, b)) {
        ##     if (PyErr_Warn(PyExc_FutureWarning,
        # and so on
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError,
                                space.wrap("integer left shift"))
    return W_IntObject(space, c)

StdObjSpace.lshift.register(int_int_lshift, W_IntObject, W_IntObject)

def int_int_rshift(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    if b < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("negative shift count"))
    if a == 0 or b == 0:
        return int_pos(w_int1)
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

StdObjSpace.rshift.register(int_int_rshift, W_IntObject, W_IntObject)

def int_int_and(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    res = a & b
    return W_IntObject(space, res)

StdObjSpace.and_.register(int_int_and, W_IntObject, W_IntObject)

def int_int_xor(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    res = a ^ b
    return W_IntObject(space, res)

StdObjSpace.xor.register(int_int_xor, W_IntObject, W_IntObject)

def int_int_or(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    res = a | b
    return W_IntObject(space, res)

StdObjSpace.or_.register(int_int_or, W_IntObject, W_IntObject)

# coerce is not wanted
##
##static int
##int_coerce(PyObject **pv, PyObject **pw)
##{
##    if (PyInt_Check(*pw)) {
##        Py_INCREF(*pv);
##        Py_INCREF(*pw);
##        return 0;
##    }
##    return 1; /* Can't do it */
##}

def int_int(space, w_int1):
    return w_int1

#?StdObjSpace.int.register(int_int, W_IntObject)

def int_long(space, w_int1):
    a = w_int1.intval
    x = long(a)  ## XXX should this really be done so?
    return space.newlong(x)

#?StdObjSpace.long.register(int_long, W_IntObject)

def int_float(space, w_int1):
    a = w_int1.intval
    x = float(a)
    return space.newdouble(x)

#?StdObjSpace.float.register(int_float, W_IntObject)

def int_oct(space, w_int1):
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

StdObjSpace.oct.register(int_oct, W_IntObject)

def int_hex(space, w_int1):
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
        ret = "0x%lx" % x
    return space.wrap(ret)

StdObjSpace.hex.register(int_hex, W_IntObject)

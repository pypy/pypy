from pypy.objspace.std.objspace import *
from floattype import W_FloatType

##############################################################
# for the time being, all calls that are made to some external
# libraries in the floatobject.c, calls are made into the 
# python math library
##############################################################

import math
import intobject

applicationfile = StdObjSpace.AppFile(__name__)

class W_FloatObject(W_Object):
    """This is a reimplementation of the CPython "PyFloatObject" 
       it is assumed that the constructor takes a real Python float as
       an argument"""

    delegate_once = {}
    statictype = W_FloatType
    
    def __init__(w_self, space, floatval):
        W_Object.__init__(w_self, space)
        w_self.floatval = floatval

# int-to-float delegation
def int_to_float(space, w_intobj):
    return W_FloatObject(space, float(w_intobj.intval))
intobject.W_IntObject.delegate_once[W_FloatObject] = int_to_float


def float_float(space,w_value):
    if w_value.__class__ == W_FloatObject:
        return w_value
    else:
        return W_FloatObject(space, w_value.floatval)

#?StdObjSpace.float.register(float_float, W_FloatObject)

def float_unwrap(space, w_float):
    return w_float.floatval

StdObjSpace.unwrap.register(float_unwrap, W_FloatObject)

def float_repr(space, w_float):
    ## %reimplement%
    # uses CPython "repr" builtin function
    return space.wrap(repr(w_float.floatval))

StdObjSpace.repr.register(float_repr, W_FloatObject)

def float_str(space, w_float):
    ## %reimplement%
    # uses CPython "str" builtin function
    return space.wrap(str(w_float.floatval))

StdObjSpace.str.register(float_str, W_FloatObject)

def float_float_lt(space, w_float1, w_float2):
    i = w_float1.floatval
    j = w_float2.floatval
    return space.newbool( i < j )
StdObjSpace.lt.register(float_float_lt, W_FloatObject, W_FloatObject)

def float_float_le(space, w_float1, w_float2):
    i = w_float1.floatval
    j = w_float2.floatval
    return space.newbool( i <= j )
StdObjSpace.le.register(float_float_le, W_FloatObject, W_FloatObject)

def float_float_eq(space, w_float1, w_float2):
    i = w_float1.floatval
    j = w_float2.floatval
    return space.newbool( i == j )
StdObjSpace.eq.register(float_float_eq, W_FloatObject, W_FloatObject)

def float_float_ne(space, w_float1, w_float2):
    i = w_float1.floatval
    j = w_float2.floatval
    return space.newbool( i != j )
StdObjSpace.ne.register(float_float_ne, W_FloatObject, W_FloatObject)

def float_float_gt(space, w_float1, w_float2):
    i = w_float1.floatval
    j = w_float2.floatval
    return space.newbool( i > j )
StdObjSpace.gt.register(float_float_gt, W_FloatObject, W_FloatObject)

def float_float_ge(space, w_float1, w_float2):
    i = w_float1.floatval
    j = w_float2.floatval
    return space.newbool( i >= j )
StdObjSpace.ge.register(float_float_ge, W_FloatObject, W_FloatObject)
    
def float_hash(space,w_value):
    ## %reimplement%
    # real Implementation should be taken from _Py_HashDouble in object.c
    return space.wrap(hash(w_value.floatval))

StdObjSpace.hash.register(float_hash, W_FloatObject)

def float_float_add(space, w_float1, w_float2):
    x = w_float1.floatval
    y = w_float2.floatval
    try:
        z = x + y
    except FloatingPointError:
        raise FailedToImplement(space.w_FloatingPointError, space.wrap("float addition"))
    return W_FloatObject(space, z)

StdObjSpace.add.register(float_float_add, W_FloatObject, W_FloatObject)

def float_float_sub(space, w_float1, w_float2):
    x = w_float1.floatval
    y = w_float2.floatval
    try:
        z = x - y
    except FloatingPointError:
        raise FailedToImplement(space.w_FloatingPointError, space.wrap("float substraction"))
    return W_FloatObject(space, z)

StdObjSpace.sub.register(float_float_sub, W_FloatObject, W_FloatObject)

def float_float_mul(space, w_float1, w_float2):
    x = w_float1.floatval
    y = w_float2.floatval
    try:
        z = x * y
    except FloatingPointError:
        raise FailedToImplement(space.w_FloatingPointError, space.wrap("float multiplication"))
    return W_FloatObject(space, z)

StdObjSpace.mul.register(float_float_mul, W_FloatObject, W_FloatObject)

def float_float_div(space, w_float1, w_float2):
    x = w_float1.floatval
    y = w_float2.floatval
    try:
        z = x / y   # XXX make sure this is the new true division
    except FloatingPointError:
        raise FailedToImplement(space.w_FloatingPointError, space.wrap("float division"))
	# no overflow
    return W_FloatObject(space, z)

StdObjSpace.div.register(float_float_div, W_FloatObject, W_FloatObject)

def float_float_mod(space, w_float1, w_float2):
    x = w_float1.floatval
    y = w_float2.floatval
    if y == 0.0:
        raise FailedToImplement(space.w_ZeroDivisionError, space.wrap("float modulo"))
    try:
        # this is a hack!!!! must be replaced by a real fmod function
        mod = math.fmod(x,y)
        if (mod and ((y < 0.0) != (mod < 0.0))):
            mod += y
    except FloatingPointError:
        raise FailedToImplement(space.w_FloatingPointError, space.wrap("float division"))

    return W_FloatObject(space, mod)

StdObjSpace.mod.register(float_float_mod, W_FloatObject, W_FloatObject)

def float_float_divmod(space, w_float1, w_float2):
    x = w_float1.floatval
    y = w_float2.floatval
    if y == 0.0:
        raise FailedToImplement(space.w_ZeroDivisionError, space.wrap("float modulo"))
    try:
        # this is a hack!!!! must be replaced by a real fmod function
        mod = math.fmod(x,y)
        div = (x -mod) / y
        if (mod):
            if ((y < 0.0) != (mod < 0.0)):
                mod += y
                div -= -1.0
        else:
            mod *= mod
            if y < 0.0:
                mod = -mod
        if div:
            floordiv = math.floor(div)
            if (div - floordiv > 0.5):
                floordiv += 1.0
        else:
            div *= div;
            floordiv = div * x / y
    except FloatingPointError:
        raise FailedToImplement(space.w_FloatingPointError, space.wrap("float division"))

    return space.newtuple([W_FloatObject(space, floordiv),
                           W_FloatObject(space, mod)])

StdObjSpace.divmod.register(float_float_divmod, W_FloatObject, W_FloatObject)

def float_float_pow(space, w_float1,w_float2,thirdArg=None):
    if thirdArg is not None:
        raise FailedToImplement(space.w_TypeError,space.wrap("pow() 3rd argument not allowed unless all arguments are integers"))
    x = w_float1.floatval
    y = w_float2.floatval
    try:
        z = x ** y
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError, space.wrap("float power"))
    return W_FloatObject(space, z)

StdObjSpace.pow.register(float_float_pow, W_FloatObject, W_FloatObject)

def float_neg(space, w_float1):
    return W_FloatObject(space, w_float1.floatval)

StdObjSpace.neg.register(float_neg, W_FloatObject)

def float_pos(space, w_float):
    if w_float.__class__ == W_FloatObject:
        return w_float
    else:
        return W_FloatObject(space, w_float.floatval)

StdObjSpace.pos.register(float_pos, W_FloatObject)

def float_abs(space, w_float):
    return W_FloatObject(space, fabs(w_float.floatval))

StdObjSpace.abs.register(float_abs, W_FloatObject)

def float_nonzero(space, w_float):
    return w_float.floatval != 0.0

StdObjSpace.is_true.register(float_nonzero, W_FloatObject)

######## coersion must be done later
later = """
def float_coerce(space, w_float):
    if w_float.__class__ == W_FloatObject:
        return w_float
    else:
        return W_FloatObject(space, w_float.floatval)

StdObjSpace.coerce.register(float_coerce, W_FloatObject)
"""

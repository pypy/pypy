from pypy.objspace.std.objspace import *
from floattype import W_FloatType

##############################################################
# for the time being, all calls that are made to some external
# libraries in the floatobject.c, calls are made into the 
# python math library
##############################################################

import math
from intobject import W_IntObject

class W_FloatObject(W_Object):
    """This is a reimplementation of the CPython "PyFloatObject" 
       it is assumed that the constructor takes a real Python float as
       an argument"""
    statictype = W_FloatType
    
    def __init__(w_self, space, floatval):
        W_Object.__init__(w_self, space)
        w_self.floatval = floatval


registerimplementation(W_FloatObject)

# int-to-float delegation
def delegate__Int(space, w_intobj):
    return W_FloatObject(space, float(w_intobj.intval))
delegate__Int.result_class = W_FloatObject
delegate__Int.priority = PRIORITY_CHANGE_TYPE


def float__Float(space, w_value):
    return w_value

def int__Float(space, w_value):
    return space.newint(int(w_value.floatval))

def unwrap__Float(space, w_float):
    return w_float.floatval

def repr__Float(space, w_float):
    ## %reimplement%
    # uses CPython "repr" builtin function
    return space.wrap(repr(w_float.floatval))

def str__Float(space, w_float):
    ## %reimplement%
    # uses CPython "str" builtin function
    return space.wrap(str(w_float.floatval))

def lt__Float_Float(space, w_float1, w_float2):
    i = w_float1.floatval
    j = w_float2.floatval
    return space.newbool( i < j )

def le__Float_Float(space, w_float1, w_float2):
    i = w_float1.floatval
    j = w_float2.floatval
    return space.newbool( i <= j )

def eq__Float_Float(space, w_float1, w_float2):
    i = w_float1.floatval
    j = w_float2.floatval
    return space.newbool( i == j )

def ne__Float_Float(space, w_float1, w_float2):
    i = w_float1.floatval
    j = w_float2.floatval
    return space.newbool( i != j )

def gt__Float_Float(space, w_float1, w_float2):
    i = w_float1.floatval
    j = w_float2.floatval
    return space.newbool( i > j )

def ge__Float_Float(space, w_float1, w_float2):
    i = w_float1.floatval
    j = w_float2.floatval
    return space.newbool( i >= j )
    
def hash__Float(space,w_value):
    ## %reimplement%
    # real Implementation should be taken from _Py_HashDouble in object.c
    return space.wrap(hash(w_value.floatval))

def add__Float_Float(space, w_float1, w_float2):
    x = w_float1.floatval
    y = w_float2.floatval
    try:
        z = x + y
    except FloatingPointError:
        raise FailedToImplement(space.w_FloatingPointError, space.wrap("float addition"))
    return W_FloatObject(space, z)

def sub__Float_Float(space, w_float1, w_float2):
    x = w_float1.floatval
    y = w_float2.floatval
    try:
        z = x - y
    except FloatingPointError:
        raise FailedToImplement(space.w_FloatingPointError, space.wrap("float substraction"))
    return W_FloatObject(space, z)

def mul__Float_Float(space, w_float1, w_float2):
    x = w_float1.floatval
    y = w_float2.floatval
    try:
        z = x * y
    except FloatingPointError:
        raise FailedToImplement(space.w_FloatingPointError, space.wrap("float multiplication"))
    return W_FloatObject(space, z)

def div__Float_Float(space, w_float1, w_float2):
    x = w_float1.floatval
    y = w_float2.floatval
    try:
        z = x / y
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError, space.wrap("float division"))
    except FloatingPointError:
        raise FailedToImplement(space.w_FloatingPointError, space.wrap("float division"))
	# no overflow
    return W_FloatObject(space, z)

def floordiv__Float_Float(space, w_float1, w_float2):
    x = w_float1.floatval
    y = w_float2.floatval
    try:
        z = x // y
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError, space.wrap("float division"))
    except FloatingPointError:
        raise FailedToImplement(space.w_FloatingPointError, space.wrap("float division"))
	# no overflow
    return W_FloatObject(space, z)

def mod__Float_Float(space, w_float1, w_float2):
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

def divmod__Float_Float(space, w_float1, w_float2):
    x = w_float1.floatval
    y = w_float2.floatval
    if y == 0.0:
        raise FailedToImplement(space.w_ZeroDivisionError, space.wrap("float modulo"))
    try:
        # XXX this is a hack!!!! must be replaced by a real fmod function
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

def pow__Float_Float_ANY(space, w_float1, w_float2, thirdArg):
    if thirdArg is not space.w_None:
        raise FailedToImplement(space.w_TypeError,space.wrap("pow() 3rd argument not allowed unless all arguments are integers"))
    x = w_float1.floatval
    y = w_float2.floatval
    try:
        z = x ** y
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError, space.wrap("float power"))
    return W_FloatObject(space, z)

def neg__Float(space, w_float1):
    return W_FloatObject(space, w_float1.floatval)

def pos__Float(space, w_float):
    if w_float.__class__ == W_FloatObject:
        return w_float
    else:
        return W_FloatObject(space, w_float.floatval)

def abs__Float(space, w_float):
    return W_FloatObject(space, abs(w_float.floatval))

def is_true__Float(space, w_float):
    return w_float.floatval != 0.0

######## coersion must be done later
later = """
def float_coerce(space, w_float):
    if w_float.__class__ == W_FloatObject:
        return w_float
    else:
        return W_FloatObject(space, w_float.floatval)

StdObjSpace.coerce.register(float_coerce, W_FloatObject)
"""


register_all(vars())

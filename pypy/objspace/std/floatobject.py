from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway
from pypy.objspace.std.noneobject import W_NoneObject

##############################################################
# for the time being, all calls that are made to some external
# libraries in the floatobject.c, calls are made into the 
# python math library
##############################################################

import math
from pypy.objspace.std.intobject import W_IntObject

class W_FloatObject(W_Object):
    """This is a reimplementation of the CPython "PyFloatObject" 
       it is assumed that the constructor takes a real Python float as
       an argument"""
    from pypy.objspace.std.floattype import float_typedef as typedef
    
    def __init__(w_self, space, floatval):
        W_Object.__init__(w_self, space)
        w_self.floatval = floatval

    def unwrap(w_self):
        return w_self.floatval

    def __repr__(self):
        return "<W_FloatObject(%f)>" % self.floatval

registerimplementation(W_FloatObject)

# bool-to-float delegation
def delegate_Bool2Float(w_bool):
    return W_FloatObject(w_bool.space, float(w_bool.boolval))

# int-to-float delegation
def delegate_Int2Float(w_intobj):
    return W_FloatObject(w_intobj.space, float(w_intobj.intval))


# float__Float is supposed to do nothing, unless it has
# a derived float object, where it should return
# an exact one.
def float__Float(space, w_float1):
    if space.is_w(space.type(w_float1), space.w_float):
        return w_float1
    a = w_float1.floatval
    return W_FloatObject(space, a)

def int__Float(space, w_value):
    value = int(w_value.floatval)
    if isinstance(value, long):    # XXX cheating
        return space.long(w_value)
    return space.newint(value)

def float_w__Float(space, w_float):
    return w_float.floatval

app = gateway.applevel(''' 
    def repr__Float(f):
        r = "%.17g"%f
        for c in r:
            if c not in '-0123456789':
                return r
        else:
            return r + '.0'    

    def str__Float(f):
        r = "%.12g"%f
        for c in r:
            if c not in '-0123456789':
                return r
        else:
            return r + '.0'    
''', filename=__file__) 
repr__Float = app.interphook('repr__Float') 
str__Float = app.interphook('str__Float') 

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

# coerce
def coerce__Float_Float(space, w_float1, w_float2):
    return space.newtuple([w_float1, w_float2])


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

truediv__Float_Float = div__Float_Float

# avoid space.getitem for a basic operation
##def floordiv__Float_Float(space, w_float1, w_float2):
##    w_t = divmod__Float_Float(space, w_float1, w_float2)
##    return space.getitem(w_t, space.wrap(0))

def floordiv__Float_Float(space, w_float1, w_float2):
    w_div, w_mod = _divmod_w(space, w_float1, w_float2)
    return w_div

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

def _divmod_w(space, w_float1, w_float2):
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
                div -= 1.0
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

    return [W_FloatObject(space, floordiv), W_FloatObject(space, mod)]

def divmod__Float_Float(space, w_float1, w_float2):
    return space.newtuple(_divmod_w(space, w_float1, w_float2))

def pow__Float_Float_ANY(space, w_float1, w_float2, thirdArg):
    if not space.is_w(thirdArg, space.w_None):
        raise FailedToImplement(space.w_TypeError, space.wrap("pow() 3rd argument not allowed unless all arguments are integers"))
    x = w_float1.floatval
    y = w_float2.floatval
    try:
        z = x ** y
    except OverflowError:
        raise FailedToImplement(space.w_OverflowError, space.wrap("float power"))
    except ValueError, e:
        raise FailedToImplement(space.w_ValueError, space.wrap(str(e)))
    except ZeroDivisionError, e:   # (0.0 ** -1)
        raise OperationError(space.w_ZeroDivisionError, space.wrap(str(e)))

    return W_FloatObject(space, z)

def neg__Float(space, w_float1):
    return W_FloatObject(space, -w_float1.floatval)

def pos__Float(space, w_float):
    return float__Float(space, w_float)

def abs__Float(space, w_float):
    return W_FloatObject(space, abs(w_float.floatval))

def nonzero__Float(space, w_float):
    return space.newbool(w_float.floatval != 0.0)

######## coersion must be done later
later = """
def float_coerce(space, w_float):
    if w_float.__class__ == W_FloatObject:
        return w_float
    else:
        return W_FloatObject(space, w_float.floatval)

StdObjSpace.coerce.register(float_coerce, W_FloatObject)
"""

def getnewargs__Float(space, w_float):
    return space.newtuple([W_FloatObject(space, w_float.floatval)])

register_all(vars())

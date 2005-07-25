from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.rpython.rarithmetic import ovfcheck_float_to_int

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
        r = "%.17g" % f
        for c in r:
            if c not in '-0123456789':
                return r
        else:
            return r + '.0'    

    def str__Float(f):
        r = "%.12g" % f
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

def hash__Float(space, w_value):
    return space.wrap(_hash_float(space, w_value.floatval))

def _hash_float(space, v):
    from pypy.objspace.std.longobject import _FromDouble, _hash as _hashlong

    # This is designed so that Python numbers of different types
    # that compare equal hash to the same value; otherwise comparisons
    # of mapping keys will turn out weird.
    fractpart, intpart = math.modf(v)

    if fractpart == 0.0:
        # This must return the same hash as an equal int or long.
        try:
            x = ovfcheck_float_to_int(intpart)
            # Fits in a C long == a Python int, so is its own hash.
            return x
        except OverflowError:
            # Convert to long and use its hash.
            try:
                w_lval = _FromDouble(space, v)
            except OverflowError:
                # can't convert to long int -- arbitrary
                if v < 0:
                    return -271828
                else:
                    return 314159
            return _hashlong(w_lval)

    # The fractional part is non-zero, so we don't have to worry about
    # making this match the hash of some other type.
    # Use frexp to get at the bits in the double.
    # Since the VAX D double format has 56 mantissa bits, which is the
    # most of any double format in use, each of these parts may have as
    # many as (but no more than) 56 significant bits.
    # So, assuming sizeof(long) >= 4, each part can be broken into two
    # longs; frexp and multiplication are used to do that.
    # Also, since the Cray double format has 15 exponent bits, which is
    # the most of any double format in use, shifting the exponent field
    # left by 15 won't overflow a long (again assuming sizeof(long) >= 4).

    v, expo = math.frexp(v)
    v *= 2147483648.0  # 2**31
    hipart = int(v)    # take the top 32 bits
    v = (v - hipart) * 2147483648.0 # get the next 32 bits
    x = hipart + int(v) + (expo << 15)
    return x


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
        mod = math.fmod(x, y)
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
        mod = math.fmod(x, y)
        # fmod is typically exact, so vx-mod is *mathematically* an
        # exact multiple of wx.  But this is fp arithmetic, and fp
        # vx - mod is an approximation; the result is that div may
        # not be an exact integral value after the division, although
        # it will always be very close to one.
        div = (x - mod) / y
        if (mod):
            # ensure the remainder has the same sign as the denominator
            if ((y < 0.0) != (mod < 0.0)):
                mod += y
                div -= 1.0
        else:
            # the remainder is zero, and in the presence of signed zeroes
            # fmod returns different results across platforms; ensure
            # it has the same sign as the denominator; we'd like to do
            # "mod = wx * 0.0", but that may get optimized away
            mod *= mod  # hide "mod = +0" from optimizer
            if y < 0.0:
                mod = -mod
        # snap quotient to nearest integral value
        if div:
            floordiv = math.floor(div)
            if (div - floordiv > 0.5):
                floordiv += 1.0
        else:
            # div is zero - get the same sign as the true quotient
            div *= div  # hide "div = +0" from optimizers
            floordiv = div * x / y  # zero w/ sign of vx/wx
    except FloatingPointError:
        raise FailedToImplement(space.w_FloatingPointError, space.wrap("float division"))

    return [W_FloatObject(space, floordiv), W_FloatObject(space, mod)]

def divmod__Float_Float(space, w_float1, w_float2):
    return space.newtuple(_divmod_w(space, w_float1, w_float2))

def pow__Float_Float_ANY(space, w_float1, w_float2, thirdArg):
    if not space.is_w(thirdArg, space.w_None):
        raise FailedToImplement(space.w_TypeError, space.wrap(
            "pow() 3rd argument not allowed unless all arguments are integers"))
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

######## coercion must be done later
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

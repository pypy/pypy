from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.longobject import W_LongObject
from pypy.rlib.rarithmetic import ovfcheck_float_to_int, intmask, isinf
from pypy.rlib.rarithmetic import formatd

import math
from pypy.objspace.std.intobject import W_IntObject

class W_FloatObject(W_Object):
    """This is a reimplementation of the CPython "PyFloatObject" 
       it is assumed that the constructor takes a real Python float as
       an argument"""
    from pypy.objspace.std.floattype import float_typedef as typedef
    
    def __init__(w_self, floatval):
        w_self.floatval = floatval

    def unwrap(w_self, space):
        return w_self.floatval

    def __repr__(self):
        return "<W_FloatObject(%f)>" % self.floatval

registerimplementation(W_FloatObject)

# bool-to-float delegation
def delegate_Bool2Float(space, w_bool):
    return W_FloatObject(float(w_bool.boolval))

# int-to-float delegation
def delegate_Int2Float(space, w_intobj):
    return W_FloatObject(float(w_intobj.intval))

# long-to-float delegation
def delegate_Long2Float(space, w_longobj):
    try:
        return W_FloatObject(w_longobj.tofloat())
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("long int too large to convert to float"))


# float__Float is supposed to do nothing, unless it has
# a derived float object, where it should return
# an exact one.
def float__Float(space, w_float1):
    if space.is_w(space.type(w_float1), space.w_float):
        return w_float1
    a = w_float1.floatval
    return W_FloatObject(a)

def int__Float(space, w_value):
    try:
        value = ovfcheck_float_to_int(w_value.floatval)
    except OverflowError:
        return space.long(w_value)
    else:
        return space.newint(value)

def long__Float(space, w_floatobj):
    try:
        return W_LongObject.fromfloat(w_floatobj.floatval)
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("cannot convert float infinity to long"))

def float_w__Float(space, w_float):
    return w_float.floatval

def should_not_look_like_an_int(s):
    for c in s:
        if c in '.eE':
            break
    else:
        s += '.0'
    return s

def repr__Float(space, w_float):
    x = w_float.floatval
    s = formatd("%.17g", x)
    return space.wrap(should_not_look_like_an_int(s))

def str__Float(space, w_float):
    x = w_float.floatval
    s = formatd("%.12g", x)
    return space.wrap(should_not_look_like_an_int(s))


def declare_new_float_comparison(opname):
    import operator
    from pypy.tool.sourcetools import func_with_new_name
    op = getattr(operator, opname)
    def f(space, w_int1, w_int2):
        i = w_int1.floatval
        j = w_int2.floatval
        return space.newbool(op(i, j))
    name = opname + "__Float_Float"
    return func_with_new_name(f, name), name

def declare_new_int_float_comparison(opname):
    import operator
    from pypy.tool.sourcetools import func_with_new_name
    op = getattr(operator, opname)
    def f(space, w_int1, w_float2):
        i = w_int1.intval
        j = w_float2.floatval
        return space.newbool(op(float(i), j))
    name = opname + "__Int_Float"
    return func_with_new_name(f, name), name

def declare_new_float_int_comparison(opname):
    import operator
    from pypy.tool.sourcetools import func_with_new_name
    op = getattr(operator, opname)
    def f(space, w_float1, w_int2):
        i = w_float1.floatval
        j = w_int2.intval
        return space.newbool(op(i, float(j)))
    name = opname + "__Float_Int"
    return func_with_new_name(f, name), name

for op in ['lt', 'le', 'eq', 'ne', 'gt', 'ge']:
    func, name = declare_new_float_comparison(op)
    globals()[name] = func
    # XXX shortcuts disabled: see r54171 and issue #384.
    #func, name = declare_new_int_float_comparison(op)
    #globals()[name] = func
    #func, name = declare_new_float_int_comparison(op)
    #globals()[name] = func

# for overflowing comparisons between longs and floats
# XXX we might have to worry (later) about eq__Float_Int, for the case
#     where int->float conversion may lose precision :-(
def eq__Float_Long(space, w_float1, w_long2):
    # XXX naive implementation
    x = w_float1.floatval
    if isinf(x) or math.floor(x) != x:
        return space.w_False
    try:
        w_long1 = W_LongObject.fromfloat(x)
    except OverflowError:
        return space.w_False
    return space.eq(w_long1, w_long2)

def eq__Long_Float(space, w_long1, w_float2):
    return eq__Float_Long(space, w_float2, w_long1)

def ne__Float_Long(space, w_float1, w_long2):
    return space.not_(eq__Float_Long(space, w_float1, w_long2))

def ne__Long_Float(space, w_long1, w_float2):
    return space.not_(eq__Float_Long(space, w_float2, w_long1))

def lt__Float_Long(space, w_float1, w_long2):
    # XXX naive implementation
    x = w_float1.floatval
    if isinf(x):
        return space.newbool(x < 0.0)
    x_floor = math.floor(x)
    try:
        w_long1 = W_LongObject.fromfloat(x_floor)
    except OverflowError:
        return space.newbool(x < 0.0)
    return space.lt(w_long1, w_long2)

def lt__Long_Float(space, w_long1, w_float2):
    return space.not_(le__Float_Long(space, w_float2, w_long1))

def le__Float_Long(space, w_float1, w_long2):
    # XXX it's naive anyway
    if space.is_true(space.lt(w_float1, w_long2)):
        return space.w_True
    else:
        return space.eq(w_float1, w_long2)

def le__Long_Float(space, w_long1, w_float2):
    return space.not_(lt__Float_Long(space, w_float2, w_long1))

def gt__Float_Long(space, w_float1, w_long2):
    return space.not_(le__Float_Long(space, w_float1, w_long2))

def gt__Long_Float(space, w_long1, w_float2):
    return lt__Float_Long(space, w_float2, w_long1)

def ge__Float_Long(space, w_float1, w_long2):
    return space.not_(lt__Float_Long(space, w_float1, w_long2))

def ge__Long_Float(space, w_long1, w_float2):
    return le__Float_Long(space, w_float2, w_long1)


def hash__Float(space, w_value):
    return space.wrap(_hash_float(space, w_value.floatval))

def _hash_float(space, v):
    from pypy.objspace.std.longobject import hash__Long

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
                w_lval = W_LongObject.fromfloat(v)
            except OverflowError:
                # can't convert to long int -- arbitrary
                if v < 0:
                    return -271828
                else:
                    return 314159
            return space.int_w(hash__Long(space, w_lval))

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
    x = intmask(hipart + int(v) + (expo << 15))
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
    return W_FloatObject(z)

def sub__Float_Float(space, w_float1, w_float2):
    x = w_float1.floatval
    y = w_float2.floatval
    try:
        z = x - y
    except FloatingPointError:
        raise FailedToImplement(space.w_FloatingPointError, space.wrap("float substraction"))
    return W_FloatObject(z)

def mul__Float_Float(space, w_float1, w_float2):
    x = w_float1.floatval
    y = w_float2.floatval
    try:
        z = x * y
    except FloatingPointError:
        raise FailedToImplement(space.w_FloatingPointError, space.wrap("float multiplication"))
    return W_FloatObject(z)

def div__Float_Float(space, w_float1, w_float2):
    x = w_float1.floatval
    y = w_float2.floatval
    if y == 0.0:
        raise FailedToImplement(space.w_ZeroDivisionError, space.wrap("float division"))    
    try:
        z = x / y
    except FloatingPointError:
        raise FailedToImplement(space.w_FloatingPointError, space.wrap("float division"))
    # no overflow
    return W_FloatObject(z)

truediv__Float_Float = div__Float_Float

def floordiv__Float_Float(space, w_float1, w_float2):
    w_div, w_mod = _divmod_w(space, w_float1, w_float2)
    return w_div

def mod__Float_Float(space, w_float1, w_float2):
    x = w_float1.floatval
    y = w_float2.floatval
    if y == 0.0:
        raise FailedToImplement(space.w_ZeroDivisionError, space.wrap("float modulo"))
    try:
        mod = math.fmod(x, y)
        if (mod and ((y < 0.0) != (mod < 0.0))):
            mod += y
    except FloatingPointError:
        raise FailedToImplement(space.w_FloatingPointError, space.wrap("float division"))

    return W_FloatObject(mod)

def _divmod_w(space, w_float1, w_float2):
    x = w_float1.floatval
    y = w_float2.floatval
    if y == 0.0:
        raise FailedToImplement(space.w_ZeroDivisionError, space.wrap("float modulo"))
    try:
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

    return [W_FloatObject(floordiv), W_FloatObject(mod)]

def divmod__Float_Float(space, w_float1, w_float2):
    return space.newtuple(_divmod_w(space, w_float1, w_float2))

def pow__Float_Float_ANY(space, w_float1, w_float2, thirdArg):
    # XXX it makes sense to do more here than in the backend
    # about sorting out errors!

    # This raises FailedToImplement in cases like overflow where a
    # (purely theoretical) big-precision float implementation would have
    # a chance to give a result, and directly OperationError for errors
    # that we want to force to be reported to the user.
    if not space.is_w(thirdArg, space.w_None):
        raise OperationError(space.w_TypeError, space.wrap(
            "pow() 3rd argument not allowed unless all arguments are integers"))
    x = w_float1.floatval
    y = w_float2.floatval
    z = 1.0
    if y == 0.0:
        z = 1.0
    elif x == 0.0:
        if y < 0.0:
            raise OperationError(space.w_ZeroDivisionError,
                                    space.wrap("0.0 cannot be raised to a negative power"))
        z = 0.0
    else:
        if x < 0.0:
            if math.floor(y) != y:
                raise OperationError(space.w_ValueError,
                                        space.wrap("negative number "
                                                   "cannot be raised to a fractional power"))
            if x == -1.0:
                # xxx what if y is infinity or a NaN
                if math.floor(y * 0.5) * 2.0 == y:
                    return space.wrap(1.0)
                else:
                    return space.wrap( -1.0)
#        else:
        try:
            z = math.pow(x,y)
        except OverflowError:
            raise FailedToImplement(space.w_OverflowError, space.wrap("float power"))
        except ValueError:
            raise FailedToImplement(space.w_ValueError, space.wrap("float power")) # xxx

    return W_FloatObject(z)


def neg__Float(space, w_float1):
    return W_FloatObject(-w_float1.floatval)

def pos__Float(space, w_float):
    return float__Float(space, w_float)

def abs__Float(space, w_float):
    return W_FloatObject(abs(w_float.floatval))

def nonzero__Float(space, w_float):
    return space.newbool(w_float.floatval != 0.0)

def getnewargs__Float(space, w_float):
    return space.newtuple([W_FloatObject(w_float.floatval)])

register_all(vars())

# pow delegation for negative 2nd arg
def pow_neg__Long_Long_None(space, w_int1, w_int2, thirdarg):
    w_float1 = delegate_Long2Float(space, w_int1)
    w_float2 = delegate_Long2Float(space, w_int2)
    return pow__Float_Float_ANY(space, w_float1, w_float2, thirdarg)

StdObjSpace.MM.pow.register(pow_neg__Long_Long_None, W_LongObject, W_LongObject, W_NoneObject, order=1)

def pow_neg__Int_Int_None(space, w_int1, w_int2, thirdarg):
    w_float1 = delegate_Int2Float(space, w_int1)
    w_float2 = delegate_Int2Float(space, w_int2)
    return pow__Float_Float_ANY(space, w_float1, w_float2, thirdarg)

StdObjSpace.MM.pow.register(pow_neg__Int_Int_None, W_IntObject, W_IntObject, W_NoneObject, order=2)

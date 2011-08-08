import math

from pypy.module.micronumpy.interp_support import Signature
from pypy.rlib import rfloat
from pypy.tool.sourcetools import func_with_new_name

def ufunc(func):
    signature = Signature()
    def impl(space, w_obj):
        from pypy.module.micronumpy.interp_numarray import Call1, convert_to_array
        if space.issequence_w(w_obj):
            w_obj_arr = convert_to_array(space, w_obj)
            w_res = Call1(func, w_obj_arr, w_obj_arr.signature.transition(signature))
            w_obj_arr.invalidates.append(w_res)
            return w_res
        else:
            return space.wrap(func(space.float_w(w_obj)))
    return func_with_new_name(impl, "%s_dispatcher" % func.__name__)

def ufunc2(func):
    signature = Signature()
    def impl(space, w_lhs, w_rhs):
        from pypy.module.micronumpy.interp_numarray import Call2, convert_to_array
        if space.issequence_w(w_lhs) or space.issequence_w(w_rhs):
            w_lhs_arr = convert_to_array(space, w_lhs)
            w_rhs_arr = convert_to_array(space, w_rhs)
            new_sig = w_lhs_arr.signature.transition(signature).transition(w_rhs_arr.signature)
            w_res = Call2(func, w_lhs_arr, w_rhs_arr, new_sig)
            w_lhs_arr.invalidates.append(w_res)
            w_rhs_arr.invalidates.append(w_res)
            return w_res
        else:
            return space.wrap(func(space.float_w(w_lhs), space.float_w(w_rhs)))
    return func_with_new_name(impl, "%s_dispatcher" % func.__name__)

@ufunc
def absolute(value):
    return abs(value)

@ufunc2
def add(lvalue, rvalue):
    return lvalue + rvalue

@ufunc2
def copysign(lvalue, rvalue):
    return rfloat.copysign(lvalue, rvalue)

@ufunc2
def divide(lvalue, rvalue):
    return lvalue / rvalue

@ufunc
def exp(value):
    try:
        return math.exp(value)
    except OverflowError:
        return rfloat.INFINITY

@ufunc
def fabs(value):
    return math.fabs(value)

@ufunc2
def maximum(lvalue, rvalue):
    return max(lvalue, rvalue)

@ufunc2
def minimum(lvalue, rvalue):
    return min(lvalue, rvalue)

@ufunc2
def multiply(lvalue, rvalue):
    return lvalue * rvalue

# Used by numarray for __pos__. Not visible from numpy application space.
@ufunc
def positive(value):
    return value

@ufunc
def negative(value):
    return -value

@ufunc
def reciprocal(value):
    if value == 0.0:
        return rfloat.copysign(rfloat.INFINITY, value)
    return 1.0 / value

@ufunc2
def subtract(lvalue, rvalue):
    return lvalue - rvalue

@ufunc
def floor(value):
    return math.floor(value)

@ufunc
def sign(value):
    if value == 0.0:
        return 0.0
    return rfloat.copysign(1.0, value)

@ufunc
def sin(value):
    return math.sin(value)

@ufunc
def cos(value):
    return math.cos(value)

@ufunc
def tan(value):
    return math.tan(value)

@ufunc2
def power(lvalue, rvalue):
    return math.pow(lvalue, rvalue)

@ufunc2
def mod(lvalue, rvalue):
    return math.fmod(lvalue, rvalue)


@ufunc
def arcsin(value):
    if value < -1.0 or  value > 1.0:
        return rfloat.NAN
    return math.asin(value)

@ufunc
def arccos(value):
    if value < -1.0 or  value > 1.0:
        return rfloat.NAN
    return math.acos(value)

@ufunc
def arctan(value):
    return math.atan(value)

import math

from pypy.module.micronumpy.interp_numarray import (Call1, Call2, Signature,
    convert_to_array)
from pypy.rlib import rfloat
from pypy.tool.sourcetools import func_with_new_name

def ufunc(func):
    signature = Signature()
    def impl(space, w_obj):
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
def copysign(lvalue, rvalue):
    return rfloat.copysign(lvalue, rvalue)

@ufunc
def exp(value):
    try:
        return math.exp(value)
    except OverflowError:
        return rfloat.INFINITY

@ufunc2
def maximum(lvalue, rvalue):
    return max(lvalue, rvalue)

@ufunc2
def minimum(lvalue, rvalue):
    return min(lvalue, rvalue)

@ufunc
def negative(value):
    return -value

@ufunc
def reciprocal(value):
    if value == 0.0:
        return rfloat.copysign(rfloat.INFINITY, value)
    return 1.0 / value

@ufunc
def floor(value):
    return math.floor(value)

@ufunc
def sign(value):
    if value == 0.0:
        return 0.0
    return rfloat.copysign(1.0, value)

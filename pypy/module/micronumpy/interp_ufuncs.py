import math

from pypy.interpreter.gateway import unwrap_spec
from pypy.module.micronumpy.interp_numarray import BaseArray, Call1, Call2, Signature, access_as_array
from pypy.rlib import rfloat
from pypy.tool.sourcetools import func_with_new_name

def _issequence(space, w_obj):
    # Copied from cpyext's PySequence_Check
    """Return True if the object provides sequence protocol, and False otherwise.
    This function always succeeds."""
    return (space.findattr(w_obj, space.wrap("__getitem__")) is not None)

def ufunc(func):
    signature = Signature()
    def impl(space, w_obj):
        if isinstance(w_obj, BaseArray):
            w_res = Call1(func, w_obj, w_obj.signature.transition(signature))
            w_obj.invalidates.append(w_res)
            return w_res
        elif _issequence(space, w_obj):
            w_obj_arr = access_as_array(space, w_obj)
            w_res = Call1(func, w_obj_arr, w_obj_arr.signature.transition(signature))
            return w_res
        else:
            return space.wrap(func(space.float_w(w_obj)))
    return func_with_new_name(impl, "%s_dispatcher" % func.__name__)

def ufunc2(func):
    signature = Signature()
    def impl(space, w_lhs, w_rhs):
        lhs_is_array = isinstance(w_lhs, BaseArray)
        rhs_is_array = isinstance(w_rhs, BaseArray)
        if lhs_is_array and rhs_is_array:
            # This is the (most likely) fall-through case in conversion checks
            # Not sure if making it a special case makes it much faster
            new_sig = w_lhs.signature.transition(signature).transition(w_rhs.signature)
            w_res = Call2(func, w_lhs, w_rhs, new_sig)
            w_lhs.invalidates.append(w_res)
            w_rhs.invalidates.append(w_res)
            return w_res
        elif _issequence(space, w_lhs) or _issequence(space, w_rhs):
            if lhs_is_array:
                w_lhs_arr = w_lhs
            else:
                w_lhs_arr = access_as_array(space, w_lhs)
            if rhs_is_array:
                w_rhs_arr = w_rhs
            else:
                w_rhs_arr = access_as_array(space, w_rhs)
            new_sig = w_lhs_arr.signature.transition(signature).transition(w_rhs_arr.signature)
            w_res = Call2(func, w_lhs_arr, w_rhs_arr, new_sig)
            if lhs_is_array:
                w_lhs_arr.invalidates.append(w_res)
            if rhs_is_array:
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
def sign(value):
    if value == 0.0:
        return 0.0
    return rfloat.copysign(1.0, value)

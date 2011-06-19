import math

from pypy.interpreter.gateway import unwrap_spec
from pypy.module.micronumpy.interp_numarray import BaseArray, Call1, Call2, Signature
from pypy.rlib import rfloat
from pypy.tool.sourcetools import func_with_new_name


def ufunc(func):
    signature = Signature()
    def impl(space, w_obj):
        if isinstance(w_obj, BaseArray):
            w_res = Call1(func, w_obj, w_obj.signature.transition(signature))
            w_obj.invalidates.append(w_res)
            return w_res
        return space.wrap(func(space.float_w(w_obj)))
    return func_with_new_name(impl, "%s_dispatcher" % func.__name__)

def ufunc2(func):
    signature = Signature()
    def impl(space, w_lhs, w_rhs):
        if isinstance(w_lhs, BaseArray) and isinstance(w_rhs, BaseArray):
            new_sig = w_lhs.signature.transition(signature).transition(w_rhs.signature)
            w_res = Call2(func, w_lhs, w_rhs, new_sig)
            w_lhs.invalidates.append(w_res)
            w_rhs.invalidates.append(w_res)
            return w_res
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

import math

from pypy.module.micronumpy import interp_dtype
from pypy.module.micronumpy.interp_support import Signature
from pypy.rlib import rfloat
from pypy.tool.sourcetools import func_with_new_name


def ufunc(func):
    signature = Signature()
    def impl(space, w_obj):
        from pypy.module.micronumpy.interp_numarray import Call1, convert_to_array, scalar
        if space.issequence_w(w_obj):
            w_obj_arr = convert_to_array(space, w_obj)
            w_res = Call1(func, w_obj_arr, w_obj_arr.signature.transition(signature))
            w_obj_arr.invalidates.append(w_res)
            return w_res
        else:
            return func(scalar(interp_dtype.W_Float64_Dtype, w_obj)).wrap(space)
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

def ufunc_dtype_caller(ufunc_name, op_name, argcount):
    if argcount == 1:
        @ufunc
        def impl(res_dtype, value):
            return getattr(res_dtype, op_name)(value)
    elif argcount == 2:
        @ufunc2
        def impl(res_dtype, lvalue, rvalue):
            return getattr(res_dtype, op_name)(lvalue, rvalue)
    impl.__name__ = ufunc_name
    return impl

for ufunc_name, op_name, argcount in [
    ("add", "add", 2),
    ("subtract", "sub", 2),
    ("multiply", "mul", 2),
    ("divide", "div", 2),
    ("mod", "mod", 2),
    ("power", "pow", 2),
    ("negative", "neg", 1),
    ("positive", "pos", 1),
    ("absolute", "abs", 1),
]:
    globals()[ufunc_name] = ufunc_dtype_caller(ufunc_name, op_name, argcount)

@ufunc2
def copysign(lvalue, rvalue):
    return rfloat.copysign(lvalue, rvalue)


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

@ufunc
def sin(value):
    return math.sin(value)

@ufunc
def cos(value):
    return math.cos(value)

@ufunc
def tan(value):
    return math.tan(value)



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

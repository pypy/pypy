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
            res_dtype = space.fromcache(interp_dtype.W_Float64Dtype)
            return func(res_dtype, scalar(space, interp_dtype.W_Float64Dtype, w_obj)).wrap(space)
    return func_with_new_name(impl, "%s_dispatcher" % func.__name__)

def ufunc2(func):
    signature = Signature()
    def impl(space, w_lhs, w_rhs):
        from pypy.module.micronumpy.interp_numarray import Call2, convert_to_array, scalar
        if space.issequence_w(w_lhs) or space.issequence_w(w_rhs):
            w_lhs_arr = convert_to_array(space, w_lhs)
            w_rhs_arr = convert_to_array(space, w_rhs)
            new_sig = w_lhs_arr.signature.transition(signature).transition(w_rhs_arr.signature)
            w_res = Call2(func, w_lhs_arr, w_rhs_arr, new_sig)
            w_lhs_arr.invalidates.append(w_res)
            w_rhs_arr.invalidates.append(w_res)
            return w_res
        else:
            res_dtype = space.fromcache(interp_dtype.W_Float64Dtype)
            return func(
                res_dtype,
                scalar(space, interp_dtype.W_Float64Dtype, w_lhs),
                scalar(space, interp_dtype.W_Float64Dtype, w_rhs),
            ).wrap(space)
    return func_with_new_name(impl, "%s_dispatcher" % func.__name__)

def find_binop_result_dtype(space, dt1, dt2, promote_bools=False):
    # dt1.num should be <= dt2.num
    if dt1.num > dt2.num:
        dt1, dt2 = dt2, dt1
    # Some operations promote op(bool, bool) to return int8, rather than bool
    if promote_bools and (dt1.kind == dt2.kind == interp_dtype.BOOLLTR):
        return space.fromcache(interp_dtype.W_Int8Dtype)
    # If they're the same kind, choose the greater one.
    if dt1.kind == dt2.kind:
        return dt2

    # Everything promotes to float, and bool promotes to everything.
    if dt2.kind == interp_dtype.FLOATINGLTR or dt1.kind == interp_dtype.BOOLLTR:
        return dt2


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

    ("maximum", "max", 2),
    ("minimum", "min", 2),

    ("copysign", "copysign", 2),

    ("negative", "neg", 1),
    ("positive", "pos", 1),
    ("absolute", "abs", 1),
    ("sign", "sign", 1),
    ("fabs", "fabs", 1),
    ("reciprocal", "reciprocal", 1),
    ("floor", "floor", 1),

    ("exp", "exp", 1),
    ("sin", "sin", 1),
    ("cos", "cos", 1),
    ("tan", "tan", 1),
    ("arcsin", "arcsin", 1),
    ("arccos", "arccos", 1),
    ("arctan", "arctan", 1),
]:
    globals()[ufunc_name] = ufunc_dtype_caller(ufunc_name, op_name, argcount)
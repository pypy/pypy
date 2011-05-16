from pypy.interpreter.gateway import unwrap_spec
from pypy.module.micronumpy.interp_numarray import BaseArray, Call1, Call2, Signature
from pypy.tool.sourcetools import func_with_new_name


def ufunc(func):
    signature = Signature()
    @unwrap_spec(array=BaseArray)
    def impl(space, array):
        w_res = Call1(func, array, array.signature.transition(signature))
        array.invalidates.append(w_res)
        return w_res
    return func_with_new_name(impl, "%s_dispatcher" % func.__name__)

def ufunc2(func):
    signature = Signature()
    @unwrap_spec(larray=BaseArray, rarray=BaseArray)
    def impl(space, larray, rarray):
        new_sig = larray.signature.transition(signature)
        w_res = Call2(func, larray, rarray, rarray.signature.transition(new_sig))
        larray.invalidates.append(w_res)
        rarray.invalidates.append(w_res)
        return w_res
    return func_with_new_name(impl, "%s_dispatcher" % func.__name__)

@ufunc
def negative(value):
    return -value

@ufunc
def absolute(value):
    return abs(value)

@ufunc2
def minimum(lvalue, rvalue):
    return min(lvalue, rvalue)

@ufunc2
def maximum(lvalue, rvalue):
    return max(lvalue, rvalue)

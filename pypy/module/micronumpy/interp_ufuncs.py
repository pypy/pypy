from pypy.interpreter.gateway import unwrap_spec
from pypy.module.micronumpy.interp_numarray import BaseArray, Call1, Signature
from pypy.tool.sourcetools import func_with_new_name


def ufunc(func):
    signature = Signature()
    @unwrap_spec(array=BaseArray)
    def impl(space, array):
        w_res = Call1(func, array, array.signature.transition(signature))
        array.invalidates.append(w_res)
        return w_res
    return func_with_new_name(impl, "%s_dispatcher" % func.__name__)

@ufunc
def negative(value):
    return -value

@ufunc
def absolute(value):
    return abs(value)
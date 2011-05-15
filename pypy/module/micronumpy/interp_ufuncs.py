from pypy.interpreter.gateway import unwrap_spec
from pypy.module.micronumpy.interp_numarray import BaseArray, Call
from pypy.tool.sourcetools import func_with_new_name


def ufunc(func):
    @unwrap_spec(array=BaseArray)
    def impl(space, array):
        w_res = Call(func, array)
        array.invalidates.append(w_res)
        return w_res
    return func_with_new_name(impl, "%s_dispatcher" % func.__name__)

@ufunc
def negative(value):
    return -value

@ufunc
def npabs(value):
    return abs(value)
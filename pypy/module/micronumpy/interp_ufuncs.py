from pypy.interpreter.gateway import unwrap_spec
from pypy.module.micronumpy.interp_numarray import BaseArray, Call


def negative_impl(value):
    return -value

@unwrap_spec(array=BaseArray)
def negative(space, array):
    return Call(negative_impl, array)
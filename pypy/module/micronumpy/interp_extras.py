from pypy.interpreter.gateway import unwrap_spec
from pypy.module.micronumpy.interp_numarray import BaseArray


@unwrap_spec(array=BaseArray)
def debug_repr(space, array):
    return space.wrap(array.find_sig().debug_repr())

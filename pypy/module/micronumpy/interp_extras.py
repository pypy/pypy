from pypy.interpreter.gateway import unwrap_spec
from pypy.module.micronumpy.interp_numarray import BaseArray


@unwrap_spec(array=BaseArray)
def debug_repr(space, array):
    return space.wrap(array.find_sig().debug_repr())

@unwrap_spec(array=BaseArray)
def remove_invalidates(space, array):
    """ Array modification will no longer invalidate any of it's
    potential children. Use only for performance debugging
    """
    del array.invalidates[:]
    return space.w_None

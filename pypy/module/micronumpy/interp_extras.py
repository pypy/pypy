from pypy.interpreter.gateway import unwrap_spec
from pypy.module.micronumpy.interp_numarray import BaseArray, get_numarray_cache


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

@unwrap_spec(arg=bool)
def set_invalidation(space, arg):
    get_numarray_cache(space).enable_invalidation = arg

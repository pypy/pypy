from pypy.rlib import jit


@jit.unroll_safe
def product(s):
    i = 1
    for x in s:
        i *= x
    return i

def convert_to_array(space, w_obj):
    from pypy.module.micronumpy.interp_numarray import W_NDimArray, array,\
         scalar_w
    from pypy.module.micronumpy import interp_ufuncs
    
    if isinstance(w_obj, W_NDimArray):
        return w_obj
    elif space.issequence_w(w_obj):
        # Convert to array.
        return array(space, w_obj, w_order=None)
    else:
        # If it's a scalar
        dtype = interp_ufuncs.find_dtype_for_scalar(space, w_obj)
        return scalar_w(space, dtype, w_obj)

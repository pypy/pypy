"""
Interp-level definition of frequently used functionals.

Candidates      implemented

  range             yes
  zip               no
  min               no
  max               no
  enumerate         no
  xrange            no

"""

from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace, W_Root, NoneNotWrapped, applevel
from pypy.rlib.rarithmetic import r_uint, intmask
from pypy.module.__builtin__.app_functional import range as app_range
from inspect import getsource, getfile

"""
Implementation of the common integer case of range. Instead of handling
all other cases here, too, we fall back to the applevel implementation
for non-integer arguments.
Ideally this implementation could be saved, if we were able to
specialize the geninterp generated code. But I guess having this
hand-optimized is a good idea.

Note the fun of using range inside range :-)
"""

def get_len_of_range(lo, hi, step):
    """
    Return number of items in range/xrange (lo, hi, step).  step > 0
    required.  Return a value < 0 if & only if the true value is too
    large to fit in a signed long.
    """

    # If lo >= hi, the range is empty.
    # Else if n values are in the range, the last one is
    # lo + (n-1)*step, which must be <= hi-1.  Rearranging,
    # n <= (hi - lo - 1)/step + 1, so taking the floor of the RHS gives
    # the proper value.  Since lo < hi in this case, hi-lo-1 >= 0, so
    # the RHS is non-negative and so truncation is the same as the
    # floor.  Letting M be the largest positive long, the worst case
    # for the RHS numerator is hi=M, lo=-M-1, and then
    # hi-lo-1 = M-(-M-1)-1 = 2*M.  Therefore unsigned long has enough
    # precision to compute the RHS exactly.

    # slight modification: we raise on everything bad and also adjust args
    if step == 0:
        raise ValueError
    elif step < 0:
        lo, hi, step = hi, lo, -step
    if lo < hi:
        uhi = r_uint(hi)
        ulo = r_uint(lo)
        diff = uhi - ulo - 1
        n = intmask(diff // r_uint(step) + 1)
        if n < 0:
            raise OverflowError
    else:
        n = 0
    return n

def range(space, w_x, w_y=None, w_step=1):
    """Return a list of integers in arithmetic position from start (defaults
to zero) to stop - 1 by step (defaults to 1).  Use a negative step to
get a list in decending order."""

    try:
        # save duplication by redirecting every error to applevel
        x = space.int_w(w_x)
        if space.is_w(w_y, space.w_None):
            start, stop = 0, x
        else:
            start, stop = x, space.int_w(w_y)
        step = space.int_w(w_step)
        howmany = get_len_of_range(start, stop, step)
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            pass
        else:
            raise
    except (ValueError, OverflowError):
        pass
    else:
        if (space.config.objspace.std.withmultilist or
            space.config.objspace.std.withrangelist):
            return range_withspecialized_implementation(space, start,
                                                        step, howmany)
        res_w = [None] * howmany
        v = start
        for idx in range(howmany):
            res_w[idx] = space.wrap(v)
            v += step
        return space.newlist(res_w)
    return range_fallback(space, w_x, w_y, w_step)
range_int = range
range_int.unwrap_spec = [ObjSpace, W_Root, W_Root, W_Root]
del range # don't hide the builtin one

range_fallback = applevel(getsource(app_range), getfile(app_range)
                          ).interphook('range')

def range_withspecialized_implementation(space, start, step, howmany):
    if space.config.objspace.std.withrangelist:
        from pypy.objspace.std.rangeobject import W_RangeListObject
        return W_RangeListObject(start, step, howmany)
    if space.config.objspace.std.withmultilist:
        from pypy.objspace.std.listmultiobject import W_ListMultiObject
        from pypy.objspace.std.listmultiobject import RangeImplementation
        impl = RangeImplementation(space, start, step, howmany)
        return W_ListMultiObject(space, impl)


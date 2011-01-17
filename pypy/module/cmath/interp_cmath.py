import math
from math import fabs
from pypy.rlib.rarithmetic import copysign, asinh
from pypy.interpreter.gateway import ObjSpace, W_Root
from pypy.module.cmath import Module
from pypy.module.cmath.constant import DBL_MIN, CM_SCALE_UP, CM_SCALE_DOWN
from pypy.module.cmath.constant import CM_LARGE_DOUBLE, M_LN2
from pypy.module.cmath.special_value import isfinite, special_type
from pypy.module.cmath.special_value import sqrt_special_values
from pypy.module.cmath.special_value import acos_special_values


def unaryfn(c_func):
    def wrapper(space, w_z):
        x = space.float_w(space.getattr(w_z, space.wrap('real')))
        y = space.float_w(space.getattr(w_z, space.wrap('imag')))
        resx, resy = c_func(x, y)
        return space.newcomplex(resx, resy)
    #
    name = c_func.func_name
    assert name.startswith('c_')
    wrapper.unwrap_spec = [ObjSpace, W_Root]
    globals()['wrapped_' + name[2:]] = wrapper
    return c_func


@unaryfn
def c_sqrt(x, y):
    # Method: use symmetries to reduce to the case when x = z.real and y
    # = z.imag are nonnegative.  Then the real part of the result is
    # given by
    #
    #   s = sqrt((x + hypot(x, y))/2)
    #
    # and the imaginary part is
    #
    #   d = (y/2)/s
    #
    # If either x or y is very large then there's a risk of overflow in
    # computation of the expression x + hypot(x, y).  We can avoid this
    # by rewriting the formula for s as:
    #
    #   s = 2*sqrt(x/8 + hypot(x/8, y/8))
    #
    # This costs us two extra multiplications/divisions, but avoids the
    # overhead of checking for x and y large.
    #
    # If both x and y are subnormal then hypot(x, y) may also be
    # subnormal, so will lack full precision.  We solve this by rescaling
    # x and y by a sufficiently large power of 2 to ensure that x and y
    # are normal.

    if not isfinite(x) or not isfinite(y):
        return sqrt_special_values[special_type(x)][special_type(y)]

    if x == 0. and y == 0.:
        return (0., y)

    ax = fabs(x)
    ay = fabs(y)

    if ax < DBL_MIN and ay < DBL_MIN and (ax > 0. or ay > 0.):
        # here we catch cases where hypot(ax, ay) is subnormal
        ax = math.ldexp(ax, CM_SCALE_UP)
        ay1= math.ldexp(ay, CM_SCALE_UP)
        s = math.ldexp(math.sqrt(ax + math.hypot(ax, ay1)),
                       CM_SCALE_DOWN)
    else:
        ax /= 8.
        s = 2.*math.sqrt(ax + math.hypot(ax, ay/8.))

    d = ay/(2.*s)

    if x >= 0.:
        return (s, copysign(d, y))
    else:
        return (d, copysign(s, y))


@unaryfn
def c_acos(x, y):
    if not isfinite(x) or not isfinite(y):
        return acos_special_values[special_type(x)][special_type(y)]

    if fabs(x) > CM_LARGE_DOUBLE or fabs(y) > CM_LARGE_DOUBLE:
        # avoid unnecessary overflow for large arguments
        real = math.atan2(fabs(y), x)
        # split into cases to make sure that the branch cut has the
        # correct continuity on systems with unsigned zeros
        if x < 0.:
            imag = -copysign(math.log(math.hypot(x/2., y/2.)) +
                             M_LN2*2., y)
        else:
            imag = copysign(math.log(math.hypot(x/2., y/2.)) +
                            M_LN2*2., -y)
    else:
        s1x, s1y = c_sqrt(1.-x, -y)
        s2x, s2y = c_sqrt(1.+x, y)
        real = 2.*math.atan2(s1x, s2x)
        imag = asinh(s2x*s1y - s2y*s1x)
    return (real, imag)

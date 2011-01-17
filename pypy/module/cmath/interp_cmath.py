import math
from pypy.rlib.rarithmetic import copysign
from pypy.interpreter.gateway import ObjSpace, W_Root
from pypy.module.cmath import Module
from pypy.module.cmath.constant import DBL_MIN, CM_SCALE_UP, CM_SCALE_DOWN
from pypy.module.cmath.special_value import isfinite, special_type
from pypy.module.cmath.special_value import sqrt_special_values


def unaryfn(name):
    def decorator(c_func):
        def wrapper(space, w_z):
            x = space.float_w(space.getattr(w_z, space.wrap('real')))
            y = space.float_w(space.getattr(w_z, space.wrap('imag')))
            resx, resy = c_func(x, y)
            return space.newcomplex(resx, resy)
        wrapper.unwrap_spec = [ObjSpace, W_Root]
        globals()['wrapped_' + name] = wrapper
        return c_func
    return decorator


@unaryfn('sqrt')
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

    ax = math.fabs(x)
    ay = math.fabs(y)

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


##@unaryfn
##def c_acos(x, y):
##    s1x, s1y = c_sqrt(1.-x, -y)
##    s2x, s2y = c_sqrt(1.+x, y)
##        r.real = 2.*atan2(s1.real, s2.real);
##        r.imag = m_asinh(s2.real*s1.imag - s2.imag*s1.real);

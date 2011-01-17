import math
from math import fabs
from pypy.rlib.rarithmetic import copysign, asinh, log1p
from pypy.interpreter.gateway import ObjSpace, W_Root
from pypy.module.cmath import Module, names_and_docstrings
from pypy.module.cmath.constant import DBL_MIN, CM_SCALE_UP, CM_SCALE_DOWN
from pypy.module.cmath.constant import CM_LARGE_DOUBLE, M_LN2
from pypy.module.cmath.constant import CM_SQRT_LARGE_DOUBLE, CM_SQRT_DBL_MIN
from pypy.module.cmath.special_value import isfinite, special_type, INF
from pypy.module.cmath.special_value import sqrt_special_values
from pypy.module.cmath.special_value import acos_special_values
from pypy.module.cmath.special_value import acosh_special_values
from pypy.module.cmath.special_value import asinh_special_values
from pypy.module.cmath.special_value import atanh_special_values


def unaryfn(c_func):
    def wrapper(space, w_z):
        x = space.float_w(space.getattr(w_z, space.wrap('real')))
        y = space.float_w(space.getattr(w_z, space.wrap('imag')))
        try:
            resx, resy = c_func(x, y)
        except ValueError:
            raise OperationError(space.w_ValueError,
                                 space.wrap("math domain error"))
        except OverflowError:
            raise OperationError(space.w_OverflowError,
                                 space.wrap("math range error"))
        return space.newcomplex(resx, resy)
    #
    name = c_func.func_name
    assert name.startswith('c_')
    wrapper.unwrap_spec = [ObjSpace, W_Root]
    wrapper.func_doc = names_and_docstrings[name[2:]]
    globals()['wrapped_' + name[2:]] = wrapper
    return c_func


def c_neg(x, y):
    return (-x, -y)


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


@unaryfn
def c_acosh(x, y):
    # XXX the following two lines seem unnecessary at least on Linux;
    # the tests pass fine without them
    if not isfinite(x) or not isfinite(y):
        return acosh_special_values[special_type(x)][special_type(y)]

    if fabs(x) > CM_LARGE_DOUBLE or fabs(y) > CM_LARGE_DOUBLE:
        # avoid unnecessary overflow for large arguments
        real = math.log(math.hypot(x/2., y/2.)) + M_LN2*2.
        imag = math.atan2(y, x)
    else:
        s1x, s1y = c_sqrt(x - 1., y)
        s2x, s2y = c_sqrt(x + 1., y)
        real = asinh(s1x*s2x + s1y*s2y)
        imag = 2.*math.atan2(s1y, s2x)
    return (real, imag)


@unaryfn
def c_asin(x, y):
    # asin(z) = -i asinh(iz)
    sx, sy = c_asinh(-y, x)
    return (sy, -sx)


@unaryfn
def c_asinh(x, y):
    if not isfinite(x) or not isfinite(y):
        return asinh_special_values[special_type(x)][special_type(y)]

    if fabs(x) > CM_LARGE_DOUBLE or fabs(y) > CM_LARGE_DOUBLE:
        if y >= 0.:
            real = copysign(math.log(math.hypot(x/2., y/2.)) +
                            M_LN2*2., x)
        else:
            real = -copysign(math.log(math.hypot(x/2., y/2.)) +
                             M_LN2*2., -x)
        imag = math.atan2(y, fabs(x))
    else:
        s1x, s1y = c_sqrt(1.+y, -x)
        s2x, s2y = c_sqrt(1.-y, x)
        real = asinh(s1x*s2y - s2x*s1y)
        imag = math.atan2(y, s1x*s2x - s1y*s2y)
    return (real, imag)


@unaryfn
def c_atan(x, y):
    # atan(z) = -i atanh(iz)
    sx, sy = c_atanh(-y, x)
    return (sy, -sx)


@unaryfn
def c_atanh(x, y):
    if not isfinite(x) or not isfinite(y):
        return atanh_special_values[special_type(x)][special_type(y)]

    # Reduce to case where x >= 0., using atanh(z) = -atanh(-z).
    if x < 0.:
        return c_neg(*c_atanh(*c_neg(x, y)))

    ay = fabs(y)
    if x > CM_SQRT_LARGE_DOUBLE or ay > CM_SQRT_LARGE_DOUBLE:
        # if abs(z) is large then we use the approximation
        # atanh(z) ~ 1/z +/- i*pi/2 (+/- depending on the sign
        # of y
        h = math.hypot(x/2., y/2.)   # safe from overflow
        real = x/4./h/h
        # the two negations in the next line cancel each other out
        # except when working with unsigned zeros: they're there to
        # ensure that the branch cut has the correct continuity on
        # systems that don't support signed zeros
        imag = -copysign(math.pi/2., -y)
    elif x == 1. and ay < CM_SQRT_DBL_MIN:
        # C99 standard says:  atanh(1+/-0.) should be inf +/- 0i
        if ay == 0.:
            real = INF
            imag = y
            raise ValueError("result is infinite")
        else:
            real = -math.log(math.sqrt(ay)/math.sqrt(math.hypot(ay, 2.)))
            imag = copysign(math.atan2(2., -ay)/2, y)
    else:
        real = log1p(4.*x/((1-x)*(1-x) + ay*ay))/4.
        imag = -math.atan2(-2.*y, (1-x)*(1+x) - ay*ay)/2.
    return (real, imag)

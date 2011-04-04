import math
from math import fabs
from pypy.rlib.objectmodel import specialize
from pypy.rlib.rfloat import copysign, asinh, log1p, isinf, isnan
from pypy.tool.sourcetools import func_with_new_name
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import NoneNotWrapped
from pypy.module.cmath import Module, names_and_docstrings
from pypy.module.cmath.constant import DBL_MIN, CM_SCALE_UP, CM_SCALE_DOWN
from pypy.module.cmath.constant import CM_LARGE_DOUBLE, DBL_MANT_DIG
from pypy.module.cmath.constant import M_LN2, M_LN10
from pypy.module.cmath.constant import CM_SQRT_LARGE_DOUBLE, CM_SQRT_DBL_MIN
from pypy.module.cmath.constant import CM_LOG_LARGE_DOUBLE
from pypy.module.cmath.special_value import isfinite, special_type, INF, NAN
from pypy.module.cmath.special_value import sqrt_special_values
from pypy.module.cmath.special_value import acos_special_values
from pypy.module.cmath.special_value import acosh_special_values
from pypy.module.cmath.special_value import asinh_special_values
from pypy.module.cmath.special_value import atanh_special_values
from pypy.module.cmath.special_value import log_special_values
from pypy.module.cmath.special_value import exp_special_values
from pypy.module.cmath.special_value import cosh_special_values
from pypy.module.cmath.special_value import sinh_special_values
from pypy.module.cmath.special_value import tanh_special_values
from pypy.module.cmath.special_value import rect_special_values

pi = math.pi
e  = math.e


@specialize.arg(0)
def call_c_func(c_func, space, x, y):
    try:
        result = c_func(x, y)
    except ValueError:
        raise OperationError(space.w_ValueError,
                             space.wrap("math domain error"))
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("math range error"))
    return result


def unaryfn(c_func):
    def wrapper(space, w_z):
        x, y = space.unpackcomplex(w_z)
        resx, resy = call_c_func(c_func, space, x, y)
        return space.newcomplex(resx, resy)
    #
    name = c_func.func_name
    assert name.startswith('c_')
    wrapper.func_doc = names_and_docstrings[name[2:]]
    fnname = 'wrapped_' + name[2:]
    globals()[fnname] = func_with_new_name(wrapper, fnname)
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
            raise ValueError("math domain error")
            #real = INF
            #imag = y
        else:
            real = -math.log(math.sqrt(ay)/math.sqrt(math.hypot(ay, 2.)))
            imag = copysign(math.atan2(2., -ay) / 2, y)
    else:
        real = log1p(4.*x/((1-x)*(1-x) + ay*ay))/4.
        imag = -math.atan2(-2.*y, (1-x)*(1+x) - ay*ay) / 2.
    return (real, imag)


@unaryfn
def c_log(x, y):
    # The usual formula for the real part is log(hypot(z.real, z.imag)).
    # There are four situations where this formula is potentially
    # problematic:
    #
    # (1) the absolute value of z is subnormal.  Then hypot is subnormal,
    # so has fewer than the usual number of bits of accuracy, hence may
    # have large relative error.  This then gives a large absolute error
    # in the log.  This can be solved by rescaling z by a suitable power
    # of 2.
    #
    # (2) the absolute value of z is greater than DBL_MAX (e.g. when both
    # z.real and z.imag are within a factor of 1/sqrt(2) of DBL_MAX)
    # Again, rescaling solves this.
    #
    # (3) the absolute value of z is close to 1.  In this case it's
    # difficult to achieve good accuracy, at least in part because a
    # change of 1ulp in the real or imaginary part of z can result in a
    # change of billions of ulps in the correctly rounded answer.
    #
    # (4) z = 0.  The simplest thing to do here is to call the
    # floating-point log with an argument of 0, and let its behaviour
    # (returning -infinity, signaling a floating-point exception, setting
    # errno, or whatever) determine that of c_log.  So the usual formula
    # is fine here.

    # XXX the following two lines seem unnecessary at least on Linux;
    # the tests pass fine without them
    if not isfinite(x) or not isfinite(y):
        return log_special_values[special_type(x)][special_type(y)]

    ax = fabs(x)
    ay = fabs(y)

    if ax > CM_LARGE_DOUBLE or ay > CM_LARGE_DOUBLE:
        real = math.log(math.hypot(ax/2., ay/2.)) + M_LN2
    elif ax < DBL_MIN and ay < DBL_MIN:
        if ax > 0. or ay > 0.:
            # catch cases where hypot(ax, ay) is subnormal
            real = math.log(math.hypot(math.ldexp(ax, DBL_MANT_DIG),
                                       math.ldexp(ay, DBL_MANT_DIG)))
            real -= DBL_MANT_DIG*M_LN2
        else:
            # log(+/-0. +/- 0i)
            raise ValueError("math domain error")
            #real = -INF
            #imag = atan2(y, x)
    else:
        h = math.hypot(ax, ay)
        if 0.71 <= h and h <= 1.73:
            am = max(ax, ay)
            an = min(ax, ay)
            real = log1p((am-1)*(am+1) + an*an) / 2.
        else:
            real = math.log(h)
    imag = math.atan2(y, x)
    return (real, imag)


_inner_wrapped_log = wrapped_log

def wrapped_log(space, w_z, w_base=NoneNotWrapped):
    w_logz = _inner_wrapped_log(space, w_z)
    if w_base is not None:
        w_logbase = _inner_wrapped_log(space, w_base)
        return space.truediv(w_logz, w_logbase)
    else:
        return w_logz
wrapped_log.func_doc = _inner_wrapped_log.func_doc


@unaryfn
def c_log10(x, y):
    rx, ry = c_log(x, y)
    return (rx / M_LN10, ry / M_LN10)


@unaryfn
def c_exp(x, y):
    if not isfinite(x) or not isfinite(y):
        if isinf(x) and isfinite(y) and y != 0.:
            if x > 0:
                real = copysign(INF, math.cos(y))
                imag = copysign(INF, math.sin(y))
            else:
                real = copysign(0., math.cos(y))
                imag = copysign(0., math.sin(y))
            r = (real, imag)
        else:
            r = exp_special_values[special_type(x)][special_type(y)]

        # need to raise ValueError if y is +/- infinity and x is not
        # a NaN and not -infinity
        if isinf(y) and (isfinite(x) or (isinf(x) and x > 0)):
            raise ValueError("math domain error")
        return r

    if x > CM_LOG_LARGE_DOUBLE:
        l = math.exp(x-1.)
        real = l * math.cos(y) * math.e
        imag = l * math.sin(y) * math.e
    else:
        l = math.exp(x)
        real = l * math.cos(y)
        imag = l * math.sin(y)
    if isinf(real) or isinf(imag):
        raise OverflowError("math range error")
    return real, imag


@unaryfn
def c_cosh(x, y):
    if not isfinite(x) or not isfinite(y):
        if isinf(x) and isfinite(y) and y != 0.:
            if x > 0:
                real = copysign(INF, math.cos(y))
                imag = copysign(INF, math.sin(y))
            else:
                real = copysign(INF, math.cos(y))
                imag = -copysign(INF, math.sin(y))
            r = (real, imag)
        else:
            r = cosh_special_values[special_type(x)][special_type(y)]

        # need to raise ValueError if y is +/- infinity and x is not
        # a NaN
        if isinf(y) and not isnan(x):
            raise ValueError("math domain error")
        return r

    if fabs(x) > CM_LOG_LARGE_DOUBLE:
        # deal correctly with cases where cosh(x) overflows but
        # cosh(z) does not.
        x_minus_one = x - copysign(1., x)
        real = math.cos(y) * math.cosh(x_minus_one) * math.e
        imag = math.sin(y) * math.sinh(x_minus_one) * math.e
    else:
        real = math.cos(y) * math.cosh(x)
        imag = math.sin(y) * math.sinh(x)
    if isinf(real) or isinf(imag):
        raise OverflowError("math range error")
    return real, imag


@unaryfn
def c_sinh(x, y):
    # special treatment for sinh(+/-inf + iy) if y is finite and nonzero
    if not isfinite(x) or not isfinite(y):
        if isinf(x) and isfinite(y) and y != 0.:
            if x > 0:
                real = copysign(INF, math.cos(y))
                imag = copysign(INF, math.sin(y))
            else:
                real = -copysign(INF, math.cos(y))
                imag = copysign(INF, math.sin(y))
            r = (real, imag)
        else:
            r = sinh_special_values[special_type(x)][special_type(y)]

        # need to raise ValueError if y is +/- infinity and x is not
        # a NaN
        if isinf(y) and not isnan(x):
            raise ValueError("math domain error")
        return r

    if fabs(x) > CM_LOG_LARGE_DOUBLE:
        x_minus_one = x - copysign(1., x)
        real = math.cos(y) * math.sinh(x_minus_one) * math.e
        imag = math.sin(y) * math.cosh(x_minus_one) * math.e
    else:
        real = math.cos(y) * math.sinh(x)
        imag = math.sin(y) * math.cosh(x)
    if isinf(real) or isinf(imag):
        raise OverflowError("math range error")
    return real, imag


@unaryfn
def c_tanh(x, y):
    # Formula:
    #
    #   tanh(x+iy) = (tanh(x)(1+tan(y)^2) + i tan(y)(1-tanh(x))^2) /
    #   (1+tan(y)^2 tanh(x)^2)
    #
    #   To avoid excessive roundoff error, 1-tanh(x)^2 is better computed
    #   as 1/cosh(x)^2.  When abs(x) is large, we approximate 1-tanh(x)^2
    #   by 4 exp(-2*x) instead, to avoid possible overflow in the
    #   computation of cosh(x).

    if not isfinite(x) or not isfinite(y):
        if isinf(x) and isfinite(y) and y != 0.:
            if x > 0:
                real = 1.0        # vv XXX why is the 2. there?
                imag = copysign(0., 2. * math.sin(y) * math.cos(y))
            else:
                real = -1.0
                imag = copysign(0., 2. * math.sin(y) * math.cos(y))
            r = (real, imag)
        else:
            r = tanh_special_values[special_type(x)][special_type(y)]

        # need to raise ValueError if y is +/-infinity and x is finite
        if isinf(y) and isfinite(x):
            raise ValueError("math domain error")
        return r

    if fabs(x) > CM_LOG_LARGE_DOUBLE:
        real = copysign(1., x)
        imag = 4. * math.sin(y) * math.cos(y) * math.exp(-2.*fabs(x))
    else:
        tx = math.tanh(x)
        ty = math.tan(y)
        cx = 1. / math.cosh(x)
        txty = tx * ty
        denom = 1. + txty * txty
        real = tx * (1. + ty*ty) / denom
        imag = ((ty / denom) * cx) * cx
    return real, imag


@unaryfn
def c_cos(x, y):
    # cos(z) = cosh(iz)
    return c_cosh(-y, x)

@unaryfn
def c_sin(x, y):
    # sin(z) = -i sinh(iz)
    sx, sy = c_sinh(-y, x)
    return sy, -sx

@unaryfn
def c_tan(x, y):
    # tan(z) = -i tanh(iz)
    sx, sy = c_tanh(-y, x)
    return sy, -sx


def c_rect(r, phi):
    if not isfinite(r) or not isfinite(phi):
        # if r is +/-infinity and phi is finite but nonzero then
        # result is (+-INF +-INF i), but we need to compute cos(phi)
        # and sin(phi) to figure out the signs.
        if isinf(r) and isfinite(phi) and phi != 0.:
            if r > 0:
                real = copysign(INF, math.cos(phi))
                imag = copysign(INF, math.sin(phi))
            else:
                real = -copysign(INF, math.cos(phi))
                imag = -copysign(INF, math.sin(phi))
            z = (real, imag)
        else:
            z = rect_special_values[special_type(r)][special_type(phi)]

        # need to raise ValueError if r is a nonzero number and phi
        # is infinite
        if r != 0. and not isnan(r) and isinf(phi):
            raise ValueError("math domain error")
        return z

    real = r * math.cos(phi)
    imag = r * math.sin(phi)
    return real, imag

def wrapped_rect(space, w_x, w_y):
    x = space.float_w(w_x)
    y = space.float_w(w_y)
    resx, resy = call_c_func(c_rect, space, x, y)
    return space.newcomplex(resx, resy)
wrapped_rect.func_doc = names_and_docstrings['rect']


def c_phase(x, y):
    # Windows screws up atan2 for inf and nan, and alpha Tru64 5.1 doesn't
    # follow C99 for atan2(0., 0.).
    if isnan(x) or isnan(y):
        return NAN
    if isinf(y):
        if isinf(x):
            if copysign(1., x) == 1.:
                # atan2(+-inf, +inf) == +-pi/4
                return copysign(0.25 * math.pi, y)
            else:
                # atan2(+-inf, -inf) == +-pi*3/4
                return copysign(0.75 * math.pi, y)
        # atan2(+-inf, x) == +-pi/2 for finite x
        return copysign(0.5 * math.pi, y)
    if isinf(x) or y == 0.:
        if copysign(1., x) == 1.:
            # atan2(+-y, +inf) = atan2(+-0, +x) = +-0.
            return copysign(0., y)
        else:
            # atan2(+-y, -inf) = atan2(+-0., -x) = +-pi.
            return copysign(math.pi, y)
    return math.atan2(y, x)

def wrapped_phase(space, w_z):
    x, y = space.unpackcomplex(w_z)
    result = call_c_func(c_phase, space, x, y)
    return space.newfloat(result)
wrapped_phase.func_doc = names_and_docstrings['phase']


def c_abs(x, y):
    if not isfinite(x) or not isfinite(y):
        # C99 rules: if either the real or the imaginary part is an
        # infinity, return infinity, even if the other part is a NaN.
        if isinf(x):
            return INF
        if isinf(y):
            return INF

        # either the real or imaginary part is a NaN,
        # and neither is infinite. Result should be NaN.
        return NAN

    result = math.hypot(x, y)
    if not isfinite(result):
        raise OverflowError("math range error")
    return result


def c_polar(x, y):
    phi = c_phase(x, y)
    r = c_abs(x, y)
    return r, phi

def wrapped_polar(space, w_z):
    x, y = space.unpackcomplex(w_z)
    resx, resy = call_c_func(c_polar, space, x, y)
    return space.newtuple([space.newfloat(resx), space.newfloat(resy)])
wrapped_polar.func_doc = names_and_docstrings['polar']


def c_isinf(x, y):
    return isinf(x) or isinf(y)

def wrapped_isinf(space, w_z):
    x, y = space.unpackcomplex(w_z)
    res = c_isinf(x, y)
    return space.newbool(res)
wrapped_isinf.func_doc = names_and_docstrings['isinf']


def c_isnan(x, y):
    return isnan(x) or isnan(y)

def wrapped_isnan(space, w_z):
    x, y = space.unpackcomplex(w_z)
    res = c_isnan(x, y)
    return space.newbool(res)
wrapped_isnan.func_doc = names_and_docstrings['isnan']

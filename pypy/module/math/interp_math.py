import math
import sys

from pypy.rlib import rfloat, unroll
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import NoneNotWrapped

class State:
    def __init__(self, space):
        self.w_e = space.wrap(math.e)
        self.w_pi = space.wrap(math.pi)
def get(space):
    return space.fromcache(State)

def _get_double(space, w_x):
    if space.is_w(space.type(w_x), space.w_float):
        return space.float_w(w_x)
    else:
        return space.float_w(space.float(w_x))

def math1(space, f, w_x):
    x = _get_double(space, w_x)
    try:
        y = f(x)
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("math range error"))
    except ValueError:
        raise OperationError(space.w_ValueError,
                             space.wrap("math domain error"))
    return space.wrap(y)
math1._annspecialcase_ = 'specialize:arg(1)'

def math1_w(space, f, w_x):
    x = _get_double(space, w_x)
    try:
        r = f(x)
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("math range error"))
    except ValueError:
        raise OperationError(space.w_ValueError,
                             space.wrap("math domain error"))
    return r
math1_w._annspecialcase_ = 'specialize:arg(1)'

def math2(space, f, w_x, w_snd):
    x = _get_double(space, w_x)
    snd = _get_double(space, w_snd)
    try:
        r = f(x, snd)
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("math range error"))
    except ValueError:
        raise OperationError(space.w_ValueError,
                             space.wrap("math domain error"))
    return space.wrap(r)
math2._annspecialcase_ = 'specialize:arg(1)'

def trunc(space, w_x):
    """Truncate x."""
    return space.trunc(w_x)

def copysign(space, w_x, w_y):
    """Return x with the sign of y."""
    # No exceptions possible.
    x = _get_double(space, w_x)
    y = _get_double(space, w_y)
    return space.wrap(rfloat.copysign(x, y))

def isinf(space, w_x):
    """Return True if x is infinity."""
    return space.wrap(rfloat.isinf(_get_double(space, w_x)))

def isnan(space, w_x):
    """Return True if x is not a number."""
    return space.wrap(rfloat.isnan(_get_double(space, w_x)))

def pow(space, w_x, w_y):
    """pow(x,y)

       Return x**y (x to the power of y).
    """
    return math2(space, math.pow, w_x, w_y)

def cosh(space, w_x):
    """cosh(x)

       Return the hyperbolic cosine of x.
    """
    return math1(space, math.cosh, w_x)

def ldexp(space, w_x,  w_i):
    """ldexp(x, i) -> x * (2**i)
    """
    x = _get_double(space, w_x)
    if (space.isinstance_w(w_i, space.w_int) or
        space.isinstance_w(w_i, space.w_long)):
        try:
            exp = space.int_w(w_i)
        except OperationError, e:
            if not e.match(space, space.w_OverflowError):
                raise
            if space.is_true(space.lt(w_i, space.wrap(0))):
                exp = -sys.maxint
            else:
                exp = sys.maxint
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("integer required for second argument"))
    try:
        r = math.ldexp(x, exp)
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("math range error"))
    except ValueError:
        raise OperationError(space.w_ValueError,
                             space.wrap("math domain error"))
    return space.wrap(r)

def hypot(space, w_x, w_y):
    """hypot(x,y)

       Return the Euclidean distance, sqrt(x*x + y*y).
    """
    return math2(space, math.hypot, w_x, w_y)

def tan(space, w_x):
    """tan(x)

       Return the tangent of x (measured in radians).
    """
    return math1(space, math.tan, w_x)

def asin(space, w_x):
    """asin(x)

       Return the arc sine (measured in radians) of x.
    """
    return math1(space, math.asin, w_x)

def fabs(space, w_x):
    """fabs(x)

       Return the absolute value of the float x.
    """
    return math1(space, math.fabs, w_x)

def floor(space, w_x):
    """floor(x)

       Return the floor of x as a float.
       This is the largest integral value <= x.
    """
    x = _get_double(space, w_x)
    return space.wrap(math.floor(x))

def sqrt(space, w_x):
    """sqrt(x)

       Return the square root of x.
    """
    return math1(space, math.sqrt, w_x)

def frexp(space, w_x):
    """frexp(x)

       Return the mantissa and exponent of x, as pair (m, e).
       m is a float and e is an int, such that x = m * 2.**e.
       If x is 0, m and e are both 0.  Else 0.5 <= abs(m) < 1.0.
    """
    mant, expo = math1_w(space, math.frexp, w_x)
    return space.newtuple([space.wrap(mant), space.wrap(expo)])

degToRad = math.pi / 180.0

def degrees(space, w_x):
    """degrees(x) -> converts angle x from radians to degrees
    """
    return space.wrap(_get_double(space, w_x) / degToRad)

def _log_any(space, w_x, base):
    # base is supposed to be positive or 0.0, which means we use e
    try:
        if space.is_true(space.isinstance(w_x, space.w_long)):
            # special case to support log(extremely-large-long)
            num = space.bigint_w(w_x)
            result = num.log(base)
        else:
            x = _get_double(space, w_x)
            if base == 10.0:
                result = math.log10(x)
            else:
                result = math.log(x)
                if base != 0.0:
                    den = math.log(base)
                    result /= den
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap('math range error'))
    except ValueError:
        raise OperationError(space.w_ValueError,
                             space.wrap('math domain error'))
    return space.wrap(result)

def log(space, w_x, w_base=NoneNotWrapped):
    """log(x[, base]) -> the logarithm of x to the given base.
       If the base not specified, returns the natural logarithm (base e) of x.
    """
    if w_base is None:
        base = 0.0
    else:
        base = _get_double(space, w_base)
        if base <= 0.0:
            # just for raising the proper errors
            return math1(space, math.log, w_base)
    return _log_any(space, w_x, base)

def log10(space, w_x):
    """log10(x) -> the base 10 logarithm of x.
    """
    return _log_any(space, w_x, 10.0)

def fmod(space, w_x, w_y):
    """fmod(x,y)

       Return fmod(x, y), according to platform C.  x % y may differ.
    """
    return math2(space, math.fmod, w_x, w_y)

def atan(space, w_x):
    """atan(x)

       Return the arc tangent (measured in radians) of x.
    """
    return math1(space, math.atan, w_x)

def ceil(space, w_x):
    """ceil(x)

       Return the ceiling of x as a float.
       This is the smallest integral value >= x.
    """
    return math1(space, math.ceil, w_x)

def sinh(space, w_x):
    """sinh(x)

       Return the hyperbolic sine of x.
    """
    return math1(space, math.sinh, w_x)

def cos(space, w_x):
    """cos(x)

       Return the cosine of x (measured in radians).
    """
    return math1(space, math.cos, w_x)

def tanh(space, w_x):
    """tanh(x)

       Return the hyperbolic tangent of x.
    """
    return math1(space, math.tanh, w_x)

def radians(space, w_x):
    """radians(x) -> converts angle x from degrees to radians
    """
    return space.wrap(_get_double(space, w_x) * degToRad)

def sin(space, w_x):
    """sin(x)

       Return the sine of x (measured in radians).
    """
    return math1(space, math.sin, w_x)

def atan2(space, w_y, w_x):
    """atan2(y, x)

       Return the arc tangent (measured in radians) of y/x.
       Unlike atan(y/x), the signs of both x and y are considered.
    """
    return math2(space, math.atan2, w_y,  w_x)

def modf(space, w_x):
    """modf(x)

       Return the fractional and integer parts of x.  Both results carry the sign
       of x.  The integer part is returned as a real.
    """
    frac, intpart = math1_w(space, math.modf, w_x)
    return space.newtuple([space.wrap(frac), space.wrap(intpart)])

def exp(space, w_x):
    """exp(x)

       Return e raised to the power of x.
    """
    return math1(space, math.exp, w_x)

def acos(space, w_x):
    """acos(x)

       Return the arc cosine (measured in radians) of x.
    """
    return math1(space, math.acos, w_x)

def fsum(space, w_iterable):
    """Sum an iterable of floats, trying to keep precision."""
    w_iter = space.iter(w_iterable)
    inf_sum = special_sum = 0.0
    partials = []
    while True:
        try:
            w_value = space.next(w_iter)
        except OperationError, e:
            if not e.match(space, space.w_StopIteration):
                raise
            break
        v = _get_double(space, w_value)
        original = v
        added = 0
        for y in partials:
            if abs(v) < abs(y):
                v, y = y, v
            hi = v + y
            yr = hi - v
            lo = y - yr
            if lo != 0.0:
                partials[added] = lo
                added += 1
            v = hi
        del partials[added:]
        if v != 0.0:
            if rfloat.isinf(v) or rfloat.isnan(v):
                if (not rfloat.isinf(original) and
                    not rfloat.isnan(original)):
                    raise OperationError(space.w_OverflowError,
                                         space.wrap("intermediate overflow"))
                if rfloat.isinf(original):
                    inf_sum += original
                special_sum += original
                del partials[:]
            else:
                partials.append(v)
    if special_sum != 0.0:
        if rfloat.isnan(special_sum):
            raise OperationError(space.w_ValueError, space.wrap("-inf + inf"))
        return space.wrap(special_sum)
    hi = 0.0
    if partials:
        hi = partials[-1]
        j = 0
        lo = 0
        for j in range(len(partials) - 2, -1, -1):
            v = hi
            y = partials[j]
            assert abs(y) < abs(v)
            hi = v + y
            yr = hi - v
            lo = y - yr
            if lo != 0.0:
                break
        if j > 0 and (lo < 0.0 and partials[j - 1] < 0.0 or
                      lo > 0.0 and partials[j - 1] > 0.0):
            y = lo * 2.0
            v = hi + y
            yr = v - hi
            if y == yr:
                hi = v
    return space.wrap(hi)

def log1p(space, w_x):
    """Find log(x + 1)."""
    return math1(space, rfloat.log1p, w_x)

def acosh(space, w_x):
    """Inverse hyperbolic cosine"""
    return math1(space, rfloat.acosh, w_x)

def asinh(space, w_x):
    """Inverse hyperbolic sine"""
    return math1(space, rfloat.asinh, w_x)

def atanh(space, w_x):
    """Inverse hyperbolic tangent"""
    return math1(space, rfloat.atanh, w_x)

def expm1(space, w_x):
    """exp(x) - 1"""
    return math1(space, rfloat.expm1, w_x)

def erf(space, w_x):
    """The error function"""
    return math1(space, _erf, w_x)

def erfc(space, w_x):
    """The complementary error function"""
    return math1(space, _erfc, w_x)

def gamma(space, w_x):
    """Compute the gamma function for x."""
    return math1(space, _gamma, w_x)

def lgamma(space, w_x):
    """Compute the natural logarithm of the gamma function for x."""
    return math1(space, _lgamma, w_x)

# Implementation of the error function, the complimentary error function, the
# gamma function, and the natural log of the gamma function.  These exist in
# libm, but I hear those implementations are horrible.

ERF_SERIES_CUTOFF = 1.5
ERF_SERIES_TERMS = 25
ERFC_CONTFRAC_CUTOFF = 30.
ERFC_CONTFRAC_TERMS = 50
_sqrtpi = 1.772453850905516027298167483341145182798

def _erf_series(x):
    x2 = x * x
    acc = 0.
    fk = ERF_SERIES_TERMS + .5
    for i in range(ERF_SERIES_TERMS):
        acc = 2.0 + x2 * acc / fk
        fk -= 1.
    return acc * x * math.exp(-x2) / _sqrtpi

def _erfc_contfrac(x):
    if x >= ERFC_CONTFRAC_CUTOFF:
        return 0.
    x2 = x * x
    a = 0.
    da = .5
    p = 1.
    p_last = 0.
    q = da + x2
    q_last = 1.
    for i in range(ERFC_CONTFRAC_TERMS):
        a += da
        da += 2.
        b = da + x2
        p_last, p = p, b * p - a * p_last
        q_last, q = q, b * q - a * q_last
    return p / q * x * math.exp(-x2) / _sqrtpi

def _erf(x):
    if rfloat.isnan(x):
        return x
    absx = abs(x)
    if absx < ERF_SERIES_CUTOFF:
        return _erf_series(x)
    else:
        cf = _erfc_contfrac(absx)
        return 1. - cf if x > 0. else cf - 1.

def _erfc(x):
    if rfloat.isnan(x):
        return x
    absx = abs(x)
    if absx < ERF_SERIES_CUTOFF:
        return 1. - _erf_series(x)
    else:
        cf = _erfc_contfrac(absx)
        return cf if x > 0. else 2. - cf

def _sinpi(x):
    y = math.fmod(abs(x), 2.)
    n = int(rfloat.round_away(2. * y))
    if n == 0:
        r = math.sin(math.pi * y)
    elif n == 1:
        r = math.cos(math.pi * (y - .5))
    elif n == 2:
        r = math.sin(math.pi * (1. - y))
    elif n == 3:
        r = -math.cos(math.pi * (y - 1.5))
    elif n == 4:
        r = math.sin(math.pi * (y - 2.))
    else:
        raise AssertionError("should not reach")
    return rfloat.copysign(1., x) * r

_lanczos_g = 6.024680040776729583740234375
_lanczos_g_minus_half = 5.524680040776729583740234375
_lanczos_num_coeffs = [
    23531376880.410759688572007674451636754734846804940,
    42919803642.649098768957899047001988850926355848959,
    35711959237.355668049440185451547166705960488635843,
    17921034426.037209699919755754458931112671403265390,
    6039542586.3520280050642916443072979210699388420708,
    1439720407.3117216736632230727949123939715485786772,
    248874557.86205415651146038641322942321632125127801,
    31426415.585400194380614231628318205362874684987640,
    2876370.6289353724412254090516208496135991145378768,
    186056.26539522349504029498971604569928220784236328,
    8071.6720023658162106380029022722506138218516325024,
    210.82427775157934587250973392071336271166969580291,
    2.5066282746310002701649081771338373386264310793408
]
_lanczos_den_coeffs = [
    0.0, 39916800.0, 120543840.0, 150917976.0, 105258076.0, 45995730.0,
    13339535.0, 2637558.0, 357423.0, 32670.0, 1925.0, 66.0, 1.0]
LANCZOS_N = len(_lanczos_den_coeffs)
_lanczos_n_iter = unroll.unrolling_iterable(range(LANCZOS_N))
_lanczos_n_iter_back = unroll.unrolling_iterable(range(LANCZOS_N - 1, -1, -1))
_gamma_integrals = [
    1.0, 1.0, 2.0, 6.0, 24.0, 120.0, 720.0, 5040.0, 40320.0, 362880.0,
    3628800.0, 39916800.0, 479001600.0, 6227020800.0, 87178291200.0,
    1307674368000.0, 20922789888000.0, 355687428096000.0,
    6402373705728000.0, 121645100408832000.0, 2432902008176640000.0,
    51090942171709440000.0, 1124000727777607680000.0]

def _lanczos_sum(x):
    num = 0.
    den = 0.
    assert x > 0.
    if x < 5.:
        for i in _lanczos_n_iter_back:
            num = num * x + _lanczos_num_coeffs[i]
            den = den * x + _lanczos_den_coeffs[i]
    else:
        for i in _lanczos_n_iter:
            num = num / x + _lanczos_num_coeffs[i]
            den = den / x + _lanczos_den_coeffs[i]
    return num / den

def _gamma(x):
    if rfloat.isnan(x) or (rfloat.isinf(x) and x > 0.):
        return x
    if rfloat.isinf(x):
        raise ValueError("math domain error")
    if x == 0.:
        raise ValueError("math domain error")
    if x == math.floor(x):
        if x < 0.:
            raise ValueError("math domain error")
        if x < len(_gamma_integrals):
            return _gamma_integrals[int(x) - 1]
    absx = abs(x)
    if absx < 1e-20:
        r = 1. / x
        if rfloat.isinf(r):
            raise OverflowError("math range error")
        return r
    if absx > 200.:
        if x < 0.:
            return 0. / -_sinpi(x)
        else:
            raise OverflowError("math range error")
    y = absx + _lanczos_g_minus_half
    if absx > _lanczos_g_minus_half:
        q = y - absx
        z = q - _lanczos_g_minus_half
    else:
        q = y - _lanczos_g_minus_half
        z = q - absx
    z = z * _lanczos_g / y
    if x < 0.:
        r = -math.pi / _sinpi(absx) / absx * math.exp(y) / _lanczos_sum(absx)
        r -= z * r
        if absx < 140.:
            r /= math.pow(y, absx - .5)
        else:
            sqrtpow = math.pow(y, absx / 2. - .25)
            r /= sqrtpow
            r /= sqrtpow
    else:
        r = _lanczos_sum(absx) / math.exp(y)
        r += z * r
        if absx < 140.:
            r *= math.pow(y, absx - .5)
        else:
            sqrtpow = math.pow(y, absx / 2. - .25)
            r *= sqrtpow
            r *= sqrtpow
    if rfloat.isinf(r):
        raise OverflowError("math range error")
    return r

def _lgamma(x):
    if rfloat.isnan(x):
        return x
    if rfloat.isinf(x):
        return rfloat.INFINITY
    if x == math.floor(x) and x <= 2.:
        if x <= 0.:
            raise ValueError("math range error")
        return 0.
    absx = abs(x)
    if absx < 1e-20:
        return -math.log(absx)
    if x > 0.:
        r = (math.log(_lanczos_sum(x)) - _lanczos_g + (x - .5) *
             (math.log(x + _lanczos_g - .5) - 1))
    else:
        r = (math.log(math.pi) - math.log(abs(_sinpi(absx))) - math.log(absx) -
             (math.log(_lanczos_sum(absx)) - _lanczos_g +
              (absx - .5) * (math.log(absx + _lanczos_g - .5) - 1)))
    if rfloat.isinf(r):
        raise OverflowError("math domain error")
    return r

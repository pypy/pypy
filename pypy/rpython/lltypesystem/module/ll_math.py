import math
import errno
import py
import sys

from pypy.rpython.lltypesystem import lltype, rffi
from pypy.tool.sourcetools import func_with_new_name
from pypy.tool.autopath import pypydir
from pypy.rlib import jit, rposix
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.platform import platform
from pypy.rlib.rfloat import isfinite, isinf, isnan, INFINITY, NAN

if sys.platform == "win32":
    if platform.name == "msvc":
        # When compiled with /O2 or /Oi (enable intrinsic functions)
        # It's no more possible to take the address of some math functions.
        # Ensure that the compiler chooses real functions instead.
        eci = ExternalCompilationInfo(
            includes = ['math.h'],
            post_include_bits = ['#pragma function(floor)'],
            )
    else:
        eci = ExternalCompilationInfo()
    # Some math functions are C99 and not defined by the Microsoft compiler
    cdir = py.path.local(pypydir).join('translator', 'c')
    math_eci = ExternalCompilationInfo(
        include_dirs = [cdir],
        includes = ['src/ll_math.h'],
        separate_module_files=[cdir.join('src', 'll_math.c')],
        export_symbols=['_pypy_math_acosh', '_pypy_math_asinh',
                        '_pypy_math_atanh',
                        '_pypy_math_expm1', '_pypy_math_log1p'],
        )
    math_prefix = '_pypy_math_'
else:
    eci = ExternalCompilationInfo(
        libraries=['m'])
    math_eci = eci
    math_prefix = ''

def llexternal(name, ARGS, RESULT, **kwargs):
    return rffi.llexternal(name, ARGS, RESULT, compilation_info=eci,
                           sandboxsafe=True, **kwargs)

def math_llexternal(name, ARGS, RESULT):
    return rffi.llexternal(math_prefix + name, ARGS, RESULT,
                           compilation_info=math_eci,
                           sandboxsafe=True)

if sys.platform == 'win32':
    underscore = '_'
else:
    underscore = ''

math_fabs = llexternal('fabs', [rffi.DOUBLE], rffi.DOUBLE)
math_log = llexternal('log', [rffi.DOUBLE], rffi.DOUBLE)
math_log10 = llexternal('log10', [rffi.DOUBLE], rffi.DOUBLE)
math_copysign = llexternal(underscore + 'copysign',
                           [rffi.DOUBLE, rffi.DOUBLE], rffi.DOUBLE,
                           pure_function=True)
math_atan2 = llexternal('atan2', [rffi.DOUBLE, rffi.DOUBLE], rffi.DOUBLE)
math_frexp = llexternal('frexp', [rffi.DOUBLE, rffi.INTP], rffi.DOUBLE)
math_modf  = llexternal('modf',  [rffi.DOUBLE, rffi.DOUBLEP], rffi.DOUBLE)
math_ldexp = llexternal('ldexp', [rffi.DOUBLE, rffi.INT], rffi.DOUBLE)
math_pow   = llexternal('pow', [rffi.DOUBLE, rffi.DOUBLE], rffi.DOUBLE)
math_fmod  = llexternal('fmod',  [rffi.DOUBLE, rffi.DOUBLE], rffi.DOUBLE)
math_hypot = llexternal(underscore + 'hypot',
                        [rffi.DOUBLE, rffi.DOUBLE], rffi.DOUBLE)
math_floor = llexternal('floor', [rffi.DOUBLE], rffi.DOUBLE, pure_function=True)

math_sqrt = llexternal('sqrt', [rffi.DOUBLE], rffi.DOUBLE)

@jit.purefunction
def sqrt_nonneg(x):
    return math_sqrt(x)
sqrt_nonneg.oopspec = "math.sqrt_nonneg(x)"

# ____________________________________________________________
#
# Error handling functions

ERANGE = errno.ERANGE
EDOM   = errno.EDOM

def _error_reset():
    rposix.set_errno(0)

def _likely_raise(errno, x):
    """Call this with errno != 0.  It usually raises the proper RPython
    exception, but may also just ignore it and return in case of underflow.
    """
    assert errno
    if errno == ERANGE:
        # We consider underflow to not be an error, like CPython.
        # On some platforms (Ubuntu/ia64) it seems that errno can be
        # set to ERANGE for subnormal results that do *not* underflow
        # to zero.  So to be safe, we'll ignore ERANGE whenever the
        # function result is less than one in absolute value.
        if math_fabs(x) < 1.0:
            return
        raise OverflowError("math range error")
    else:
        raise ValueError("math domain error")

# ____________________________________________________________
#
# Custom implementations

def ll_math_isnan(y):
    # By not calling into the external function the JIT can inline this.
    # Floats are awesome.
    return y != y

def ll_math_isinf(y):
    # Use a bitwise OR so the JIT doesn't produce 2 different guards.
    return (y == INFINITY) | (y == -INFINITY)

def ll_math_isfinite(y):
    # Use a custom hack that is reasonably well-suited to the JIT.
    # Floats are awesome (bis).
    z = 0.0 * y
    return z == z       # i.e.: z is not a NaN


ll_math_floor = math_floor

ll_math_copysign = math_copysign


def ll_math_atan2(y, x):
    """wrapper for atan2 that deals directly with special cases before
    delegating to the platform libm for the remaining cases.  This
    is necessary to get consistent behaviour across platforms.
    Windows, FreeBSD and alpha Tru64 are amongst platforms that don't
    always follow C99.
    """
    if isnan(x) or isnan(y):
        return NAN

    if isinf(y):
        if isinf(x):
            if math_copysign(1.0, x) == 1.0:
                # atan2(+-inf, +inf) == +-pi/4
                return math_copysign(0.25 * math.pi, y)
            else:
                # atan2(+-inf, -inf) == +-pi*3/4
                return math_copysign(0.75 * math.pi, y)
        # atan2(+-inf, x) == +-pi/2 for finite x
        return math_copysign(0.5 * math.pi, y)

    if isinf(x) or y == 0.0:
        if math_copysign(1.0, x) == 1.0:
            # atan2(+-y, +inf) = atan2(+-0, +x) = +-0.
            return math_copysign(0.0, y)
        else:
            # atan2(+-y, -inf) = atan2(+-0., -x) = +-pi.
            return math_copysign(math.pi, y)

    return math_atan2(y, x)


# XXX Various platforms (Solaris, OpenBSD) do nonstandard things for log(0),
# log(-ve), log(NaN).  For now I'm ignoring this issue as these are a bit
# more marginal platforms for us.


def ll_math_frexp(x):
    # deal with special cases directly, to sidestep platform differences
    if isnan(x) or isinf(x) or not x:
        mantissa = x
        exponent = 0
    else:
        exp_p = lltype.malloc(rffi.INTP.TO, 1, flavor='raw')
        try:
            mantissa = math_frexp(x, exp_p)
            exponent = rffi.cast(lltype.Signed, exp_p[0])
        finally:
            lltype.free(exp_p, flavor='raw')
    return (mantissa, exponent)


INT_MAX = int(2**31-1)
INT_MIN = int(-2**31)

def ll_math_ldexp(x, exp):
    if x == 0.0 or isinf(x) or isnan(x):
        return x    # NaNs, zeros and infinities are returned unchanged
    if exp > INT_MAX:
        # overflow (64-bit platforms only)
        r = math_copysign(INFINITY, x)
        errno = ERANGE
    elif exp < INT_MIN:
        # underflow to +-0 (64-bit platforms only)
        r = math_copysign(0.0, x)
        errno = 0
    else:
        _error_reset()
        r = math_ldexp(x, exp)
        errno = rposix.get_errno()
        if isinf(r):
            errno = ERANGE
    if errno:
        _likely_raise(errno, r)
    return r


def ll_math_modf(x):
    # some platforms don't do the right thing for NaNs and
    # infinities, so we take care of special cases directly.
    if isinf(x):
        return (math_copysign(0.0, x), x)
    elif isnan(x):
        return (x, x)
    intpart_p = lltype.malloc(rffi.DOUBLEP.TO, 1, flavor='raw')
    try:
        fracpart = math_modf(x, intpart_p)
        intpart = intpart_p[0]
    finally:
        lltype.free(intpart_p, flavor='raw')
    return (fracpart, intpart)


def ll_math_copysign(x, y):
    return math_copysign(x, y)     # no error checking needed


def ll_math_fmod(x, y):
    if isinf(y):
        if isinf(x):
            raise ValueError("math domain error")
        return x  # fmod(x, +/-Inf) returns x for finite x (or if x is a NaN).

    _error_reset()
    r = math_fmod(x, y)
    errno = rposix.get_errno()
    if isnan(r):
        if isnan(x) or isnan(y):
            errno = 0
        else:
            errno = EDOM
    if errno:
        _likely_raise(errno, r)
    return r


def ll_math_hypot(x, y):
    # hypot(x, +/-Inf) returns Inf, even if x is a NaN.
    if isinf(x):
        return math_fabs(x)
    if isinf(y):
        return math_fabs(y)

    _error_reset()
    r = math_hypot(x, y)
    errno = rposix.get_errno()
    if isnan(r):
        if isnan(x) or isnan(y):
            errno = 0
        else:
            errno = EDOM
    elif isinf(r):
        if isinf(x) or isnan(x) or isinf(y) or isnan(y):
            errno = 0
        else:
            errno = ERANGE
    if errno:
        _likely_raise(errno, r)
    return r


def ll_math_pow(x, y):
    # deal directly with IEEE specials, to cope with problems on various
    # platforms whose semantics don't exactly match C99

    if isnan(x):
        if y == 0.0:
            return 1.0   # NaN**0 = 1
        return x

    elif isnan(y):
        if x == 1.0:
            return 1.0   # 1**Nan = 1
        return y

    elif isinf(x):
        odd_y = not isinf(y) and math_fmod(math_fabs(y), 2.0) == 1.0
        if y > 0.0:
            if odd_y:
                return x
            return math_fabs(x)
        elif y == 0.0:
            return 1.0
        else:   # y < 0.0
            if odd_y:
                return math_copysign(0.0, x)
            return 0.0

    elif isinf(y):
        if math_fabs(x) == 1.0:
            return 1.0
        elif y > 0.0 and math_fabs(x) > 1.0:
            return y
        elif y < 0.0 and math_fabs(x) < 1.0:
            if x == 0.0:
                raise ValueError("0**-inf: divide by zero")
            return -y    # result is +inf
        else:
            return 0.0

    _error_reset()
    r = math_pow(x, y)
    errno = rposix.get_errno()
    if isnan(r):
        # a NaN result should arise only from (-ve)**(finite non-integer)
        errno = EDOM
    elif isinf(r):
        # an infinite result here arises either from:
        # (A) (+/-0.)**negative (-> divide-by-zero)
        # (B) overflow of x**y with x and y finite
        if x == 0.0:
            errno = EDOM
        else:
            errno = ERANGE
    if errno:
        _likely_raise(errno, r)
    return r

def ll_math_sqrt(x):
    if x < 0.0:
        raise ValueError, "math domain error"
    
    if isfinite(x):
        return sqrt_nonneg(x)

    return x   # +inf or nan

# ____________________________________________________________
#
# Default implementations

def new_unary_math_function(name, can_overflow, c99):
    if sys.platform == 'win32' and c99:
        c_func = math_llexternal(name, [rffi.DOUBLE], rffi.DOUBLE)
    else:
        c_func = llexternal(name, [rffi.DOUBLE], rffi.DOUBLE)

    def ll_math(x):
        _error_reset()
        r = c_func(x)
        # Error checking fun.  Copied from CPython 2.6
        errno = rposix.get_errno()
        if isnan(r):
            if isnan(x):
                errno = 0
            else:
                errno = EDOM
        elif isinf(r):
            if isinf(x) or isnan(x):
                errno = 0
            elif can_overflow:
                errno = ERANGE
            else:
                errno = EDOM
        if errno:
            _likely_raise(errno, r)
        return r

    return func_with_new_name(ll_math, 'll_math_' + name)

# ____________________________________________________________

unary_math_functions = [
    'acos', 'asin', 'atan',
    'ceil', 'cos', 'cosh', 'exp', 'fabs',
    'sin', 'sinh', 'tan', 'tanh', 'log', 'log10',
    'acosh', 'asinh', 'atanh', 'log1p', 'expm1',
    ]
unary_math_functions_can_overflow = [
    'cosh', 'exp', 'log1p', 'sinh', 'expm1',
    ]
unary_math_functions_c99 = [
    'acosh', 'asinh', 'atanh', 'log1p', 'expm1',
    ]

for name in unary_math_functions:
    can_overflow = name in unary_math_functions_can_overflow
    c99 = name in unary_math_functions_c99
    globals()['ll_math_' + name] = new_unary_math_function(name, can_overflow, c99)

import math
import errno
import py
import sys

from pypy.rpython.lltypesystem import lltype, rffi
from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib import rposix
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rlib.rarithmetic import isinf

math_frexp = rffi.llexternal('frexp', [rffi.DOUBLE, rffi.INTP], rffi.DOUBLE,
                             sandboxsafe=True)
math_modf  = rffi.llexternal('modf',  [rffi.DOUBLE, rffi.DOUBLEP], rffi.DOUBLE,
                             sandboxsafe=True)
math_ldexp = rffi.llexternal('ldexp', [rffi.DOUBLE, rffi.INT], rffi.DOUBLE,
                             sandboxsafe=True)

unary_math_functions = [
    'acos', 'asin', 'atan', 'ceil', 'cos', 'cosh', 'exp', 'fabs',
    'floor', 'log', 'log10', 'sin', 'sinh', 'sqrt', 'tan', 'tanh'
    ]

binary_math_functions = [
    'atan2', 'fmod', 'hypot', 'pow'
    ]

def ll_math_frexp(x):
    exp_p = lltype.malloc(rffi.INTP.TO, 1, flavor='raw')
    try:
        _error_reset()
        mantissa = math_frexp(x, exp_p)
        _check_error(mantissa)
        exponent = rffi.cast(lltype.Signed, exp_p[0])
    finally:
        lltype.free(exp_p, flavor='raw')
    return (mantissa, exponent)

def ll_math_modf(x):
    intpart_p = lltype.malloc(rffi.DOUBLEP.TO, 1, flavor='raw')
    try:
        _error_reset()
        fracpart = math_modf(x, intpart_p)
        _check_error(fracpart)
        intpart = intpart_p[0]
    finally:
        lltype.free(intpart_p, flavor='raw')
    return (fracpart, intpart)

def ll_math_ldexp(x, exp):
    _error_reset()
    r = math_ldexp(x, exp)
    _check_error(r)
    return r

def _error_reset():
    rposix.set_errno(0)

ERANGE = errno.ERANGE
def _check_error(x):
    errno = rposix.get_errno()
    if isinf(x):
        errno = ERANGE
    if errno:
        if errno == ERANGE:
            if not x:
                return # we consider underflow to not be an error, like CPython
            raise OverflowError("math range error")
        else:
            raise ValueError("math domain error")

if sys.platform[:3] == "win":
    eci = ExternalCompilationInfo(libraries=[])
else:
    eci = ExternalCompilationInfo(libraries=['m'])


def new_unary_math_function(name):
    c_func = rffi.llexternal(name, [rffi.DOUBLE], rffi.DOUBLE,
                             compilation_info=eci, sandboxsafe=True)

    def ll_math(x):
        _error_reset()
        r = c_func(x)
        _check_error(r)
        return r

    return func_with_new_name(ll_math, 'll_math_' + name)

def new_binary_math_function(name):
    if sys.platform == 'win32' and name in ('hypot',):
        cname = '_' + name
    else:
        cname = name
    c_func = rffi.llexternal(cname, [rffi.DOUBLE, rffi.DOUBLE], rffi.DOUBLE,
                             compilation_info=eci, sandboxsafe=True)

    def ll_math(x, y):
        _error_reset()
        r = c_func(x, y)
        _check_error(r)
        return r

    return func_with_new_name(ll_math, 'll_math_' + name)

# the two above are almost the same, but they're C-c C-v not to go mad
# with meta-programming

for name in unary_math_functions:
    globals()['ll_math_' + name] = new_unary_math_function(name)
    
for name in binary_math_functions:
    globals()['ll_math_' + name] = new_binary_math_function(name)
    

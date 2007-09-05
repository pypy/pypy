# this registry use the new interface for external functions
# all the above declarations in extfunctable should be moved here at some point.

from extfunc import register_external

# ___________________________
# math functions

import math
from pypy.rpython.lltypesystem.module import ll_math
from pypy.rpython.ootypesystem.module import ll_math as oo_math
from pypy.rpython.module import ll_os
from pypy.rpython.module import ll_time
try:
    import termios
except ImportError:
    pass
else:
    from pypy.rpython.module import ll_termios

# the following functions all take one float, return one float
# and are part of math.h
simple_math_functions = [
    'acos', 'asin', 'atan', 'ceil', 'cos', 'cosh', 'exp', 'fabs',
    'floor', 'log', 'log10', 'sin', 'sinh', 'sqrt', 'tan', 'tanh'
    ]
for name in simple_math_functions:
    register_external(getattr(math, name), [float], float,
                      "ll_math.ll_math_%s" % name,
                       sandboxsafe=True)

complex_math_functions = [
    ('frexp', [float],        (float, int)),
    ('atan2', [float, float], float),
    ('fmod',  [float, float], float),
    ('ldexp', [float, int],   float),
    ('modf',  [float],        (float, float)),
    ('hypot', [float, float], float),
    ('pow',   [float, float], float),
    ]

for name, args, res in complex_math_functions:
    func = getattr(math, name)
    llimpl = getattr(ll_math, 'll_math_%s' % name, None)
    oofake = getattr(oo_math, 'll_math_%s' % name, None)
    register_external(func, args, res, 'll_math.ll_math_%s' % name,
                      llimpl=llimpl, oofakeimpl=oofake,
                      sandboxsafe=True)


# ___________________________
# os.path functions

from pypy.tool.sourcetools import func_with_new_name
import os.path

# os.path.join is RPython, but we don't want to compile it directly
# because it's platform dependant. This is ok for lltype where the
# execution platform is the same as the translation platform, but not
# for ootype where the executable produced by some backends (e.g. CLI,
# JVM) are expected to run everywhere.  Thus, we register it as an
# external function, but we provide a clone for lltype using
# func_with_new_name.

# XXX: I can't see any easy way to provide an oofakeimpl for the
# llinterpreter

path_functions = [
    ('join',     [str, str], str),
    ]

for name, args, res in path_functions:
    func = getattr(os.path, name)
    llimpl = func_with_new_name(func, name)
    register_external(func, args, res, 'll_os_path.ll_%s' % name,
                      llimpl=llimpl, sandboxsafe=True)

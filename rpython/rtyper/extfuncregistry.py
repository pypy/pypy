# this registry uses the new interface for external functions

from rpython.rtyper.extfunc import register_external

# ___________________________
# math functions

import math
from rpython.rtyper.lltypesystem.module import ll_math
from rpython.rtyper.module import ll_os
from rpython.rtyper.module import ll_time
from rpython.rlib import rfloat
try:
    import termios
except ImportError:
    pass
else:
    from rpython.rtyper.module import ll_termios

# the following functions all take one float, return one float
# and are part of math.h
for name in ll_math.unary_math_functions:
    llimpl = getattr(ll_math, 'll_math_%s' % name, None)
    try:
        f = getattr(math, name)
    except AttributeError:
        f = getattr(rfloat, name)
    register_external(f, [float], float,
                      export_name="ll_math.ll_math_%s" % name,
                       sandboxsafe=True, llimpl=llimpl)

_register = [  # (module, [(method name, arg types, return type), ...], ...)
    (rfloat, [
        ('isinf', [float], bool),
        ('isnan', [float], bool),
        ('isfinite', [float], bool),
        ('copysign', [float, float], float),
    ]),
    (math, [
       ('floor', [float], float),
       ('sqrt', [float], float),
       ('log', [float], float),
       ('log10', [float], float),
       ('log1p', [float], float),
       ('sin', [float], float),
       ('cos', [float], float),
       ('atan2', [float, float], float),
       ('hypot', [float, float], float),
       ('frexp', [float], (float, int)),
       ('ldexp', [float, int], float),
       ('modf', [float], (float, float)),
       ('fmod', [float, float], float),
       ('pow', [float, float], float),
    ]),
]
for module, methods in _register:
    for name, arg_types, return_type in methods:
        method_name = 'll_math_%s' % name
        register_external(getattr(module, name), arg_types, return_type,
                          export_name='ll_math.%s' % method_name,
                          sandboxsafe=True,
                          llimpl=getattr(ll_math, method_name))


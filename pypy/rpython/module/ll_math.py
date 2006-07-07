import math
import py

simple_math_functions = [
    'acos', 'asin', 'atan', 'ceil', 'cos', 'cosh', 'exp', 'fabs',
    'floor', 'log', 'log10', 'sin', 'sinh', 'sqrt', 'tan', 'tanh'
    ]

for name in simple_math_functions:
    exec py.code.Source("""
    def ll_math_%(name)s(x):
        return math.%(name)s(x)
    ll_math_%(name)s.suggested_primitive = True
    """ % {"name": name}).compile()

def ll_math_pow(x, y):
    return math.pow(x, y)
ll_math_pow.suggested_primitive = True

def ll_math_atan2(x, y):
    return math.atan2(x, y)
ll_math_atan2.suggested_primitive = True

def ll_math_fmod(x, y):
    return math.fmod(x, y)
ll_math_fmod.suggested_primitive = True

def ll_math_ldexp(x, y):
    return math.ldexp(x, y)
ll_math_ldexp.suggested_primitive = True

def ll_math_hypot(x, y):
    return math.hypot(x, y)
ll_math_hypot.suggested_primitive = True

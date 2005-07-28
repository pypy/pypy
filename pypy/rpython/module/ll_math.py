from pypy.rpython import lltype

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


FREXP_RESULT = lltype.GcStruct('tuple2', ('item0', lltype.Float),
                               ('item1', lltype.Signed))

def ll_frexp_result(mantissa, exponent):
    tup = lltype.malloc(FREXP_RESULT)
    tup.item0 = mantissa
    tup.item1 = exponent
    return tup
    
def ll_math_frexp(x):
    mantissa, exponent = math.frexp(x)
    return ll_frexp_result(mantissa, exponent)
ll_math_frexp.suggested_primitive = True

def ll_math_atan2(x, y):
    return math.atan2(x, y)
ll_math_atan2.suggested_primitive = True

def ll_math_fmod(x, y):
    return math.fmod(x, y)
ll_math_fmod.suggested_primitive = True

def ll_math_ldexp(x, y):
    return math.ldexp(x, y)
ll_math_ldexp.suggested_primitive = True

MODF_RESULT = lltype.GcStruct('tuple2', ('item0', lltype.Float),
                       ('item1', lltype.Float))

def ll_modf_result(fracpart, intpart):
    tup = lltype.malloc(MODF_RESULT)
    tup.item0 = fracpart
    tup.item1 = intpart
    return tup

def ll_math_modf(x):
    fracpart, intpart = math.modf(x)
    return ll_modf_result(fracpart, intpart)
ll_math_modf.suggested_primitive = True

def ll_math_hypot(x, y):
    return math.hypot(x, y)
ll_math_hypot.suggested_primitive = True

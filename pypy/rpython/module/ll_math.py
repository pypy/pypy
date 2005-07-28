from pypy.rpython import lltype

import math

def ll_math_cos(x):
    return math.cos(x)
ll_math_cos.suggested_primitive = True

def ll_math_sin(x):
    return math.sin(x)
ll_math_sin.suggested_primitive = True

def ll_math_acos(x):
    return math.acos(x)
ll_math_acos.suggested_primitive = True

def ll_math_sinh(x):
    return math.sinh(x)
ll_math_sinh.suggested_primitive = True

def ll_math_cosh(x):
    return math.cosh(x)
ll_math_cosh.suggested_primitive = True

def ll_math_hypot(x, y):
    return math.hypot(x, y)
ll_math_hypot.suggested_primitive = True

def ll_math_sqrt(x):
    return math.sqrt(x)
ll_math_sqrt.suggested_primitive = True

def ll_math_log(x):
    return math.log(x)
ll_math_log.suggested_primitive = True

def ll_math_log10(x):
    return math.log10(x)
ll_math_log10.suggested_primitive = True

def ll_math_ceil(x):
    return math.ceil(x)
ll_math_ceil.suggested_primitive = True


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

def ll_math_floor(x):
    return math.floor(x)
ll_math_floor.suggested_primitive = True

def ll_math_exp(x):
    return math.exp(x)

def ll_math_ldexp(x, y):
    return math.ldexp(x, y)

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

def ll_math_fabs(x):
    return math.fabs(x)
ll_math_fabs.suggested_primitive = True

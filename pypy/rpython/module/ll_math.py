from pypy.rpython import lltype

import math

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
ll_modf_result.suggested_primitive = True

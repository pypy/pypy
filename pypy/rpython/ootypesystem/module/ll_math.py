import math
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.rtupletype import TUPLE_TYPE

FREXP_RESULT = TUPLE_TYPE([ootype.Float, ootype.Signed])
MODF_RESULT = TUPLE_TYPE([ootype.Float, ootype.Float])

def ll_frexp_result(mantissa, exponent):
    tup = ootype.new(FREXP_RESULT)
    tup.item0 = mantissa
    tup.item1 = exponent
    return tup

def ll_modf_result(fracpart, intpart):
    tup = ootype.new(MODF_RESULT)
    tup.item0 = fracpart
    tup.item1 = intpart
    return tup

def ll_math_frexp(x):
    mantissa, exponent = math.frexp(x)
    return ll_frexp_result(mantissa, exponent)

def ll_math_modf(x):
    fracpart, intpart = math.modf(x)
    return ll_modf_result(fracpart, intpart)


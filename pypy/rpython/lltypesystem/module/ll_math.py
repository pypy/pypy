import math

from pypy.rpython.lltypesystem import lltype, rtupletype
from pypy.tool.staticmethods import ClassMethods

FREXP_RESULT = rtupletype.TUPLE_TYPE([lltype.Float, lltype.Signed]).TO
MODF_RESULT = rtupletype.TUPLE_TYPE([lltype.Float, lltype.Float]).TO

def ll_frexp_result(mantissa, exponent):
    tup = lltype.malloc(FREXP_RESULT)
    tup.item0 = mantissa
    tup.item1 = exponent
    return tup

def ll_modf_result(fracpart, intpart):
    tup = lltype.malloc(MODF_RESULT)
    tup.item0 = fracpart
    tup.item1 = intpart
    return tup

class Implementation:
    __metaclass__ = ClassMethods

    def ll_math_frexp(cls, x):
        mantissa, exponent = math.frexp(x)
        return ll_frexp_result(mantissa, exponent)
    ll_math_frexp.suggested_primitive = True

    def ll_math_modf(cls, x):
        fracpart, intpart = math.modf(x)
        return ll_modf_result(fracpart, intpart)
    ll_math_modf.suggested_primitive = True

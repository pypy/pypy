import math

from pypy.rpython.ootypesystem import ootype
from pypy.tool.staticmethods import ClassMethods

FREXP_RESULT = ootype.Record({"item0": ootype.Float, "item1": ootype.Signed})
MODF_RESULT = ootype.Record({"item0": ootype.Float, "item1": ootype.Float})

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

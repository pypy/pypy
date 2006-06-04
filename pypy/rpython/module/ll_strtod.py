# string -> float helper
from pypy.rpython import rarithmetic
from pypy.rpython.module.support import LLSupport, ll_strcpy


def ll_strtod_parts_to_float(sign, beforept, afterpt, exponent):
    return rarithmetic.parts_to_float(LLSupport.from_rstr(sign),
                                      LLSupport.from_rstr(beforept),
                                      LLSupport.from_rstr(afterpt),
                                      LLSupport.from_rstr(exponent))
ll_strtod_parts_to_float.suggested_primitive = True

def ll_strtod_formatd(fmt, x):
    return LLSupport.to_rstr(rarithmetic.formatd(LLSupport.from_rstr(fmt), x))
ll_strtod_formatd.suggested_primitive = True

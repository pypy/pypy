# string -> float helper
from pypy.rpython import rarithmetic
from pypy.rpython.module.support import to_rstr, from_rstr, ll_strcpy


def ll_strtod_parts_to_float(sign, beforept, afterpt, exponent):
    return rarithmetic.parts_to_float(from_rstr(sign),
                                      from_rstr(beforept),
                                      from_rstr(afterpt),
                                      from_rstr(exponent))
ll_strtod_parts_to_float.suggested_primitive = True

def ll_strtod_formatd(fmt, x):
    return to_rstr(rarithmetic.formatd(from_rstr(fmt), x))
ll_strtod_formatd.suggested_primitive = True

from pypy.rlib import rarithmetic
from pypy.rpython.module.support import LLSupport
from pypy.tool.staticmethods import ClassMethods

class Implementation:
    def ll_strtod_formatd(fmt, x):
        return LLSupport.to_rstr(rarithmetic.formatd(LLSupport.from_rstr(fmt), x))
    ll_strtod_formatd.suggested_primitive = True
    ll_strtod_formatd = staticmethod(ll_strtod_formatd)

    def ll_strtod_parts_to_float(sign, beforept, afterpt, exponent):
        return rarithmetic.parts_to_float(LLSupport.from_rstr(sign),
                                          LLSupport.from_rstr(beforept),
                                          LLSupport.from_rstr(afterpt),
                                          LLSupport.from_rstr(exponent))
    ll_strtod_parts_to_float.suggested_primitive = True
    ll_strtod_parts_to_float = staticmethod(ll_strtod_parts_to_float)

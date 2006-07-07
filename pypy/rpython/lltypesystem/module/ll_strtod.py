from pypy.rpython import rarithmetic
from pypy.rpython.module.support import LLSupport
from pypy.tool.staticmethods import ClassMethods

class Implementation:
    def ll_strtod_formatd(fmt, x):
        return LLSupport.to_rstr(rarithmetic.formatd(LLSupport.from_rstr(fmt), x))
    ll_strtod_formatd.suggested_primitive = True
    ll_strtod_formatd = staticmethod(ll_strtod_formatd)
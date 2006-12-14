from pypy.rlib import rarithmetic
from pypy.rpython.module.support import OOSupport
from pypy.tool.staticmethods import ClassMethods

class Implementation(object, OOSupport):
    __metaclass__ = ClassMethods

    def ll_strtod_formatd(cls, fmt, x):
        return cls.to_rstr(rarithmetic.formatd(cls.from_rstr(fmt), x))
    ll_strtod_formatd.suggested_primitive = True


    def ll_strtod_parts_to_float(cls, sign, beforept, afterpt, exponent):
        return rarithmetic.parts_to_float(cls.from_rstr(sign),
                                          cls.from_rstr(beforept),
                                          cls.from_rstr(afterpt),
                                          cls.from_rstr(exponent))
    ll_strtod_parts_to_float.suggested_primitive = True

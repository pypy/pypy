from pypy.rpython import rarithmetic
from pypy.rpython.module.support import OOSupport
from pypy.tool.staticmethods import ClassMethods

class Implementation(object, OOSupport):
    __metaclass__ = ClassMethods

    def ll_strtod_formatd(cls, fmt, x):
        return cls.to_rstr(rarithmetic.formatd(cls.from_rstr(fmt), x))
    ll_strtod_formatd.suggested_primitive = True

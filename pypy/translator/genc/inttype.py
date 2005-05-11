from __future__ import generators
from pypy.annotation.model import SomeInteger
from pypy.translator.genc.basetype import CType


class CIntType(CType):
    typename      = 'int'
    error_return  = '-1'
    s_annotation  = SomeInteger()

    def nameof(self, v, debug=None):
        return '%d' % (v,)


class CUnsignedType(CType):
    typename      = 'unsigned'
    error_return  = '-1'
    s_annotation  = SomeInteger(nonneg=True, unsigned=True)

    def nameof(self, v, debug=None):
        assert v >= 0
        return '%d' % (v,)

from __future__ import generators
from pypy.annotation.model import SomePBC
from pypy.translator.genc.basetype import CType


class CNoneType(CType):
    typename      = 'none'
    error_return  = '-1'
    s_annotation  = SomePBC({None: True})

    def nameof(self, v, debug=None):
        assert v is None
        return '0'

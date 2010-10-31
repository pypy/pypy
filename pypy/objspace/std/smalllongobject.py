"""
Implementation of 'small' longs, stored as a C 'long long' value.
Useful for 32-bit applications manipulating 64-bit values.
"""
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.rlib.rarithmetic import r_longlong


class W_SmallLongObject(W_Object):
    from pypy.objspace.std.longtype import long_typedef as typedef

    def __init__(w_self, value):
        assert isinstance(value, r_longlong)
        w_self._longlong = value

    def as_bigint(w_self):
        xxx

registerimplementation(W_SmallLongObject)

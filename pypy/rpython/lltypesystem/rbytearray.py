
from pypy.rpython.rbytearray import AbstractByteArrayRepr
from pypy.rpython.lltypesystem import lltype

BYTEARRAY = lltype.GcArray(lltype.Char)

class ByteArrayRepr(AbstractByteArrayRepr):
    lowleveltype = lltype.Ptr(BYTEARRAY)

    def convert_const(self, value):
        if value is None:
            return lltype.nullptr(BYTEARRAY)
        p = lltype.malloc(BYTEARRAY, len(value))
        for i, c in enumerate(value):
            p[i] = chr(c)
        return p

bytearray_repr = ByteArrayRepr()

def hlbytearray(ll_b):
    b = bytearray()
    for i in range(len(ll_b)):
        b.append(ll_b[i])
    return b

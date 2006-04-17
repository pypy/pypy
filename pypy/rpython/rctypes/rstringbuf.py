from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rctypes.rmodel import CTypesRefRepr


class StringBufRepr(CTypesRefRepr):
    pass


STRBUFTYPE = lltype.Array(lltype.Char)

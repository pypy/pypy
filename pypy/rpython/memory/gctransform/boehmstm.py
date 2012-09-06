from pypy.rpython.memory.gctransform.boehm import BoehmGCTransformer
from pypy.rpython.lltypesystem import lltype
from pypy.rlib.rarithmetic import r_uint, LONG_BIT


_first_gcflag            = 1 << (LONG_BIT//2)
GCFLAG_GLOBAL            = _first_gcflag << 0
GCFLAG_NOT_WRITTEN       = _first_gcflag << 2

GCFLAG_PREBUILT          = GCFLAG_GLOBAL|GCFLAG_NOT_WRITTEN
REV_INITIAL              = r_uint(1)


class BoehmSTMGCTransformer(BoehmGCTransformer):
    HDR = lltype.Struct("header", ("hash", lltype.Signed),
                                  ("tid", lltype.Signed),    # for flags only
                                  ("revision", lltype.Unsigned))

    def gcheader_initdata(self, hdr):
        hdr.tid = GCFLAG_PREBUILT
        hdr.revision = REV_INITIAL

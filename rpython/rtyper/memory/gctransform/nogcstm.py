from rpython.rtyper.memory.gctransform.boehm import BoehmGCTransformer
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rlib.rarithmetic import r_uint, LONG_BIT


_first_gcflag            = 1 << (LONG_BIT//2)
GCFLAG_GLOBAL            = _first_gcflag << 0
GCFLAG_NOT_WRITTEN       = _first_gcflag << 2

GCFLAG_PREBUILT          = GCFLAG_GLOBAL|GCFLAG_NOT_WRITTEN
REV_INITIAL              = r_uint(1)


class NoneSTMGCTransformer(BoehmGCTransformer):
    HDR = lltype.Struct("header", ("hash", lltype.Signed),
                                  ("size", lltype.Signed),
                                  ("tid", lltype.Signed),    # for flags only
                                  ("revision", lltype.Unsigned))

    def gcheader_initdata(self, hdr, ptr):
        ptr = lltype.normalizeptr(ptr)
        TYPE = lltype.typeOf(ptr).TO
        if TYPE._is_varsize():
            while isinstance(ptr._T, lltype.Struct):
                ptr = getattr(ptr, ptr._T._arrayfld)
            hdr.size = llmemory.sizeof(TYPE, len(ptr))
        else:
            hdr.size = llmemory.sizeof(TYPE)
        hdr.tid = GCFLAG_PREBUILT
        hdr.revision = REV_INITIAL

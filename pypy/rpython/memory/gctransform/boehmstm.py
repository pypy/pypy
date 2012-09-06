from pypy.rpython.memory.gctransform.boehm import BoehmGCTransformer
from pypy.rpython.lltypesystem import lltype


class BoehmSTMGCTransformer(BoehmGCTransformer):
    HDR = lltype.Struct("header", ("hash", lltype.Signed),
                                  ("tid", lltype.Signed),    # for flags only
                                  ("revision", lltype.Unsigned))

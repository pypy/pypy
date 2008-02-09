
""" Implementation of pure-rpython low-level buffer, which allows
you to take address of underlaying memory. Will be used to implement
buffer protocol on app-level
"""

from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rarithmetic import r_uint

class RBuffer:
    ll_buffer = lltype.nullptr(rffi.CCHARP.TO)
    
    def __init__(self, size, address=r_uint(0)):
        if address == 0:
            self.ll_buffer = lltype.malloc(rffi.CCHARP.TO, size,
                                           zero=True, flavor='raw')
        else:
            self.ll_buffer = rffi.cast(rffi.CCHARP, address)
        self.size = size

    def address(self):
        return rffi.cast(rffi.UINT, self.ll_buffer)

    def getitem(self, item):
        # XXX think how to avoid multiple layers of boundary checks
        if item >= self.size or item < 0:
            raise IndexError(item)
        return self.ll_buffer[item]

    def setitem(self, item, value):
        if item >= self.size or item < 0:
            raise IndexError(item)
        self.ll_buffer[item] = value

    def free(self):
        if self.ll_buffer:
            lltype.free(self.ll_buffer, flavor='raw')
            self.ll_buffer = lltype.nullptr(rffi.CCHARP.TO)

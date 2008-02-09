
""" Implementation of pure-rpython low-level buffer, which allows
you to take address of underlaying memory. Will be used to implement
buffer protocol on app-level
"""

from pypy.rpython.lltypesystem import lltype, rffi

class RBuffer:
    ll_buffer = lltype.nullptr(rffi.CCHARP.TO)
    
    def __init__(self, size):
        self.ll_buffer = lltype.malloc(rffi.CCHARP.TO, size, flavor='raw')
        self.size = size

    def address(self):
        return rffi.cast(rffi.INT, self.ll_buffer)

    def free(self):
        if self.ll_buffer:
            lltype.free(self.ll_buffer, flavor='raw')

from pypy.interpreter.buffer import RWBuffer
from pypy.rpython.lltypesystem import lltype, rffi

CHAR_TP = lltype.Ptr(lltype.Array(lltype.Char, hints={'nolength': True}))

class NumpyBuffer(RWBuffer):
    def __init__(self, array):
        RWBuffer.__init__(self)
        self.array = array

    def getlength(self):
        return self.array.get_concrete().find_size()

    def getitem(self, index):
        if index > self.getlength() - 1:
            raise IndexError("Index out of bounds (0<=index<%d)" % self.getlength())
        storage = self.array.get_concrete().get_root_storage()
        char_data = rffi.cast(CHAR_TP, storage)
        return char_data[index]


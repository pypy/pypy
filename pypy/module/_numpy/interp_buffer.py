from pypy.interpreter.buffer import RWBuffer
from pypy.rpython.lltypesystem import lltype, rffi

CHAR_TP = lltype.Ptr(lltype.Array(lltype.Char, hints={'nolength': True}))

class NumpyBuffer(RWBuffer):
    def __init__(self, array):
        RWBuffer.__init__(self)
        self.array = array

    def getlength(self):
        return self.array.get_concrete().find_size() * self.array.find_dtype().num_bytes

    def getitem(self, index):
        index = self.calc_index(index)
        if index > self.getlength() - 1:
            raise IndexError("Index out of bounds (0<=index<%d)" % self.getlength())
        storage = self.array.get_concrete().get_root_storage()
        char_data = rffi.cast(CHAR_TP, storage)
        return char_data[index]

    def setitem(self, index, value):
        index = self.calc_index(index)
        if index > self.getlength() - 1:
            raise IndexError("Index out of bounds (0<=index<%d)" % self.getlength())
        storage = self.array.get_concrete().get_root_storage()
        char_ptr = rffi.cast(CHAR_TP, storage)
        char_ptr[index] = value

    def setslice(self, index, newstring):
        offset_index = self.calc_index(index)
        if offset_index + len(newstring) > self.getlength():
            raise IndexError("End of slice to set out of bounds (0<=index<%d)" % self.getlength())
        for idx in range(0, len(newstring)):
            self.setitem(index + idx, newstring[idx])

    def calc_index(self, index):
        return index

class NumpyViewBuffer(NumpyBuffer):
    def calc_index(self, index):
        return self.array.calc_index(index) * self.array.find_dtype().num_bytes


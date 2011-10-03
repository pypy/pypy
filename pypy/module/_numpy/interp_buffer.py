from pypy.interpreter.buffer import RWBuffer
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rstring import StringBuilder
from pypy.rlib import jit

CHAR_TP = lltype.Ptr(lltype.Array(lltype.Char, hints={'nolength': True}))

setslice_driver = jit.JitDriver(greens = ['index', 'end', 'self', 'newstring'],
                                reds = ['idx'])
getslice_driver = jit.JitDriver(greens = ['stop', 'step', 'self', 'builder'],
                                reds = ['idx'])
class NumpyBuffer(RWBuffer):
    def __init__(self, array):
        self.array = array
        storage = self.array.get_concrete().get_root_storage()
        self.char_data = rffi.cast(CHAR_TP, storage)
        self.length = self.array.get_concrete().find_size() \
                          * self.array.find_dtype().num_bytes

    def getlength(self):
        return self.length

    def getitem_noboundcheck(self, index):
        index = self.calc_index(index)
        return self.char_data[index]

    def getitem(self, index):
        if index > self.getlength():
            raise IndexError("Index out of bounds (0<=index<=%d)" % self.getlength())
        return self.getitem_noboundcheck(index)

    def setitem_noboundcheck(self, index, value):
        index = self.calc_index(index)
        self.char_data[index] = value

    def setitem(self, index, value):
        if index > self.getlength():
            raise IndexError("Index out of bounds (0<=index<=%d)" % self.getlength())
        self.setitem_noboundcheck(index, value)

    def setslice(self, index, newstring):
        if index + len(newstring) > self.getlength():
            raise IndexError("End of slice to set out of bounds (0<=index<=%d)" % self.getlength())
        idx = 0
        end = len(newstring)
        while idx < end:
            setslice_driver.jit_merge_point(self=self, newstring=newstring, index=index, end=end,
                                            idx=idx)
            self.setitem_noboundcheck(idx + index, newstring[idx])
            idx += 1

    def getslice(self, start, stop, step, size):
        builder = StringBuilder(size)

        idx = start
        while idx < stop:
            getslice_driver.jit_merge_point(self=self, builder=builder, stop=stop, step=step,
                                            idx=idx)
            builder.append(self.getitem_noboundcheck(idx))
            idx += step

        return builder.build()

    def calc_index(self, index):
        return index

class NumpyViewBuffer(NumpyBuffer):
    def calc_index(self, index):
        box_size = self.array.find_dtype().num_bytes
        # index is a byte-index, calculate the box-index from it
        box_index = index / box_size
        # and we need the byte-inside-box index, too.
        in_box_index = index % box_size
        # now we use calc_index to get the correct box_index
        offset_index = self.array.calc_index(box_index)
        return offset_index * box_size + in_box_index


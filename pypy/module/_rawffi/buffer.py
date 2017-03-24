from rpython.rtyper.lltypesystem import rffi

from pypy.interpreter.bufffer import Buffer

# XXX not the most efficient implementation


class RawFFIBuffer(Buffer):
    _immutable_ = True

    def __init__(self, datainstance):
        self.datainstance = datainstance
        self.readonly = False

    def getlength(self):
        return self.datainstance.getrawsize()

    def getformat(self):
        return self.datainstance.fmt

    #XXX we keep the default of 1 for now.  I *think* it does not make
    # sense to give another answer here without also tweaking the
    # 'shape' and 'strides'.  At least it makes memoryobject.py think the
    # buffer is not C-contiguous, which is nonsense (e.g. cast() are
    # refused).  Now, the memoryview we get from a ctypes object is the
    # one that would correspond to an array of chars of the same
    # size---which is wrong, because ctypes gives a more complicated
    # result on CPython (at least 3.5), but at least it corresponds to
    # the basics.  (For example, CPython 3.5 gives a zero-dimensional
    # memoryview if the ctypes type is not an array.)
    #def getitemsize(self):
    #    return self.datainstance.itemsize

    def getitem(self, index):
        ll_buffer = self.datainstance.ll_buffer
        return ll_buffer[index]

    def setitem(self, index, char):
        ll_buffer = self.datainstance.ll_buffer
        ll_buffer[index] = char

    def get_raw_address(self):
        ll_buffer = self.datainstance.ll_buffer
        return rffi.cast(rffi.CCHARP, ll_buffer)

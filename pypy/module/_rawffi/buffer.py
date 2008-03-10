from pypy.interpreter.buffer import RWBuffer

# XXX not the most efficient implementation


class RawFFIBuffer(RWBuffer):

    def __init__(self, datainstance):
        self.datainstance = datainstance

    def getlength(self):
        return self.datainstance.getrawsize()

    def getitem(self, index):
        ll_buffer = self.datainstance.ll_buffer
        return ll_buffer[index]

    def setitem(self, index, char):
        ll_buffer = self.datainstance.ll_buffer
        ll_buffer[index] = char

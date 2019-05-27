import sys

from pypy.module._io.interp_iobase import W_RawIOBase

class W_WinConsoleIO(W_RawIOBase):
    def __init__(self, space):
        W_RawIOBase.__init__(self, space)

    def descr_init(self, space, w_nameobj, w_mode="r", w_closefd=True, w_opener=None):
        #self.fd = -1
        #self.created = 0
        #self.readable = 0
        #self.writable = 0
        #self.closehandle = 0;
        #self.blksize = 0
        fd = space.int_w(w_nameobj)
        if self.fd < 0:
            raise oefmt(space.w_ValueError, "negative file descriptor")
        self.fd = fd

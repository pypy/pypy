import sys

from pypy.module._io.interp_iobase import W_RawIOBase
from rpython.rlib import rwin32

def _pyio_get_console_type():
    pass

class W_WinConsoleIO(W_RawIOBase):
    def __init__(self, space):
        W_RawIOBase.__init__(self, space)

    def descr_init(self, space, w_nameobj, w_mode="r", w_closefd=True, w_opener=None):
        #self.fd = -1
        #self.created = 0
        self.readable = False
        self.writable = False
        #self.closehandle = 0;
        #self.blksize = 0
        rwa = False
        console_type = '\0'
        self.fd = space.int_w(w_nameobj)
        if self.fd < 0:
            decodedname = space.fsdecode_w(w_nameobj)
            name = rffi.cast(rffi.CWCHARP, decodedname)
            console_type = _pyio_get_console_type(decodedname)
            if not console_type:
                raise oefmt(space.w_ValueError,
                        "Invalid console type")
            if console_type == '\0':
                raise oefmt(space.w_ValueError,
                        "Cannot open non-console file")
        s = space.text_w(w_mode)
        
        for char in s:
            if char in "+abx":
                # OK do nothing
                pass
            else if char == "r":
                if rwa:
                    raise oefmt(space.w_ValueError,
                            "invalid mode: %.200s", mode)
                rwa = True
                self.readable = True
                if console_type == "x":
                    console_type = "r"
            else if char == "w":
                if rwa:
                    raise oefmt(space.w_ValueError,
                            "invalid mode: %.200s", mode)
                rwa = True
                self.writable = True;
                if console_type == 'x':
                    console_type = 'w'
            else:
                raise oefmt(space.w_ValueError,
                            "invalid mode: %.200s", mode)
        if not rwa:
            raise oefmt(space.w_ValueError,
                        "Must have exactly one of read or write mode")
        
        if self.fd >= 0:
            self.handle = rwin32.get_osfhandle(self.fd)
            self.closehandle = False
        else:
            access = rwin32.GENERIC_READ

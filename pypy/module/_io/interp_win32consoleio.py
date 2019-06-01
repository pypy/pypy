import sys

from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import WrappedDefault, interp2app, unwrap_spec
from pypy.module._io.interp_iobase import (W_RawIOBase, DEFAULT_BUFFER_SIZE)
from rpython.rlib import rwin32

def _get_console_type():
    pass

def _pyio_get_console_type():
    pass

class W_WinConsoleIO(W_RawIOBase):
    SMALLBUF = 4
    
    def __init__(self, space):
        W_RawIOBase.__init__(self, space)
        self.handle = rwin32.INVALID_HANDLE_VALUE
        self.fd = -1
        self.created = 0
        self.readable = 0
        self.writable = 0
        self.closehandle = 0
        self.blksize = 0

    @unwrap_spec(w_mode=WrappedDefault("r"), w_closefd=WrappedDefault(True), w_opener=WrappedDefault(None))
    def descr_init(self, space, w_nameobj, w_mode, w_closefd, w_opener):
        #self.fd = -1
        #self.created = 0
        self.readable = False
        self.writable = False
        #self.closehandle = 0;
        self.blksize = 0
        rwa = False
        console_type = '\0'
        self.buf = lltype.malloc(rffi.CCHARPP.TO,SMALLBUF,flavor='raw')

        self.fd = space.int_w(w_nameobj)
        closefd = space.bool_w(w_closefd)

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
            elif char == "r":
                if rwa:
                    raise oefmt(space.w_ValueError,
                            "invalid mode: %.200s", mode)
                rwa = True
                self.readable = True
                if console_type == "x":
                    console_type = "r"
            elif char == "w":
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
            self.closehandle = True
            if not closefd:
                raise oefmt(space.w_ValueError,
                        "Cannot use closefd=False with a file name")
            if self.writeable:
                access = rwin32.GENERIC_WRITE
        
            from rpython.rlib._os_support import _preferred_traits, string_trait
            traits = _preferred_traits(name)
            if not (traits.str is unicode):
                raise oefmt(space.w_ValueError,
                            "Non-unicode string name %s", traits.str)
            win32traits = make_win32_traits(traits)
            self.handle = win32traits.CreateFile(name, 
                rwin32.GENERIC_READ | rwin32.GENERIC_WRITE,
                rwin32.FILE_SHARE_READ | rwin32.FILE_SHARE_WRITE,
                rffi.NULL, win32traits.OPEN_EXISTING, 0, rffi.NULL)
            if self.handle == rwin32.INVALID_HANDLE_VALUE:
                self.handle = win32traits.CreateFile(name, 
                    access,
                    rwin32.FILE_SHARE_READ | rwin32.FILE_SHARE_WRITE,
                    rffi.NULL, win32traits.OPEN_EXISTING, 0, rffi.NULL)

            if self.handle == rwin32.INVALID_HANDLE_VALUE:
                raise WindowsError(rwin32.GetLastError_saved(),
                                   "Failed to open handle")
        
        if console_type == '\0':
            console_type = _get_console_type(self.handle)

        if console_type == '\0': 
            raise oefmt(space.w_ValueError,
                        "Cannot open non-console file")
        
        if self.writable and console_type != 'w':
            raise oefmt(space.w_ValueError,
                        "Cannot open input buffer for writing")

        if self.readable and console_type != 'r':
            raise oefmt(space.w_ValueError,
                        "Cannot open output buffer for reading")

        self.blksize = DEFAULT_BUFFER_SIZE
        rffi.c_memset(self.buf, 0, SMALLBUF)

W_WinConsoleIO.typedef = TypeDef(
    '_io.WinConsoleIO', W_WinConsoleIO.typedef,
    #__new__  = interp2app(W_FileIO.descr_new.im_func),
    __init__  = interp2app(W_WinConsoleIO.descr_init),
    )

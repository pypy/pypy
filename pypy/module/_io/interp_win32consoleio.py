import sys
import os

from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.typedef import (
    TypeDef, generic_new_descr, GetSetProperty)
from pypy.interpreter.gateway import WrappedDefault, interp2app, unwrap_spec
from pypy.module._io.interp_iobase import (W_RawIOBase, DEFAULT_BUFFER_SIZE)
from pypy.interpreter.unicodehelper import fsdecode
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib._os_support import _preferred_traits
from rpython.rlib import rwin32
from rpython.rlib.rwin32file import make_win32_traits

import unicodedata

SMALLBUF = 4

def _get_console_type(handle):
    mode = lltype.malloc(rwin32.LPDWORD.TO,0,flavor='raw')
    peek_count = lltype.malloc(rwin32.LPDWORD.TO,0,flavor='raw')
    try:
        if handle == rwin32.INVALID_HANDLE_VALUE:
            return '\0'

        if not rwin32.GetConsoleMode(handle, mode):
            return '\0'

        # Peek at the handle to see whether it is an input or output handle
        if rwin32.GetNumberOfConsoleInputEvents(handle, peek_count):
            return 'r'
        return 'w'
    finally:
        lltype.free(mode, flavor='raw')
        lltype.free(peek_count, flavor='raw')

def _pyio_get_console_type(space, w_path_or_fd):
    fd = space.int_w(w_path_or_fd)
    if fd >= 0:
        handle = rwin32.get_osfhandle(fd)
        if handle == rwin32.INVALID_HANDLE_VALUE:
            return '\0'
        return _get_console_type(handle)


    decoded = space.fsdecode_w(w_path_or_fd)
    if not decoded:
        return '\0'
    
    decoded_wstr = rffi.cast(rffi.CWCHARP, decoded)
    if not decoded_wstr:
        return '\0'
 
    m = '\0'
    
    # In CPython the _wcsicmp function is used to perform case insensitive comparison
    normdecoded = unicodedata.normalize("NFKD", decoded.lower())
    if normdecoded == unicodedata.normalize("NFKD", "CONIN$".lower()):
        m = 'r'
    elif normdecoded == unicodedata.normalize("NFKD", "CONOUT$".lower()):
        m = 'w'
    elif normdecoded == unicodedata.normalize("NFKD", "CON".lower()):
        m = 'x'

    if m != '\0':
        return m

    length = 0
    
    pname_buf = lltype.malloc(rffi.CWCHARP.TO, rwin32.MAX_PATH, flavor='raw')

    traits = _preferred_traits(decoded_wstr)
    win32traits = make_win32_traits(traits)
    length = win32traits.GetFullPathName(decoded_wstr, rwin32.MAX_PATH, pname_buf, rffi.NULL)
    
    if length > rwin32.MAX_PATH:
        lltype.free(pname_buf, flavor='raw')
        pname_buf = lltype.malloc(rffi.CWCHARP.TO, length, flavor='raw')
        if pname_buf:
            length = win32traits.GetFullPathName(decoded_wstr, rwin32.MAX_PATH, pname_buf, rffi.NULL)
        else:
            length = 0

    if length:
        if length >= 4 and pname_buf[3] == '\\' and \
           (pname_buf[2] == '.' or pname_buf[2] == '?') and \
           pname_buf[1] == '\\' and pname_buf[0] == '\\':
           pname_buf += 4
        normdecoded = unicodedata.normalize("NFKD", decoded.lower())
        if normdecoded == unicodedata.normalize("NFKD", "CONIN$".lower()):
            m = 'r'
        elif normdecoded == unicodedata.normalize("NFKD", "CONOUT$".lower()):
            m = 'w'
        elif normdecoded == unicodedata.normalize("NFKD", "CON".lower()):
            m = 'x'
           
    lltype.free(pname_buf, flavor='raw')
    return m


class W_WinConsoleIO(W_RawIOBase):
    def __init__(self, space):
        W_RawIOBase.__init__(self, space)
        self.handle = rwin32.INVALID_HANDLE_VALUE
        self.fd = -1
        self.created = 0
        self.readable = 0
        self.writable = 0
        self.closehandle = 0
        self.blksize = 0

    def _internal_close(self, space):
        pass
        
    @unwrap_spec(w_mode=WrappedDefault("r"), w_closefd=WrappedDefault(True), w_opener=WrappedDefault(None))
    def descr_init(self, space, w_nameobj, w_mode, w_closefd, w_opener):
        #self.fd = -1
        #self.created = 0
        name = None
        self.readable = False
        self.writable = False
        #self.closehandle = 0;
        self.blksize = 0
        rwa = False
        console_type = '\0'
        self.buf = lltype.malloc(rffi.CCHARPP.TO,SMALLBUF,flavor='raw')

        try:
            self.fd = space.int_w(w_nameobj)
            closefd = space.bool_w(w_closefd)

            if self.fd < 0:
                w_decodedname = space.fsdecode(w_nameobj)
                name = rffi.cast(rffi.CWCHARP, space.text_w(w_decodedname))
                console_type = _pyio_get_console_type(space, w_decodedname)
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
                                "invalid mode: %s", space.text_w(w_mode))
                    rwa = True
                    self.readable = True
                    if console_type == "x":
                        console_type = "r"
                elif char == "w":
                    if rwa:
                        raise oefmt(space.w_ValueError,
                                "invalid mode: %s", space.text_w(w_mode))
                    rwa = True
                    self.writable = True;
                    if console_type == 'x':
                        console_type = 'w'
                else:
                    raise oefmt(space.w_ValueError,
                                "invalid mode: %s", space.text_w(w_mode))
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
                if self.writable:
                    access = rwin32.GENERIC_WRITE
            
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
        finally:
           lltype.free(self.buf, flavor='raw')
        
        return None
        
    def repr_w(self, space):
        typename = space.type(self).name
        try:
            w_name = space.getattr(self, space.newtext("name"))
        except OperationError as e:
            if not e.match(space, space.w_Exception):
                raise
            return space.newtext("<%s>" % (typename,))
        else:
            name_repr = space.text_w(space.repr(w_name))
            return space.newtext("<%s name=%s>" % (typename, name_repr))
            
    def fileno_w(self, space):
        if self.fd < 0 and self.handle != rwin32.INVALID_HANDLE_VALUE:
            if self.writable:
                self.fd = rwin32.open_osfhandle(self.handle, rwin32._O_WRONLY | rwin32._O_BINARY)
            else:
                self.fd = rwin32.open_osfhandle(self.handle, rwin32._O_RDONLY | rwin32._O_BINARY)
        if self.fd < 0:
            return err_mode("fileno")
         
        return space.newint(self.fd)

W_WinConsoleIO.typedef = TypeDef(
    '_io._WinConsoleIO', W_WinConsoleIO.typedef,
    __new__  = generic_new_descr(W_WinConsoleIO),
    __init__  = interp2app(W_WinConsoleIO.descr_init),
    __repr__ = interp2app(W_WinConsoleIO.repr_w),
    )

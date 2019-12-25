import sys
import os

from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.typedef import (
    TypeDef, generic_new_descr, GetSetProperty)
from pypy.interpreter.gateway import WrappedDefault, interp2app, unwrap_spec
from pypy.module._io.interp_iobase import (W_RawIOBase, convert_size, DEFAULT_BUFFER_SIZE)
from pypy.module.signal.interp_signal import sigintevent
from pypy.interpreter.unicodehelper import fsdecode
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib._os_support import _preferred_traits
from rpython.rlib import rwin32
from rpython.rlib.runicode import WideCharToMultiByte, MultiByteToWideChar
from rpython.rlib.rwin32file import make_win32_traits
from rpython.rlib.buffer import ByteBuffer

from rpython.rtyper.tool import rffi_platform as platform

import unicodedata

# SMALLBUF determines how many utf-8 characters will be
# buffered within the stream, in order to support reads
# of less than one character
SMALLBUF = 4
# BUFMAX determines how many bytes can be read in one go.
BUFMAX = (32*1024*1024)
BUFSIZ = platform.ConstantInteger("BUFSIZ")

def err_closed(space):
    return oefmt(space.w_ValueError,
                "I/O operation on closed file")

def err_mode(space, state):
    # TODO sort out the state
    return oefmt(space.w_ValueError,
                "I/O operation on closed file")

def read_console_wide(space, handle, maxlen):
    """ 
    Make a blocking call to ReadConsoleW
    """
    err = 0
    sig = 0
    buf = ByteBuffer(maxlen + 1)
    addr = buf.get_raw_address()
    off = 0
    readlen = 0
    while off < maxlen:
        with lltype.scoped_alloc(rwin32.LPDWORD.TO, 1) as n:
            neg_one = rffi.cast(rwin32.DWORD, -1)
            n[0] = neg_one
            len = min(maxlen - off, BUFSIZ)
            rwin32.SetLastError_saved(0)
            res = rwin32.ReadConsoleW(handle,
                             rffi.cast(rwin32.LPVOID, rffi.ptradd(addr, off)),
                             len, n, rffi.NULL)
            err = rwin32.GetLastError_saved()
            if not res:
                break
                
            if n[0] == neg_one and err == rwin32.ERROR_OPERATION_ABORTED:
                break
                
            if n[0] == 0:
                if err != rwin32.ERROR_OPERATION_ABORTED:
                    break
                err = 0
                hInterruptEvent = sigintevent()
                if rwin32.WaitForSingleObject(hInterruptEvent, 100) == rwin32.WAIT_OBJECT_0:
                    rwin32.ResetEvent(hInterruptEvent)
                    space.getexecutioncontext().checksignals()
            readlen += n[0]
            
            # We didn't manage to read the whole buffer
            # don't try again as it will just block
            if n[0] < len:
                break
                
            # We read a new line
            if buf[readlen -1] == u'\n':
                break
            
            with lltype.scoped_alloc(rwin32.LPWORD.TO, 1) as char_type:
                if off + BUFSIZ >= maxlen and \
                    rwin32.GetStringTypeW(rwin32.CT_CTYPE3, buf[readlen - 1], 1, char_type) and \
                    char_type == rwin32.C3_HIGHSURROGATE:
                    maxlen += 1
                    off += n[0]
                    continue
                off += BUFSIZ
    if err:
        return None
        
    if readlen > 0 and buf[0] == u'\x1a':
        readlen = 0
    return buf.getslice(0, readlen, 1, readlen)


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

    if space.isinstance_w(w_path_or_fd, space.w_int):
        fd = space.int_w(w_path_or_fd)
        handle = rwin32.get_osfhandle(fd)
        if handle == rwin32.INVALID_HANDLE_VALUE:
            return '\0'
        return _get_console_type(handle)

    decoded = space.fsdecode_w(w_path_or_fd)
    if not decoded:
        return '\0'
 
    m = '\0'

    # In CPython the _wcsicmp function is used to perform case insensitive comparison
    dlower = decoded.lower()
    if  dlower == 'CONIN$'.lower():
        m = 'r'
    elif dlower == 'CONOUT$'.lower():
        m = 'w'
    elif dlower == 'CON'.lower():
        m = 'x'

    if m != '\0':
        return m

    if len(dlower) >=4:
        if dlower[:4] == '\\\\.\\' or dlower[:4] == '\\\\?\\':
            dlower = dlower[4:]
            if  dlower == 'CONIN$'.lower():
                 m = 'r'
            elif dlower == 'CONOUT$'.lower():
                 m = 'w'
            elif dlower == 'CON'.lower():
                 m = 'x'
    return m


class W_WinConsoleIO(W_RawIOBase):
    def __init__(self, space):
        W_RawIOBase.__init__(self, space)
        self.handle = rwin32.INVALID_HANDLE_VALUE
        self.fd = -1
        self.created = 0
        self.readable = False
        self.writable = False
        self.closehandle = False
        self.blksize = 0
        self.buf = None

    def _dealloc_warn_w(self, space, w_source):
        buf = self.buf
        if buf:
            lltype.free(buf, flavor='raw')
        
    def _copyfrombuf(self, buf, lgt):
        n = 0
        while self.buf[0] != '\x00' and lgt > 0:
            buf[n] = self.buf[0]
            for i in range(1, SMALLBUF):
                self.buf[i-1] = self.buf[i]
            self.buf[SMALLBUF-1] = rffi.cast(lltype.Char, 0)
            lgt -= 1
            n += 1
        return n
        
    def _buflen(self):
        for i in range(len(SMALLBUF)):
            if self.buf[i] != '\x00':
                return i
        return SMALLBUF

    @unwrap_spec(mode='text', closefd=int)
    def descr_init(self, space, w_nameobj, mode='r', closefd=True, w_opener=None):
        name = rffi.cast(rffi.CWCHARP, 0)
        self.fd = -1
        self.handle = rwin32.INVALID_HANDLE_VALUE
        self.readable = False
        self.writable = False
        self.blksize = 0
        rwa = False
        console_type = '\0'
        self.buf = lltype.malloc(rffi.CCHARP.TO, SMALLBUF, flavor='raw', zero=True)

        if space.isinstance_w(w_nameobj, space.w_int): 
            self.fd = space.int_w(w_nameobj)
            if self.fd < 0:
                raise oefmt(space.w_ValueError,
                        "negative file descriptor")

        # make the flow analysis happy,otherwise it thinks w_path
        # is undefined later
        w_path = w_nameobj
        if self.fd < 0:
            from pypy.module.posix.interp_posix import fspath
            w_path = fspath(space, w_nameobj)
            console_type = _pyio_get_console_type(space, w_path)
            if not console_type:
                raise oefmt(space.w_ValueError,
                        "Invalid console type")
            if console_type == '\0':
                raise oefmt(space.w_ValueError,
                        "Cannot open non-console file")
        
        for char in mode:
            if char in "+abx":
                # OK do nothing
                pass
            elif char == "r":
                if rwa:
                    raise oefmt(space.w_ValueError,
                            "invalid mode: %s", mode)
                rwa = True
                self.readable = True
                if console_type == "x":
                    console_type = "r"
            elif char == "w":
                if rwa:
                    raise oefmt(space.w_ValueError,
                            "invalid mode: %s", mode)
                rwa = True
                self.writable = True
                if console_type == 'x':
                    console_type = 'w'
            else:
                raise oefmt(space.w_ValueError,
                            "invalid mode: %s", mode)
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
        
            traits = _preferred_traits(space.realunicode_w(w_path))
            if not (traits.str is unicode):
                raise oefmt(space.w_ValueError,
                            "Non-unicode string name %s", traits.str)
            win32traits = make_win32_traits(traits)
            
            pathlen = space.len_w(w_path)
            name = rffi.utf82wcharp(space.utf8_w(w_path), pathlen)
            self.handle = win32traits.CreateFile(name, 
                rwin32.GENERIC_READ | rwin32.GENERIC_WRITE,
                rwin32.FILE_SHARE_READ | rwin32.FILE_SHARE_WRITE,
                rffi.NULL, win32traits.OPEN_EXISTING, 0, rffi.NULL)
            if self.handle == rwin32.INVALID_HANDLE_VALUE:
                self.handle = win32traits.CreateFile(name, 
                    access,
                    rwin32.FILE_SHARE_READ | rwin32.FILE_SHARE_WRITE,
                    rffi.NULL, win32traits.OPEN_EXISTING, 0, rffi.NULL)
            lltype.free(name, flavor='raw')
            
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
    
    def readable_w(self, space):
        if self.handle == rwin32.INVALID_HANDLE_VALUE:
            raise err_closed(space)
        return space.newbool(self.readable)
    
    def writable_w(self, space):
        if self.handle == rwin32.INVALID_HANDLE_VALUE:
            raise err_closed(space)
        return space.newbool(self.writable)
    
    def isatty_w(self, space):
        if self.handle == rwin32.INVALID_HANDLE_VALUE:
            raise err_closed(space)
        return space.newbool(True)
    
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
        traits = _preferred_traits(u"")
        win32traits = make_win32_traits(traits)
        if self.fd < 0 and self.handle != rwin32.INVALID_HANDLE_VALUE:
            if self.writable:
                self.fd = rwin32.open_osfhandle(rffi.cast(rffi.INTP, self.handle), win32traits._O_WRONLY | win32traits._O_BINARY)
            else:
                self.fd = rwin32.open_osfhandle(rffi.cast(rffi.INTP, self.handle), win32traits._O_RDONLY | win32traits._O_BINARY)
        if self.fd < 0:
            raise err_mode(space, "fileno")
        return space.newint(self.fd)
        
    def readinto_w(self, space, w_buffer):
        rwbuffer = space.writebuf_w(w_buffer)
        length = rwbuffer.getlength()
        return space.newint(self.readinto(space, rwbuffer, length))

    def readinto(self, space, rwbuffer, length):
        
        if self.handle == rwin32.INVALID_HANDLE_VALUE:
            raise err_closed(space)
            
        if not self.readable:
            raise err_mode(space, "reading")
            
        if not length:
            return 0
            
        if length > BUFMAX:
            raise oefmt(space.w_ValueError,
                        "cannot read more than %d bytes", BUFMAX)
                        
        wlen = length / 4
        if wlen < 1:
            wlen = 1
            
        read_len = self._copyfrombuf(rwbuffer, length)
        if read_len > 0:
            rwbuffer.delslice(read_len, rwbuffer.length())
            length = length - read_len
            wlen = wlen - 1
            
        if length == read_len or wlen < 1:
            return read_len
            
        wbuf = read_console_wide(space, self.handle, wlen)
            
        if not wbuf:
            return -1
        n = len(wbuf)
        if len(wbuf) == 0: 
            return read_len
            
        u8n = 0
               
        if length < 4:
            if WideCharToMultiByte(rwin32.CP_UTF8,
                                       0, wbuf, n, self.buf,
                                       rffi.sizeof(self.buf)/ rffi.sizeof(self.buf[0]),
                                       rffi.NULL, rffi.NULL):
                u8n = self._copyfrombuf(rwbuffer, length)
            else:
                addr = rwbuffer.get_raw_address()
                u8n = WideCharToMultiByte(rwin32.CP_UTF8,
                                                0, wbuf, n, self.buf, length,
                                                rffi.NULL, rffi.NULL)
                                                
        if u8n:
            read_len += u8n
            u8n = 0
        else:
            err = rwin32.GetLastError_saved()
            if err == rwin32.ERROR_INSUFFICIENT_BUFFER:
                u8n = WideCharToMultiByte(rwin32.CP_UTF8, 0, wbuf,
                                                 n, rffi.NULL, 0, rffi.NULL, rffi.NULL)
            
        if u8n:
            raise oefmt(space.w_ValueError,
                    "Buffer had room for %d bytes but %d bytes required",
                    length, u8n)
                    
        if err:
            raise oefmt(space.w_WindowsError,
                    err)
        
        if length < 0:
            return -1
        
        return read_len
            
    def read_w(self, space, w_size=None):
        size = convert_size(space, w_size)
        if self.handle == rwin32.INVALID_HANDLE_VALUE:
            raise err_closed(space)
        if not self.readable:
            raise err_mode(space,"reading")

        if size < 0:
            return self.readall_w(space)

        if size > BUFMAX:
             raise oefmt(space.w_ValueError,
                        "Cannot read more than %d bytes",
                        BUFMAX)

        with lltype.scoped_alloc(rffi.CCHARP.TO, size) as buf:
            bytes_read = self.readinto(space, buf, size)
            if bytes_read < 0:
                return space.newbytes('')
            ret_str = space.charp2str(buf)
            return space.newbytes(ret_str)

    def readall_w(self, space):
        if self.handle == rwin32.INVALID_HANDLE_VALUE:
            raise err_closed(space)

        bufsize = BUFSIZ
        buf = lltype.malloc(rffi.CWCHARP.TO, bufsize + 1, flavor='raw')
        length = 0
        n = lltype.malloc(rwin32.LPDWORD.TO, 1, flavor='raw')
        n[0] = 0

        try:
            # Read the bytes from the console
            while True:
                if length >= bufsize:
                    if length > BUFMAX:
                        break
                    newsize = length
                    if newsize < bufsize:
                        raise oefmt(space.w_OverflowError,
                                    "unbounded read returned more bytes "
                                    "than a Python bytes object can hold")
                    bufsize = newsize
                    lltype.free(buf, flavor='raw')
                    buf = lltype.malloc(rffi.CWCHARP.TO, bufsize + 1, flavor='raw')
                    subbuf = read_console_wide(space, self.handle, bufsize - length)
                    
                    if len(subbuf) > 0:
                        rwin32.wcsncpy_s(buf[length], bufsize - length +1, subbuf, n)
                        if n[0] == 0:
                            break
                    else:
                        break 
                        
                    length += n
                    
            if length == 0 and self._buflen() == 0:
                return None
            
            # Compute the size for the destination buffer
            if length:
                bytes_size = WideCharToMultiByte(rwin32.CP_UTF8, 0, buf,
                                     length, rffi.NULL, 0, rffi.NULL, rffi.NULL)
                 
                if bytes_size:
                    err = rwin32.GetLastError_saved()
                    raise WindowsError(err, "Failed to convert wide characters to multi byte string")
            else:
                bytes_size = 0    
            bytes_size += self._buflen()
            
            # Create destination buffer and convert the bytes
            with lltype.scoped_alloc(rffi.CCHARP.TO, bytes_size) as ret_bytes:
                rn = self._copyfrombuf(ret_bytes, bytes_size)
            
                if length:
                    bytes_size = WideCharToMultiByte(rwin32.CP_UTF8, 0, buf, length,
                             ret_bytes[rn], bytes_size - rn, rffi.NULL, rffi.NULL)
                             
                    if not bytes_size:
                        err = rwin32.GetLastError_saved()
                        raise WindowsError(err,
                             "Failed to convert wide characters to multi byte string")
                    
                    bytes_size += rn
            
                ret_str = space.charp2str(bytes)
                return space.newbytes(ret_str)
            
        finally:
            lltype.free(buf, flavor='raw')
            lltype.free(n, flavor='raw')

    def write_w(self, space, w_data):
        buffer = space.charbuf_w(w_data)
        with lltype.scoped_alloc(rwin32.LPDWORD.TO, 1) as n:
        
            if self.handle == rwin32.INVALID_HANDLE_VALUE:
                raise err_closed(space)
            
            if not self.writable:
                raise err_mode(space,"writing")
            
            if not len(buffer):
                return space.newint(0)
            
            if len(buffer) > BUFMAX:
                buflen = BUFMAX
            else:
                buflen = len(buffer)
        
            wlen = MultiByteToWideChar(rwin32.CP_UTF8, 0 , buffer, buflen, rffi.NULL, 0)
        
            while wlen > (32766 / rffi.sizeof(rffi.CWCHARP)):
                buflen /= 2
                wlen = MultiByteToWideChar(rwin32.CP_UTF8, 0 , buffer, buflen, rffi.NULL, 0)
            
            if not wlen:
                raise WindowsError("Failed to convert bytes to wide characters")
        
            with lltype.scoped_alloc(rffi.CWCHARP.TO, wlen) as wbuf:
                wlen = MultiByteToWideChar(rwin32.CP_UTF8, 0 , buffer, buflen, wbuf, wlen)
                if wlen:
                    res = rwin32.WriteConsoleW(self.handle, rffi.cast(rwin32.LPVOID, wbuf), wlen, n , rffi.NULL)
                
                    if res and n[0] < wlen:
                        buflen = WideCharToMultiByte(rwin32.CP_UTF8, 0, wbuf, n[0],
                        rffi.NULL, 0, rffi.NULL, rffi.NULL)
                
                        if buflen:
                            wlen = MultiByteToWideChar(rwin32.CP_UTF8, 0, buffer,
                                                       buflen, rffi.NULL, 0)
                            if buflen != wlen:
                                raise WindowsError("second call to MultiByteToWideChar "
                                        "had different lengthed buffer")
                        
                else:
                    res = 0
                
                if not res:
                    err = rwin32.GetLastError_saved()
                    raise WindowsError(err, "Failed to convert multi byte string to wide characters")
                
                return space.newint(buflen)
            
    def get_blksize(self,space):
        return space.newint(self.blksize)
        

W_WinConsoleIO.typedef = TypeDef(
    '_io.WinConsoleIO', W_RawIOBase.typedef,
    __new__  = generic_new_descr(W_WinConsoleIO),
    __init__  = interp2app(W_WinConsoleIO.descr_init),
    __repr__ = interp2app(W_WinConsoleIO.repr_w),
    
    readable = interp2app(W_WinConsoleIO.readable_w),
    writable = interp2app(W_WinConsoleIO.writable_w),
    isatty   = interp2app(W_WinConsoleIO.isatty_w),
    read     = interp2app(W_WinConsoleIO.read_w),
    readall  = interp2app(W_WinConsoleIO.readall_w),
    readinto = interp2app(W_WinConsoleIO.readinto_w),    
    fileno   = interp2app(W_WinConsoleIO.fileno_w),
    write    = interp2app(W_WinConsoleIO.write_w),   
    _blksize = GetSetProperty(W_WinConsoleIO.get_blksize),
    )

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
from rpython.rlib.rwin32file import make_win32_traits
from rpython.rtyper.tool import rffi_platform as platform

import unicodedata

SMALLBUF = 4
BUFMAX = (32*1024*1024)
BUFSIZ = platform.ConstantInteger("BUFSIZ")
CONIN = rffi.unicode2wcharp(u"CONIN$")
CONOUT = rffi.unicode2wcharp(u"CONOUT$")
CON = rffi.unicode2wcharp(u"CON")

def err_closed(space):
    raise oefmt(space.w_ValueError,
                "I/O operation on closed file")

def err_mode(space, state):
    # TODO sort out the state
    raise oefmt(space.w_ValueError,
                "I/O operation on closed file")

def read_console_w(space, handle, maxlen, readlen):
    err = 0
    sig = 0
    buf = lltype.malloc(rffi.CWCHARP, maxlen, flavor='raw')

    try:
        if not buf:
            return None
        
        off = 0
        while off < maxlen:
            with lltype.scoped_alloc(rwin32.LPDWORD.TO, 1) as n:
                n[0] = -1
                len = min(maxlen - off, BUFSIZ)
                rwin32.SetLastError_saved(0)
                res = rwin32.ReadConsoleW(handle, buf[off], len, n, rffi.NULL)
                err = rwin32.GetLastError_saved()
                if not res:
                    break
                    
                if n == -1 and err == rwin32.ERROR_OPERATION_ABORTED:
                    break
                    
                if n == 0:
                    if err != rwin32.ERROR_OPERATION_ABORTED:
                        break
                    err = 0
                    hInterruptEvent = sigintevent()
                    if rwin32.WaitForSingleObjectEx(hInterruptEvent, 100, False) == rwin32.WAIT_OBJECT_0:
                        rwin32.ResetEvent(hInterruptEvent)
                        space.getexecutioncontext().checksignals()
                
                readlen += n
                
                # We didn't manage to read the whole buffer
                # don't try again as it will just block
                if n < len:
                    break
                    
                # We read a new line
                if buf[readlen -1] == u'\n':
                    break
                
                with lltype.scoped_alloc(rwin32.LPWORD.TO, 1) as char_type:
                    if off + BUFSIZ >= maxlen and \
                        rwin32.GetStringTypeW(rwin32.CT_CTYPE3, buf[readlen - 1], 1, char_type) and \
                        char_type == rwin32.C3_HIGHSURROGATE:
                        maxlen += 1
                        newbuf = lltype.malloc(rffi.CWCHARP, maxlen, flavor='raw')
                        lltype.free(buf, flavor='raw')
                        buf = newbuf
                        off += n
                        continue
                    off += BUFSIZ
        if err:
            lltype.free(buf, flavor='raw')
            return None
            
        if readlen > 0 and buf[0] == u'\x1a':
            lltype.free(buf, flavor='raw')
            buf = lltype.malloc(rwin32.CWCHARP, 1, flavor='raw')
            buf[0] = '\0'
            readlen = 0
        return buf
    except:
        lltype.free(buf, flavor='raw')


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
    
    decoded_wstr = rffi.cast(rffi.CWCHARP, decoded)
    if not decoded_wstr:
        return '\0'
 
    m = '\0'
    
    # In CPython the _wcsicmp function is used to perform case insensitive comparison
    decoded.lower()
    if not rwin32.wcsicmp(decoded_wstr, CONIN):
        m = 'r'
    elif not rwin32.wcsicmp(decoded_wstr, CONOUT):
        m = 'w'
    elif not rwin32.wcsicmp(decoded_wstr, CON):
        m = 'x'


    if m != '\0':
        return m

    length = 0
    
    pname_buf = lltype.malloc(rffi.CWCHARP.TO, rwin32.MAX_PATH, flavor='raw')

    uni_decoded_wstr = rffi.wcharp2unicode(decoded_wstr)
    traits = _preferred_traits(uni_decoded_wstr)
    win32traits = make_win32_traits(traits)
    w_str_nullptr = lltype.nullptr(win32traits.LPSTRP.TO)
    length = win32traits.GetFullPathName(decoded_wstr, rwin32.MAX_PATH, pname_buf, w_str_nullptr)
    
    if length > rwin32.MAX_PATH:
        lltype.free(pname_buf, flavor='raw')
        pname_buf = lltype.malloc(rffi.CWCHARP.TO, length, flavor='raw')
        if pname_buf:
            length = win32traits.GetFullPathName(decoded_wstr, rwin32.MAX_PATH, pname_buf, w_str_nullptr)
        else:
            length = 0

    if length:
        if length >= 4 and pname_buf[3] == u'\\' and \
           (pname_buf[2] == u'.' or pname_buf[2] == u'?') and \
           pname_buf[1] == u'\\' and pname_buf[0] == u'\\':
            name = rffi.ptradd(pname_buf, 4)
 
            if not rwin32.wcsicmp(name, CONIN):
                m = 'r'
            elif not rwin32.wcsicmp(name, CONOUT):
                m = 'w'
            elif not rwin32.wcsicmp(name, CON):
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

    # def _internal_close(self, space):
        # pass
        
    def _copyfrombuf(self, buf, len):
        n = 0
        while self.buf[0] and len:
            buf[n] = self.buf[0]
            for i in range(1, SMALLBUF):
                self.buf[i-1] = self.buf[i]
            self.buf[SMALLBUF-1] = 0
            len -= 1
            n += 1
        return n
        
    def _buflen(self):
        for i in range(len(SMALLBUF)):
            if not self.buf[i]:
                return i
        return SMALLBUF

    @unwrap_spec(w_mode=WrappedDefault("r"), w_closefd=WrappedDefault(True), w_opener=WrappedDefault(None))
    def descr_init(self, space, w_nameobj, w_mode, w_closefd, w_opener):
        return None
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
    
    def readable_w(self, space):
        if self.handle == rwin32.INVALID_HANDLE_VALUE:
            return err_closed(space)
        return space.newbool(self.readable)
    
    def writable_w(self, space):
        if self.handle == rwin32.INVALID_HANDLE_VALUE:
            return err_closed(space)
        return space.newbool(self.writable)
    
    def isatty_w(self, space):
        if self.handle == rwin32.INVALID_HANDLE_VALUE:
            return err_closed(space)
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
        if self.fd < 0 and self.handle != rwin32.INVALID_HANDLE_VALUE:
            if self.writable:
                self.fd = rwin32.open_osfhandle(self.handle, rwin32._O_WRONLY | rwin32._O_BINARY)
            else:
                self.fd = rwin32.open_osfhandle(self.handle, rwin32._O_RDONLY | rwin32._O_BINARY)
        if self.fd < 0:
            return err_mode("fileno")
        return space.newint(self.fd)
        
    def readinto_w(self, space, w_buffer):
        rwbuffer = space.writebuf_w(w_buffer)
        length = rwbuffer.getlength()
        
        if self.handle == rwin32.INVALID_HANDLE_VALUE:
            return err_closed(space)
            
        if not self.readable:
            err_mode(space, "reading")
            
        if not length:
            return space.newint(0)
            
        if length > BUFMAX:
            raise oefmt(space.w_ValueError,
                        "cannot read more than %d bytes", BUFMAX)
                        
        wlen = rffi.cast(rwin32.DWORD, length / 4)
        if not wlen:
            wlen = 1
            
        read_len = self._copyfrombuf(rwbuffer, rffi.cast(rwin32.DWORD, length))
        if read_len:
            rwbuffer.setslice(read_len, length)
            length = length - read_len
            wlen = wlen - 1
            
        if length == read_len or not wlen:
            return space.newint(read_len)
            
        with lltype.scoped_alloc(rwin32.LPDWORD.TO, 1) as n:
            wbuf = read_console_w(space, self.handle, wlen , n)
            
            if not wbuf:
                return space.newint(-1)
                
            if n == 0:
                return space.newint(read_len)
                
            u8n = 0
            
            if len < 4:
                if rwin32.WideCharToMultiByte(rwin32.CP_UTF8,
                                           0, wbuf, n, self.buf,
                                           rffi.sizeof(self.buf)/ rffi.sizeof(self.buf[0]),
                                           rffi.NULL, rffi.NULL):
                    u8n = self._copyfrombuf(rwbuffer, len)
                else:
                    u8n = rwin32.WideCharToMultiByte(rwin32.CP_UTF8,
                                                    0, wbuf, n, buf, len,
                                                    rffi.NULL, rffi.NULL)
                                                    
            if u8n:
                read_len += u8n
                u8n = 0
            else:
                err = rwin32.GetLastError_saved()
                if err == rwin32.ERROR_INSUFFICIENT_BUFFER:
                    u8n = rwin32.WideCharToMultiByte(rwin32.CP_UTF8, 0, wbuf,
                                                     n, rffi.NULL, 0, rffi.NULL, rffi.NULL)
                
            if u8n:
                raise oefmt(space.w_ValueError,
                        "Buffer had room for %d bytes but %d bytes required",
                        len, u8n)
                        
            if err:
                raise oefmt(space.w_WindowsError,
                        err)
            
            if len < 0:
                return None
            
            return space.newint(read_len)
            
    def read_w(self, space, w_size=None):
        size = convert_size(space, w_size)
        if self.handle == rwin32.INVALID_HANDLE_VALUE:
            err_closed(space)
        if not self.readable:
            return err_mode("reading")

        if size < 0:
            return self.readall_w(space)

        if size > BUFMAX:
             raise oefmt(space.w_ValueError,
                        "Cannot read more than %d bytes",
                        BUFMAX)

        w_buffer = space.call_function(space.w_bytearray, w_size)
        w_bytes_size = self.readinto_w(space, w_buffer)
        if w_bytes_size < 0:
            return None
        space.delslice(w_buffer, w_bytes_size, space.len(w_buffer))
        
        return space.w_bytes(w_buffer)

    def readall_w(self, space):
        if self.handle == rwin32.INVALID_HANDLE_VALUE:
            err_closed(space)

        bufsize = BUFSIZ
        buf = lltype.malloc(rffi.CWCHARP, bufsize + 1, flavor='raw')
        len = 0
        n = lltype.malloc(rffi.CWCHARP, 1, flavor='raw')
        n[0] = 0

        try:
            # Read the bytes from the console
            while True:
                if len >= bufsize:
                    if len > BUFMAX:
                        break
                    newsize = len
                    if newsize < bufsize:
                        raise oefmt(space.w_OverflowError,
                                    "unbounded read returned more bytes "
                                    "than a Python bytes object can hold")
                    bufsize = newsize
                    lltype.free(buf, flavor='raw')
                    buf = lltype.malloc(rffi.CWCHARP, bufsize + 1, flavor='raw')
                    subbuf = read_console_w(self.handle, bufsize - len, n)
                    
                    if n > 0:
                        rwin32.wcsncpy_s(buf[len], bufsize - len +1, subbuf, n)
                    
                    lltype.free(subbuf, flavor='raw')
                    
                    if n == 0:
                        break
                        
                    len += n
                    
            if len == 0 and self._buflen() == 0:
                return None
            
            # Compute the size for the destination buffer
            if len:
                bytes_size = rwin32.WideCharToMultiByte(rwin32.CP_UTF8, 0, buf,
                 len, rffi.NULL, 0, rffi.NULL, rffi.NULL)
                 
                if bytes_size:
                    err = rwin32.GetLastError_saved()
                    raise WindowsError(err, "Failed to convert wide characters to multi byte string")
            else:
                bytes_size = 0    
            bytes_size += self._buflen()
            
            # Create destination buffer and convert the bytes
            bytes = lltype.malloc(rffi.CCHARP, bytes_size, flavor='raw')
            rn = self._copyfrombuf(bytes, bytes_size)
            
            if len:
                bytes_size = rwin32.WideCharToMultiByte(rwin32.CP_UTF8, 0, buf, len,
                             bytes[rn], bytes_size - rn, rffi.NULL, rffi.NULL)
                             
                if not bytes_size:
                    lltype.free(bytes, flavor='raw')
                    err = rwin32.GetLastError_saved()
                    raise WindowsError(err, "Failed to convert wide characters to multi byte string")
                    
                bytes_size += rn
            
            lltype.free(bytes, flavor='raw')
            w_bytes = space.charp2str(bytes)
            return space.newbytes(w_bytes)
            
        finally:
            lltype.free(buf, flavor='raw')
            lltype.free(n, flavor='raw')

    def write_w(self, space, w_data):
        buffer = space.charbuf_w(w_data)
        n = lltype.malloc(rwin32.LPDWORD.TO, 0, flavor='raw')
        
        if self.handle == rwin32.INVALID_HANDLE_VALUE:
            return err_closed(space)
            
        if not self.writable:
            return err_mode("writing")
            
        if not len(buffer):
            return 0
            
        if len(buffer) > BUFMAX:
            buflen = BUFMAX
        else:
            buflen = len(buffer)
        
        wlen = rwin32.MultiByteToWideChar(rwin32.CP_UTF8, 0 , buffer, buflen, rffi.NULL, 0)
        
        while wlen > (32766 / rffi.sizeof(rffi.CWCHARP.TO)):
            buflen /= 2
            wlen = rwin32.MultiByteToWideChar(rwin32.CP_UTF8, 0 , buffer, buflen, rffi.NULL, 0)
            
        if not wlen:
            lltype.free(n, flavor='raw')
            raise WindowsError("Failed to convert bytes to wide characters")
        
        with lltype.scoped_alloc(rffi.CWCHARP, wlen) as wbuf:
            wlen = rwin32.MultiByteToWideChar(rwin32.CP_UTF8, 0 , buffer, buflen, wbuf, wlen)
            if wlen:
                res = rwin32.WriteConsoleW(self.handle, wbuf, wlen, n , rffi.NULL)
                
                if res and n < wlen:
                    buflen = rwin32.WideCharToMultiByte(rwin32.CP_UTF8, 0, wbuf, n,
                    rffi.NULL, 0, rffi.NULL, rffi.NULL)
                
                    if buflen:
                        wlen = rwin32.MultiByteToWideChar(rwin32.CP_UTF8, 0, buffer,
                        buflen, rffi.NULL, 0)
                        assert len == wlen
                        
            else:
                res = 0
                
            if not res:
                err = rwin32.GetLastError_saved()
                lltype.free(n, flavor='raw')
                raise WindowsError(err, "Failed to convert multi byte string to wide characters")
                
            lltype.free(n, flavor='raw')
            return space.newint(len)
            
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
    write = interp2app(W_WinConsoleIO.write_w),   
    _blksize = GetSetProperty(W_WinConsoleIO.get_blksize),
    )

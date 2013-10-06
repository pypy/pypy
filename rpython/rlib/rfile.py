
""" This file makes open() and friends RPython. Note that RFile should not
be used directly and instead it's magically appearing each time you call
python builtin open()
"""

import os
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rlib.rarithmetic import r_uint, intmask
from rpython.rlib import rposix
from rpython.rlib.rstring import StringBuilder

eci = ExternalCompilationInfo(includes=['stdio.h'])

def llexternal(*args):
    return rffi.llexternal(*args, compilation_info=eci)

FILE = lltype.Struct('FILE') # opaque type maybe

c_open = llexternal('fopen', [rffi.CCHARP, rffi.CCHARP], lltype.Ptr(FILE))
c_close = llexternal('fclose', [lltype.Ptr(FILE)], rffi.INT)
c_write = llexternal('fwrite', [rffi.CCHARP, rffi.SIZE_T, rffi.SIZE_T,
                                     lltype.Ptr(FILE)], rffi.SIZE_T)
c_read = llexternal('fread', [rffi.CCHARP, rffi.SIZE_T, rffi.SIZE_T,
                                   lltype.Ptr(FILE)], rffi.SIZE_T)
c_feof = llexternal('feof', [lltype.Ptr(FILE)], rffi.INT)
c_ferror = llexternal('ferror', [lltype.Ptr(FILE)], rffi.INT)
c_clearerror = llexternal('clearerr', [lltype.Ptr(FILE)], lltype.Void)
c_fseek = llexternal('fseek', [lltype.Ptr(FILE), rffi.LONG, rffi.INT],
                          rffi.INT)
c_tmpfile = llexternal('tmpfile', [], lltype.Ptr(FILE))
c_fileno = llexternal('fileno', [lltype.Ptr(FILE)], rffi.INT)
c_ftell = llexternal('ftell', [lltype.Ptr(FILE)], lltype.Signed)
c_fflush = llexternal('fflush', [lltype.Ptr(FILE)], lltype.Signed)

BASE_BUF_SIZE = 4096

def create_file(filename, mode="r", buffering=-1):
    assert buffering == -1
    assert filename is not None
    assert mode is not None
    ll_name = rffi.str2charp(filename)
    try:
        ll_mode = rffi.str2charp(mode)
        try:
            ll_f = c_open(ll_name, ll_mode)
            if not ll_f:
                errno = rposix.get_errno()
                raise OSError(errno, os.strerror(errno))
        finally:
            lltype.free(ll_mode, flavor='raw')
    finally:
        lltype.free(ll_name, flavor='raw')
    return RFile(ll_f)

def create_temp_rfile():
    res = c_tmpfile()
    if not res:
        errno = rposix.get_errno()
        raise OSError(errno, os.strerror(errno))
    return RFile(res)

class RFile(object):
    def __init__(self, ll_file):
        self.ll_file = ll_file

    def write(self, value):
        assert value is not None
        ll_file = self.ll_file
        if not ll_file:
            raise ValueError("I/O operation on closed file")
        assert value is not None
        ll_value = rffi.get_nonmovingbuffer(value)
        try:
            # note that since we got a nonmoving buffer, it is either raw
            # or already cannot move, so the arithmetics below are fine
            total_bytes = 0
            ll_current = ll_value
            while total_bytes < len(value):
                bytes = c_write(ll_current, 1, len(value) - r_uint(total_bytes),
                                ll_file)
                if bytes == 0:
                    errno = rposix.get_errno()
                    raise OSError(errno, os.strerror(errno))
                total_bytes += bytes
                ll_current = rffi.cast(rffi.CCHARP,
                                       rffi.cast(lltype.Unsigned, ll_value) +
                                       total_bytes)
        finally:
            rffi.free_nonmovingbuffer(value, ll_value)

    def close(self):
        if self.ll_file:
            # double close is allowed
            res = c_close(self.ll_file)
            self.ll_file = lltype.nullptr(FILE)
            if res == -1:
                errno = rposix.get_errno()
                raise OSError(errno, os.strerror(errno))

    def read(self, size=-1):
        ll_file = self.ll_file
        if not ll_file:
            raise ValueError("I/O operation on closed file")
        if size < 0:
            # read the entire contents
            buf = lltype.malloc(rffi.CCHARP.TO, BASE_BUF_SIZE, flavor='raw')
            try:
                s = StringBuilder()
                while True:
                    returned_size = c_read(buf, 1, BASE_BUF_SIZE, ll_file)
                    if returned_size == 0:
                        if c_feof(ll_file):
                            # ok, finished
                            return s.build()
                        errno = c_ferror(ll_file)
                        c_clearerror(ll_file)
                        raise OSError(errno, os.strerror(errno))
                    s.append_charpsize(buf, returned_size)
            finally:
                lltype.free(buf, flavor='raw')
        else:
            raw_buf, gc_buf = rffi.alloc_buffer(size)
            try:
                returned_size = c_read(raw_buf, 1, size, ll_file)
                if returned_size == 0:
                    if not c_feof(ll_file):
                        errno = c_ferror(ll_file)
                        raise OSError(errno, os.strerror(errno))
                s = rffi.str_from_buffer(raw_buf, gc_buf, size,
                                         rffi.cast(lltype.Signed, returned_size))
            finally:
                rffi.keep_buffer_alive_until_here(raw_buf, gc_buf)
            return s

    def seek(self, pos, whence=0):
        ll_file = self.ll_file
        if not ll_file:
            raise ValueError("I/O operation on closed file")
        res = c_fseek(ll_file, pos, whence)
        if res == -1:
            errno = rposix.get_errno()
            raise OSError(errno, os.strerror(errno))

    def fileno(self):
        if self.ll_file:
            return intmask(c_fileno(self.ll_file))
        raise ValueError("I/O operation on closed file")

    def tell(self):
        if self.ll_file:
            res = intmask(c_ftell(self.ll_file))
            if res == -1:
                errno = rposix.get_errno()
                raise OSError(errno, os.strerror(errno))
            return res
        raise ValueError("I/O operation on closed file")

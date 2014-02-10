
""" This file makes open() and friends RPython. Note that RFile should not
be used directly and instead it's magically appearing each time you call
python builtin open()
"""

import os
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.tool import rffi_platform as platform
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rlib.rarithmetic import r_uint, intmask
from rpython.rlib import rposix
from rpython.rlib.rstring import StringBuilder

eci = ExternalCompilationInfo(includes=['stdio.h', 'unistd.h', 'sys/types.h'])

def llexternal(*args, **kwargs):
    return rffi.llexternal(*args, compilation_info=eci, **kwargs)

FILE = lltype.Struct('FILE') # opaque type maybe

class CConfig(object):
    _compilation_info_ = eci

    off_t = platform.SimpleType('off_t')


CC = platform.configure(CConfig)
OFF_T = CC['off_t']
c_open = llexternal('fopen', [rffi.CCHARP, rffi.CCHARP], lltype.Ptr(FILE))
c_close = llexternal('fclose', [lltype.Ptr(FILE)], rffi.INT)
c_fwrite = llexternal('fwrite', [rffi.CCHARP, rffi.SIZE_T, rffi.SIZE_T,
                                     lltype.Ptr(FILE)], rffi.SIZE_T)
c_fread = llexternal('fread', [rffi.CCHARP, rffi.SIZE_T, rffi.SIZE_T,
                                   lltype.Ptr(FILE)], rffi.SIZE_T)
c_feof = llexternal('feof', [lltype.Ptr(FILE)], rffi.INT)
c_ferror = llexternal('ferror', [lltype.Ptr(FILE)], rffi.INT)
c_clearerror = llexternal('clearerr', [lltype.Ptr(FILE)], lltype.Void)
c_fseek = llexternal('fseek', [lltype.Ptr(FILE), rffi.LONG, rffi.INT],
                          rffi.INT)
c_tmpfile = llexternal('tmpfile', [], lltype.Ptr(FILE))
c_fileno = llexternal('fileno', [lltype.Ptr(FILE)], rffi.INT)
c_ftell = llexternal('ftell', [lltype.Ptr(FILE)], rffi.LONG)
c_fflush = llexternal('fflush', [lltype.Ptr(FILE)], rffi.INT)
c_ftruncate = llexternal('ftruncate', [rffi.INT, OFF_T], rffi.INT, macro=True)

c_fgets = llexternal('fgets', [rffi.CCHARP, rffi.INT, lltype.Ptr(FILE)],
                     rffi.CCHARP)

c_popen = llexternal('popen', [rffi.CCHARP, rffi.CCHARP], lltype.Ptr(FILE))
c_pclose = llexternal('pclose', [lltype.Ptr(FILE)], rffi.INT)

BASE_BUF_SIZE = 4096
BASE_LINE_SIZE = 100

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

def create_popen_file(command, type):
    ll_command = rffi.str2charp(command)
    try:
        ll_type = rffi.str2charp(type)
        try:
            ll_f = c_popen(ll_command, ll_type)
            if not ll_f:
                errno = rposix.get_errno()
                raise OSError(errno, os.strerror(errno))
        finally:
            lltype.free(ll_type, flavor='raw')
    finally:
        lltype.free(ll_command, flavor='raw')
    return RPopenFile(ll_f)

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
            length = len(value)
            bytes = c_fwrite(ll_value, 1, length, ll_file)
            if bytes != length:
                errno = rposix.get_errno()
                raise OSError(errno, os.strerror(errno))
        finally:
            rffi.free_nonmovingbuffer(value, ll_value)

    def close(self):
        if self.ll_file:
            # double close is allowed
            res = self._do_close()
            self.ll_file = lltype.nullptr(FILE)
            if res == -1:
                errno = rposix.get_errno()
                raise OSError(errno, os.strerror(errno))

    def _do_close(self):
        return c_close(self.ll_file)

    def read(self, size=-1):
        # XXX CPython uses a more delicate logic here
        ll_file = self.ll_file
        if not ll_file:
            raise ValueError("I/O operation on closed file")
        if size < 0:
            # read the entire contents
            buf = lltype.malloc(rffi.CCHARP.TO, BASE_BUF_SIZE, flavor='raw')
            try:
                s = StringBuilder()
                while True:
                    returned_size = c_fread(buf, 1, BASE_BUF_SIZE, ll_file)
                    returned_size = intmask(returned_size)  # is between 0 and BASE_BUF_SIZE
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
                returned_size = c_fread(raw_buf, 1, size, ll_file)
                returned_size = intmask(returned_size)  # is between 0 and size
                if returned_size == 0:
                    if not c_feof(ll_file):
                        errno = c_ferror(ll_file)
                        raise OSError(errno, os.strerror(errno))
                s = rffi.str_from_buffer(raw_buf, gc_buf, size, returned_size)
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

    def flush(self):
        if self.ll_file:
            res = c_fflush(self.ll_file)
            if res != 0:
                errno = rposix.get_errno()
                raise OSError(errno, os.strerror(errno))
            return
        raise ValueError("I/O operation on closed file")

    def truncate(self, arg=-1):
        if self.ll_file:
            if arg == -1:
                arg = self.tell()
            res = c_ftruncate(self.fileno(), arg)
            if res == -1:
                errno = rposix.get_errno()
                raise OSError(errno, os.strerror(errno))
            return
        raise ValueError("I/O operation on closed file")

    def __del__(self):
        self.close()

    def _readline1(self, raw_buf):
        result = c_fgets(raw_buf, BASE_LINE_SIZE, self.ll_file)
        if not result:
            if c_feof(self.ll_file):   # ok
                return 0
            errno = c_ferror(self.ll_file)
            raise OSError(errno, os.strerror(errno))
        #
        # Assume that fgets() works as documented, and additionally
        # never writes beyond the final \0, which the CPython
        # fileobject.c says appears to be the case everywhere.
        # The only case where the buffer was not big enough is the
        # case where the buffer is full, ends with \0, and doesn't
        # end with \n\0.
        strlen = 0
        while raw_buf[strlen] != '\0':
            strlen += 1
        if (strlen == BASE_LINE_SIZE - 1 and
              raw_buf[BASE_LINE_SIZE - 2] != '\n'):
            return -1    # overflow!
        # common case
        return strlen

    def readline(self):
        if self.ll_file:
            raw_buf, gc_buf = rffi.alloc_buffer(BASE_LINE_SIZE)
            try:
                c = self._readline1(raw_buf)
                if c >= 0:
                    return rffi.str_from_buffer(raw_buf, gc_buf,
                                                BASE_LINE_SIZE, c)
                #
                # this is the rare case: the line is longer than BASE_LINE_SIZE
                s = StringBuilder()
                while True:
                    s.append_charpsize(raw_buf, BASE_LINE_SIZE - 1)
                    c = self._readline1(raw_buf)
                    if c >= 0:
                        break
                #
                s.append_charpsize(raw_buf, c)
                return s.build()
            finally:
                rffi.keep_buffer_alive_until_here(raw_buf, gc_buf)
        raise ValueError("I/O operation on closed file")


class RPopenFile(RFile):

    def _do_close(self):
        return c_pclose(self.ll_file)

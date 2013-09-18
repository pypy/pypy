
import os
from rpython.rlib import rposix
from rpython.rlib.rarithmetic import r_uint
from rpython.annotator import model as annmodel
from rpython.rtyper.rtyper import Repr
from rpython.rlib.rstring import StringBuilder
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.rtyper.lltypesystem.rstr import string_repr, STR
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.annlowlevel import hlstr
from rpython.rtyper.lltypesystem.lloperation import llop

FILE = lltype.Struct('FILE') # opaque type maybe
FILE_WRAPPER = lltype.GcStruct("FileWrapper", ('file', lltype.Ptr(FILE)))

eci = ExternalCompilationInfo(includes=['stdio.h'])

c_open = rffi.llexternal('fopen', [rffi.CCHARP, rffi.CCHARP],
                          lltype.Ptr(FILE), compilation_info=eci)
c_close = rffi.llexternal('fclose', [lltype.Ptr(FILE)], rffi.INT,
                          compilation_info=eci)
c_write = rffi.llexternal('fwrite', [rffi.CCHARP, rffi.SIZE_T, rffi.SIZE_T,
                                     lltype.Ptr(FILE)], rffi.SIZE_T)
c_read = rffi.llexternal('fread', [rffi.CCHARP, rffi.SIZE_T, rffi.SIZE_T,
                                   lltype.Ptr(FILE)], rffi.SIZE_T)
c_feof = rffi.llexternal('feof', [lltype.Ptr(FILE)], rffi.INT)
c_ferror = rffi.llexternal('ferror', [lltype.Ptr(FILE)], rffi.INT)
c_clearerror = rffi.llexternal('clearerr', [lltype.Ptr(FILE)], lltype.Void)
c_fseek = rffi.llexternal('fseek', [lltype.Ptr(FILE), rffi.LONG, rffi.INT],
                          rffi.INT)

def ll_open(name, mode):
    file_wrapper = lltype.malloc(FILE_WRAPPER)
    ll_name = rffi.str2charp(name)
    ll_mode = rffi.str2charp(mode)
    try:
        ll_f = c_open(ll_name, ll_mode)
        if not ll_f:
            errno = rposix.get_errno()
            raise OSError(errno, os.strerror(errno))
        file_wrapper.file = ll_f
    finally:
        lltype.free(ll_name, flavor='raw')
        lltype.free(ll_mode, flavor='raw')
    return file_wrapper

def ll_write(file_wrapper, value):
    ll_file = file_wrapper.file
    if not ll_file:
        raise ValueError("I/O operation on closed file")
    value = hlstr(value)
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

BASE_BUF_SIZE = 4096

def ll_read(file_wrapper, size):
    ll_file = file_wrapper.file
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
def ll_seek(file_wrapper, pos, whence):
    ll_file = file_wrapper.file
    if not ll_file:
        raise ValueError("I/O operation on closed file")
    res = c_fseek(ll_file, pos, whence)
    if res == -1:
        errno = rposix.get_errno()
        raise OSError(errno, os.strerror(errno))        

def ll_close(file_wrapper):
    if file_wrapper.file:
        # double close is allowed
        res = c_close(file_wrapper.file)
        file_wrapper.file = lltype.nullptr(FILE)
        if res == -1:
            errno = rposix.get_errno()
            raise OSError(errno, os.strerror(errno))

class FileRepr(Repr):
    lowleveltype = lltype.Ptr(FILE_WRAPPER)

    def __init__(self, typer):
        Repr.__init__(self)

    def rtype_constructor(self, hop):
        repr = hop.rtyper.getrepr(annmodel.SomeString())
        arg_0 = hop.inputarg(repr, 0)
        if len(hop.args_v) == 1:
            arg_1 = hop.inputconst(string_repr, "r")
        else:
            arg_1 = hop.inputarg(repr, 1)
        hop.exception_is_here()
        open = hop.rtyper.getannmixlevel().delayedfunction(
            ll_open, [annmodel.SomeString()] * 2,
            annmodel.SomePtr(self.lowleveltype))
        v_open = hop.inputconst(lltype.typeOf(open), open)
        return hop.genop('direct_call', [v_open, arg_0, arg_1],
                         resulttype=self)

    def rtype_method_write(self, hop):
        args_v = hop.inputargs(self, string_repr)
        hop.exception_is_here()
        return hop.gendirectcall(ll_write, *args_v)

    def rtype_method_close(self, hop):
        r_self = hop.inputarg(self, 0)
        hop.exception_is_here()
        return hop.gendirectcall(ll_close, r_self)

    def rtype_method_read(self, hop):
        r_self = hop.inputarg(self, 0)
        if len(hop.args_v) != 2:
            arg_1 = hop.inputconst(lltype.Signed, -1)
        else:
            arg_1 = hop.inputarg(lltype.Signed, 1)
        hop.exception_is_here()
        return hop.gendirectcall(ll_read, r_self, arg_1)

    def rtype_method_seek(self, hop):
        r_self = hop.inputarg(self, 0)
        arg_1 = hop.inputarg(lltype.Signed, 1)
        if len(hop.args_v) != 3:
            arg_2 = hop.inputconst(lltype.Signed, os.SEEK_SET)
        else:
            arg_2 = hop.inputarg(lltype.Signed, 2)
        hop.exception_is_here()
        return hop.gendirectcall(ll_seek, r_self, arg_1, arg_2)

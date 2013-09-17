
import os
from rpython.rlib import rposix
from rpython.rlib.rarithmetic import r_uint
from rpython.annotator import model as annmodel
from rpython.rtyper.rtyper import Repr
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
    value = hlstr(value)
    assert value is not None
    ll_value = rffi.get_nonmovingbuffer(value)
    try:
        # NO GC OPERATIONS HERE
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

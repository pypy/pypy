
import os
from rpython.rlib import rposix
from rpython.rtyper.rtyper import Repr
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.lltypesystem.rstr import string_repr
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.annlowlevel import hlstr

FILE = lltype.Struct('FILE') # opaque type maybe
FILE_WRAPPER = lltype.GcStruct("FileWrapper", ('file', lltype.Ptr(FILE)))

eci = ExternalCompilationInfo(includes=['stdio.h'])

c_open = rffi.llexternal('fopen', [rffi.CCHARP, rffi.CCHARP],
                          lltype.Ptr(FILE), compilation_info=eci)

def ll_open(name, mode):
    file_wrapper = lltype.malloc(FILE_WRAPPER)
    name = hlstr(name)
    mode = hlstr(mode)
    with rffi.scoped_str2charp(name) as ll_name:
        with rffi.scoped_str2charp(mode) as ll_mode:
            ll_f = c_open(ll_name, ll_mode)
            if not ll_f:
                errno = rposix.get_errno()
                raise OSError(errno, os.strerror(errno))
            file_wrapper.file = ll_f
    return file_wrapper

def ll_write(file_wrapper, value):
    value = hlstr(value)
    with rffi.scoped_str2charp(value) as ll_value:
        pass

def ll_close(file_wrapper):
    pass

class FileRepr(Repr):
    lowleveltype = lltype.Ptr(FILE_WRAPPER)

    def __init__(self, typer):
        pass

    def rtype_constructor(self, hop):
        arg_0 = hop.inputarg(string_repr, 0)
        arg_1 = hop.inputarg(string_repr, 1)
        hop.exception_is_here()
        return hop.gendirectcall(ll_open, arg_0, arg_1)

    def rtype_method_write(self, hop):
        args_v = hop.inputargs(self, string_repr)
        hop.exception_is_here()
        return hop.gendirectcall(ll_write, *args_v)

    def rtype_method_close(self, hop):
        r_self = hop.inputarg(self, 0)
        hop.exception_is_here()
        return hop.gendirectcall(ll_close, r_self)

import py
import os
from pypy.tool.autopath import pypydir
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo


cdir = py.path.local(pypydir) / 'translator' / 'stm'


eci = ExternalCompilationInfo(
    include_dirs = [cdir],
    includes = ['src_stm/et.h'],
    post_include_bits = [
        r'''#define stm_begin_transaction_inline()  ; \
              jmp_buf _jmpbuf;                   \
              setjmp(_jmpbuf);                   \
              stm_begin_transaction(&_jmpbuf);
        '''],
    separate_module_sources = ['#include "src_stm/et.c"\n'],
)

def llexternal(name, args, result, **kwds):
    return rffi.llexternal(name, args, result, compilation_info=eci,
                           _nowrapper=True, **kwds)


descriptor_init = llexternal('stm_descriptor_init', [], lltype.Void)
descriptor_done = llexternal('stm_descriptor_done', [], lltype.Void)

begin_transaction = llexternal('stm_begin_transaction_inline',[], lltype.Void)
commit_transaction = llexternal('stm_commit_transaction', [], lltype.Signed)

read_word = llexternal('stm_read_word', [rffi.VOIDPP], rffi.VOIDP)
write_word = llexternal('stm_write_word', [rffi.VOIDPP, rffi.VOIDP],
                        lltype.Void)

CALLBACK = lltype.Ptr(lltype.FuncType([rffi.VOIDP], rffi.VOIDP))
perform_transaction = llexternal('stm_perform_transaction',
                                 [CALLBACK, rffi.VOIDP], rffi.VOIDP)

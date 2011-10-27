import py
import os
from pypy.tool.autopath import pypydir
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rlib.rarithmetic import LONG_BIT


cdir = py.path.local(pypydir) / 'translator' / 'stm'

eci = ExternalCompilationInfo(
    include_dirs = [cdir],
    includes = ['src_stm/et.h'],
    pre_include_bits = ['#define PYPY_LONG_BIT %d' % LONG_BIT],
    separate_module_sources = ['#include "src_stm/et.c"\n'],
)

def llexternal(name, args, result, **kwds):
    return rffi.llexternal(name, args, result, compilation_info=eci,
                           _nowrapper=True, **kwds)

SignedP = lltype.Ptr(lltype.Array(lltype.Signed, hints={'nolength': True}))


descriptor_init = llexternal('stm_descriptor_init', [], lltype.Void)
descriptor_done = llexternal('stm_descriptor_done', [], lltype.Void)

#begin_transaction = llexternal('STM_begin_transaction', [], lltype.Void)
#commit_transaction = llexternal('stm_commit_transaction', [], lltype.Signed)

stm_read_word = llexternal('stm_read_word', [SignedP], lltype.Signed)
stm_write_word = llexternal('stm_write_word', [SignedP, lltype.Signed],
                            lltype.Void)

CALLBACK = lltype.Ptr(lltype.FuncType([rffi.VOIDP], rffi.VOIDP))
perform_transaction = llexternal('stm_perform_transaction',
                                 [CALLBACK, rffi.VOIDP], rffi.VOIDP)

abort_and_retry = llexternal('stm_abort_and_retry', [], lltype.Void)

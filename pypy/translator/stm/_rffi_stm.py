import py
import os
from pypy.tool.autopath import pypydir
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rlib.rarithmetic import LONG_BIT


cdir = py.path.local(pypydir) / 'translator' / 'stm'
cdir2 = py.path.local(pypydir) / 'translator' / 'c'

eci = ExternalCompilationInfo(
    include_dirs = [cdir, cdir2],
    includes = ['src_stm/et.h', 'src_stm/et.c'],
    pre_include_bits = ['#define PYPY_LONG_BIT %d' % LONG_BIT],
    separate_module_sources = ['\n'],    # hack for test_rffi_stm
)

def llexternal(name, args, result, **kwds):
    return rffi.llexternal(name, args, result, compilation_info=eci,
                           _nowrapper=True, **kwds)

SignedP = rffi.CArrayPtr(lltype.Signed)


stm_descriptor_init = llexternal('stm_descriptor_init', [], lltype.Void)
stm_descriptor_done = llexternal('stm_descriptor_done', [], lltype.Void)

##begin_transaction = llexternal('STM_begin_transaction', [], lltype.Void)
##begin_inevitable_transaction = llexternal('stm_begin_inevitable_transaction',
##                                          [], lltype.Void)
##commit_transaction = llexternal('stm_commit_transaction', [], lltype.Signed)
stm_try_inevitable = llexternal('stm_try_inevitable', [], lltype.Void)

##descriptor_init_and_being_inevitable_transaction = llexternal(
##    'stm_descriptor_init_and_being_inevitable_transaction', [], lltype.Void)
##commit_transaction_and_descriptor_done = llexternal(
##    'stm_commit_transaction_and_descriptor_done', [], lltype.Void)

stm_read_word = llexternal('stm_read_word', [SignedP], lltype.Signed)
stm_write_word = llexternal('stm_write_word', [SignedP, lltype.Signed],
                            lltype.Void)

CALLBACK = lltype.Ptr(lltype.FuncType([rffi.VOIDP], rffi.VOIDP))
stm_perform_transaction = llexternal('stm_perform_transaction',
                                     [CALLBACK, rffi.VOIDP], rffi.VOIDP)

stm_abort_and_retry = llexternal('stm_abort_and_retry', [], lltype.Void)

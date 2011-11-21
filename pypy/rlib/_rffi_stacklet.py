import py
from pypy.tool.autopath import pypydir
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.tool import rffi_platform
from pypy.rlib.rarithmetic import is_emulated_long
import sys


cdir = py.path.local(pypydir) / 'translator' / 'c'

eci = ExternalCompilationInfo(
    include_dirs = [cdir],
    includes = ['src/stacklet/stacklet.h'],
    separate_module_sources = ['#include "src/stacklet/stacklet.c"\n'],
)
if sys.platform == 'win32':
    if is_emulated_long:
        asmsrc = 'switch_x64_msvc.asm'
    else:
        asmsrc = 'switch_x86_msvc.asm'
    eci.separate_module_files += (cdir / 'src' / 'stacklet' / asmsrc, )
    eci.export_symbols += (
        'stacklet_newthread',
        'stacklet_deletethread',
        'stacklet_new',
        'stacklet_switch',
        'stacklet_destroy',
        '_stacklet_translate_pointer',
        )

rffi_platform.verify_eci(eci.convert_sources_to_files())

def llexternal(name, args, result, **kwds):
    return rffi.llexternal(name, args, result, compilation_info=eci,
                           _nowrapper=True, **kwds)

# ----- types -----

handle = rffi.COpaquePtr(typedef='stacklet_handle', compilation_info=eci)
thread_handle = rffi.COpaquePtr(typedef='stacklet_thread_handle',
                                compilation_info=eci)
run_fn = lltype.Ptr(lltype.FuncType([handle, llmemory.Address], handle))

# ----- constants -----

null_handle = lltype.nullptr(handle.TO)

def is_empty_handle(h):
    return rffi.cast(lltype.Signed, h) == -1

# ----- functions -----

newthread = llexternal('stacklet_newthread', [], thread_handle)
deletethread = llexternal('stacklet_deletethread',[thread_handle], lltype.Void)

new = llexternal('stacklet_new', [thread_handle, run_fn, llmemory.Address],
                 handle, random_effects_on_gcobjs=True)
switch = llexternal('stacklet_switch', [thread_handle, handle], handle,
                    random_effects_on_gcobjs=True)
destroy = llexternal('stacklet_destroy', [thread_handle, handle], lltype.Void)

_translate_pointer = llexternal("_stacklet_translate_pointer",
                                [llmemory.Address, llmemory.Address],
                                llmemory.Address)

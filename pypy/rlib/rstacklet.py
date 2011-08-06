import py
from pypy.tool.autopath import pypydir
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo

###
### Note: stacklets do not reliably work on top of CPython, but well,
### they seem to work fine after being translated...  This is due
### to the fact that on CPython, you get strange effects because the
### PyThreadState is not explicitly handled when we start a new
### stacklet or switch to another one, notably the 'frame' field.
###


cdir = py.path.local(pypydir) / 'translator' / 'c'


eci = ExternalCompilationInfo(
    include_dirs = [cdir],
    includes = ['src/stacklet/stacklet.h'],
    separate_module_sources = ['#include "src/stacklet/stacklet.c"\n'],
)

def llexternal(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=eci,
                           sandboxsafe=True)

# ----- types -----

handle = rffi.COpaquePtr(typedef='stacklet_handle', compilation_info=eci)
thread_handle = rffi.COpaquePtr(typedef='stacklet_thread_handle',
                                compilation_info=eci)
run_fn = lltype.Ptr(lltype.FuncType([handle, rffi.VOIDP], handle))

# ----- constants -----

def is_empty_handle(h):
    return rffi.cast(lltype.Signed, h) == -1

# ----- functions -----

newthread = llexternal('stacklet_newthread', [], thread_handle)
deletethread = llexternal('stacklet_deletethread',[thread_handle], lltype.Void)

new = llexternal('stacklet_new', [thread_handle, run_fn, rffi.VOIDP],
                 handle)
switch = llexternal('stacklet_switch', [thread_handle, handle], handle)
destroy = llexternal('stacklet_destroy', [thread_handle, handle], lltype.Void)

from pypy.rpython.lltypesystem import lltype, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo

###
### Note: stacklets do not reliably work on top of CPython, but well,
### they seem to work fine after being translated...
###


#cdir = py.path.local(pypydir) / 'translator' / 'c'
cdir = '/home/arigo/hg/arigo/hack/pypy-hack/stacklet'


eci = ExternalCompilationInfo(
    include_dirs = [cdir],
    includes = ['stacklet.h'],
    separate_module_sources = ['#include "stacklet.c"\n'],
)

def llexternal(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=eci)


# ----- types -----

handle = lltype.Signed
thread_handle = lltype.Signed
run_fn = lltype.Ptr(lltype.FuncType([handle, lltype.Signed], handle))

# ----- constants -----

EMPTY_STACK_HANDLE = -1

# ----- functions -----

newthread = llexternal('stacklet_newthread', [], thread_handle)
deletethread = llexternal('stacklet_deletethread',[thread_handle], lltype.Void)

new = llexternal('stacklet_new', [thread_handle, run_fn, lltype.Signed],
                 handle)
switch = llexternal('stacklet_switch', [thread_handle, handle], handle)
destroy = llexternal('stacklet_destroy', [thread_handle, handle], lltype.Void)

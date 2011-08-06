import py
from pypy.tool.autopath import pypydir
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.annlowlevel import llhelper

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
                           _nowrapper=True)

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

_new = llexternal('stacklet_new', [thread_handle, run_fn, rffi.VOIDP],
                  handle)
_switch = llexternal('stacklet_switch', [thread_handle, handle], handle)
_destroy = llexternal('stacklet_destroy', [thread_handle, handle], lltype.Void)

_translate_pointer = llexternal("_stacklet_translate_pointer",
                                [handle, llmemory.Address],
                                llmemory.Address)

# ____________________________________________________________

def getgcclass(gcrootfinder):
    gcrootfinder = gcrootfinder.replace('/', '_')
    module = __import__('pypy.rlib._stacklet_%s' % gcrootfinder,
                        None, None, ['__doc__'])
    return module.StackletGcRootFinder
getgcclass._annspecialcase_ = 'specialize:memo'

def new(gcrootfinder, thrd, runfn, arg):
    c = getgcclass(gcrootfinder)
    return c.new(thrd, llhelper(run_fn, runfn), arg)
new._annspecialcase_ = 'specialize:arg(2)'

def switch(gcrootfinder, thrd, h):
    c = getgcclass(gcrootfinder)
    return c.switch(thrd, h)

def destroy(gcrootfinder, thrd, h):
    c = getgcclass(gcrootfinder)
    c.destroy(thrd, h)

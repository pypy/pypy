
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.rffi import platform
from pypy.rpython.extfunc import genericcallable
from pypy.module.thread.os_thread import Bootstrapper
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr
from pypy.translator.tool.cbuild import cache_c_module
from pypy.rpython.lltypesystem import llmemory
import thread, py
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem.lltype import typeOf

class BaseBootstrapper:
    def bootstrap(self):
        pass

class ThreadError(Exception):
    def __init__(self, msg):
        self.msg = msg

class Lock(object):
    """ Container for low-level implementation
    of a lock object
    """
    def __init__(self, ll_lock):
        self._lock = ll_lock

includes = ['unistd.h', 'src/thread.h']
from pypy.tool.autopath import pypydir
pypydir = py.path.local(pypydir)
srcdir = pypydir.join('translator', 'c', 'src')

def setup_thread_so():
    files = [srcdir.join('thread.c')]
    modname = '_thread'
    cache_c_module(files, modname, include_dirs=[str(srcdir)])
    return str(pypydir.join('_cache', modname)) + '.so'
libraries = [setup_thread_so()]

def llexternal(name, args, result):
    return rffi.llexternal(name, args, result, includes=includes,
                           libraries=libraries)

CALLBACK = lltype.Ptr(lltype.FuncType([rffi.VOIDP], rffi.VOIDP))
c_thread_start = llexternal('RPyThreadStart', [CALLBACK, rffi.VOIDP], rffi.INT)
c_thread_get_ident = llexternal('RPyThreadGetIdent', [], rffi.INT)

TLOCKP = rffi.COpaque('struct RPyOpaque_ThreadLock', includes=includes)

c_thread_lock_init = llexternal('RPyThreadLockInit', [TLOCKP], lltype.Void)
c_thread_acuirelock = llexternal('RPyThreadAcquireLock', [TLOCKP, rffi.INT],
                                 rffi.INT)
c_thread_releaselock = llexternal('RPyThreadReleaseLock', [TLOCKP], lltype.Void)

def ll_allocate_lock():
    ll_lock = lltype.malloc(TLOCKP.TO, flavor='raw')
    res = c_thread_lock_init(ll_lock)
    if res == -1:
        raise ThreadError("out of resources")
    return Lock(ll_lock)

def ll_acquire_lock(lock, waitflag):
    return c_thread_acuirelock(lock._lock, waitflag)

def ll_release_lock(lock):
    try:
        if ll_acquire_lock(lock, 0):
            raise ThreadError("bad lock")
    finally:
        c_thread_releaselock(lock._lock)

# a simple wrapper, not to expose C functions (is this really necessary?)
def ll_get_ident():
    return c_thread_get_ident()

def start_new_thread(x, y):
    raise NotImplementedError("Should never be invoked directly")

def ll_start_new_thread(l_func, arg):
    l_arg = cast_instance_to_base_ptr(arg)
    l_arg = rffi.cast(rffi.VOIDP, l_arg)
    return c_thread_start(l_func, l_arg)

class LLStartNewThread(ExtRegistryEntry):
    _about_ = start_new_thread
    
    def compute_result_annotation(self, s_func, s_arg):
        bookkeeper = self.bookkeeper
        s_result = bookkeeper.emulate_pbc_call(bookkeeper.position_key,
                                               s_func, [s_arg])
        assert annmodel.s_None.contains(s_result)
        return annmodel.SomeInteger()
    
    def specialize_call(self, hop):
        rtyper = hop.rtyper
        bk = rtyper.annotator.bookkeeper
        r_result = rtyper.getrepr(hop.s_result)
        hop.exception_is_here()
        args_r = [rtyper.getrepr(s_arg) for s_arg in hop.args_s]
        _callable = hop.args_s[0].const
        funcptr = lltype.functionptr(CALLBACK.TO, _callable.func_name,
                                     _callable=_callable)
        func_s = bk.immutablevalue(funcptr)
        s_args = [func_s, hop.args_s[1]]
        obj = rtyper.getannmixlevel().delayedfunction(
            ll_start_new_thread, s_args, annmodel.SomeInteger())
        bootstrap = rtyper.getannmixlevel().delayedfunction(
            _callable, [hop.args_s[1]], annmodel.s_None)
        vlist = [hop.inputconst(typeOf(obj), obj),
                 hop.inputconst(typeOf(bootstrap), bootstrap),
                 #hop.inputarg(args_r[0], 0),
                 hop.inputarg(args_r[1], 1)]
        return hop.genop('direct_call', vlist, r_result)

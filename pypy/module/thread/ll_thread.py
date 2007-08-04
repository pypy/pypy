
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.rffi import platform
from pypy.rpython.extfunc import genericcallable
from pypy.module.thread.os_thread import Bootstrapper
from pypy.translator.tool.cbuild import cache_c_module
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr,\
     cast_base_ptr_to_instance
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

includes = ['unistd.h', 'thread.h']

def setup_thread_so():
    from pypy.tool.autopath import pypydir
    pypydir = py.path.local(pypydir)
    srcdir = pypydir.join('translator', 'c', 'src')
    modname = '_thread'
    files = [srcdir.join('thread.c')]
    cache_c_module(files, modname, include_dirs=[str(srcdir)])
    return str(pypydir.join('_cache', modname)) + '.so'
libraries = [setup_thread_so()]

def llexternal(name, args, result):
    return rffi.llexternal(name, args, result, includes=includes,
                           libraries=libraries)

CALLBACK = lltype.FuncType([rffi.VOIDP], rffi.VOIDP)
c_thread_start = llexternal('RPyThreadStart', [CALLBACK, rffi.VOIDP], rffi.INT)
c_thread_get_ident = llexternal('RPyThreadGetIdent', [], lltype.Void)

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

def ll_start_new_thread(l_func, arg):
    l_arg = cast_instance_to_base_ptr(arg)
    ident = c_thread_start(l_func, l_arg)
    if ident == -1:
        raise ThreadError("can't start new thread")
    return ident

class LLStartNewThread(ExtRegistryEntry):
    _about_ = ll_start_new_thread

    def compute_result_annotation(self, s_func, s_arg):
        bookkeeper = self.bookkeeper
        assert s_func.is_constant(), "Cannot call ll_start_new_thread with non-constant function"
        s_result = bookkeeper.emulate_pbc_call(bookkeeper.position_key,
                                               s_func, [s_arg])
        assert annmodel.s_None.contains(s_result), (
            """thread.start_new_thread(f, arg): f() should return None""")
        return annmodel.SomeInteger()

    def compute_annotation_bk(self, bookkeeper):
        return annmodel.SomePBC([bookkeeper.getdesc(self.instance)])

    def specialize_call(self, hop):
        rtyper = hop.rtyper
        bookkeeper = rtyper.annotator.bookkeeper
        _callable = hop.args_s[0].const
        args_r = [rtyper.getrepr(s_arg) for s_arg in hop.args_s]
        ll_arg = args_r[1].lowleveltype
        _type = lltype.FuncType([ll_arg], lltype.Void)
        funcptr = lltype.functionptr(_type, _callable.func_name,
                                     _callable=_callable)
        r_result = rtyper.getrepr(hop.s_result)
        ll_result = r_result.lowleveltype
        args_s = [bookkeeper.immutablevalue(i) for i in [funcptr, ll_arg]]
        obj = rtyper.getannmixlevel().delayedfunction(
            ll_start_new_thread, args_s, annmodel.SomeInteger())
        vlist = [hop.inputconst(typeOf(obj), obj)] + hop.inputargs(*args_r)
        hop.exception_is_here()
        return hop.genop('direct_call', vlist, r_result)

# a simple wrapper, not to expose C functions (is this really necessary?)
def ll_get_ident():
    return c_thread_get_ident()

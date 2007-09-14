
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.rffi import platform
from pypy.rpython.extfunc import genericcallable
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr
from pypy.translator.tool.cbuild import cache_c_module
from pypy.rpython.lltypesystem import llmemory
import thread, py
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem.lltype import typeOf
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.nonconst import NonConstant

class error(Exception):
    def __init__(self, msg):
        self.msg = msg

from pypy.tool.autopath import pypydir
pypydir = py.path.local(pypydir)
c_dir = pypydir.join('translator', 'c')
includes = ['unistd.h', 'src/thread.h']

def setup_thread_so():
    # XXX this is quiiiiiiiite a hack!
    files = [c_dir.join('src', 'thread.c')]
    modname = '_thread'
    cache_c_module(files, modname, include_dirs=[str(c_dir)])
    return str(pypydir.join('_cache', modname)) + '.so'
libraries = [setup_thread_so()]

def llexternal(name, args, result):
    return rffi.llexternal(name, args, result, includes=includes,
                           libraries=libraries, include_dirs=[str(c_dir)])

CALLBACK = lltype.Ptr(lltype.FuncType([rffi.VOIDP], rffi.VOIDP))
c_thread_start = llexternal('RPyThreadStart', [CALLBACK, rffi.VOIDP], rffi.INT)
c_thread_get_ident = llexternal('RPyThreadGetIdent', [], rffi.INT)

TLOCKP = rffi.COpaquePtr('struct RPyOpaque_ThreadLock', includes=includes)

c_thread_lock_init = llexternal('RPyThreadLockInit', [TLOCKP], lltype.Void)
c_thread_acquirelock = llexternal('RPyThreadAcquireLock', [TLOCKP, rffi.INT],
                                  rffi.INT)
c_thread_releaselock = llexternal('RPyThreadReleaseLock', [TLOCKP], lltype.Void)
c_thread_fused_releaseacquirelock = llexternal(
    'RPyThreadFusedReleaseAcquireLock', [TLOCKP], lltype.Void)

def allocate_lock():
    ll_lock = lltype.malloc(TLOCKP.TO, flavor='raw')
    res = c_thread_lock_init(ll_lock)
    if res == -1:
        lltype.free(ll_lock, flavor='raw')
        raise error("out of resources")
    return Lock(ll_lock)

def _start_new_thread(x, y):
    return thread.start_new_thread(x, (y,))

def ll_start_new_thread(l_func, arg):
    l_arg = cast_instance_to_base_ptr(arg)
    l_arg = rffi.cast(rffi.VOIDP, l_arg)
    ident = c_thread_start(l_func, l_arg)
    if ident == -1:
        raise error("can't start new thread")
    return ident

class LLStartNewThread(ExtRegistryEntry):
    _about_ = _start_new_thread
    
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

# wrappers...

def get_ident():
    return c_thread_get_ident()

def start_new_thread(x, y):
    return _start_new_thread(x, y[0])

class Lock(object):
    """ Container for low-level implementation
    of a lock object
    """
    def __init__(self, ll_lock):
        self._lock = ll_lock

    def acquire(self, flag):
        return bool(c_thread_acquirelock(self._lock, int(flag)))

    def release(self):
        # Sanity check: the lock must be locked
        if self.acquire(False):
            c_thread_releaselock(self._lock)
            raise error(NonConstant("bad lock"))
        else:
            c_thread_releaselock(self._lock)

    def fused_release_acquire(self):
        # Sanity check: the lock must be locked
        if self.acquire(False):
            c_thread_releaselock(self._lock)
            raise error(NonConstant("bad lock"))
        else:
            c_thread_fused_releaseacquirelock(self._lock)

    def __del__(self):
        lltype.free(self._lock, flavor='raw')


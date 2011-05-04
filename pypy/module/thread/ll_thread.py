
from pypy.rpython.lltypesystem import rffi, lltype, llmemory
from pypy.rpython.tool import rffi_platform as platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo
import py, os
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rlib import jit
from pypy.rlib.debug import ll_assert
from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.tool import autopath

class error(Exception):
    pass

eci = ExternalCompilationInfo(
    includes = ['src/thread.h'],
    separate_module_sources = [''],
    include_dirs = [str(py.path.local(autopath.pypydir).join('translator', 'c'))],
    export_symbols = ['RPyThreadGetIdent', 'RPyThreadLockInit',
                      'RPyThreadAcquireLock', 'RPyThreadReleaseLock',
                      'RPyThreadYield',
                      'RPyThreadGetStackSize', 'RPyThreadSetStackSize',
                      'RPyThreadAfterFork']
)

def llexternal(name, args, result, **kwds):
    kwds.setdefault('sandboxsafe', True)
    return rffi.llexternal(name, args, result, compilation_info=eci,
                           **kwds)

def _emulated_start_new_thread(func):
    "NOT_RPYTHON"
    import thread
    try:
        ident = thread.start_new_thread(func, ())
    except thread.error:
        ident = -1
    return rffi.cast(rffi.LONG, ident)

CALLBACK = lltype.Ptr(lltype.FuncType([], lltype.Void))
c_thread_start = llexternal('RPyThreadStart', [CALLBACK], rffi.LONG,
                            _callable=_emulated_start_new_thread,
                            threadsafe=True)  # release the GIL, but most
                                              # importantly, reacquire it
                                              # around the callback
c_thread_get_ident = llexternal('RPyThreadGetIdent', [], rffi.LONG,
                                _nowrapper=True)    # always call directly

TLOCKP = rffi.COpaquePtr('struct RPyOpaque_ThreadLock',
                          compilation_info=eci)

c_thread_lock_init = llexternal('RPyThreadLockInit', [TLOCKP], rffi.INT,
                                threadsafe=False)   # may add in a global list
c_thread_acquirelock = llexternal('RPyThreadAcquireLock', [TLOCKP, rffi.INT],
                                  rffi.INT,
                                  threadsafe=True)    # release the GIL
c_thread_releaselock = llexternal('RPyThreadReleaseLock', [TLOCKP], lltype.Void,
                                  threadsafe=True)    # release the GIL

# another set of functions, this time in versions that don't cause the
# GIL to be released.  To use to handle the GIL lock itself.
c_thread_acquirelock_NOAUTO = llexternal('RPyThreadAcquireLock',
                                         [TLOCKP, rffi.INT], rffi.INT,
                                         _nowrapper=True)
c_thread_releaselock_NOAUTO = llexternal('RPyThreadReleaseLock',
                                         [TLOCKP], lltype.Void,
                                         _nowrapper=True)

# this function does nothing apart from releasing the GIL temporarily.
yield_thread = llexternal('RPyThreadYield', [], lltype.Void, threadsafe=True)

def allocate_lock():
    return Lock(allocate_ll_lock())

def ll_start_new_thread(func):
    ident = c_thread_start(func)
    if ident == -1:
        raise error("can't start new thread")
    return ident

# wrappers...

@jit.loop_invariant
def get_ident():
    return rffi.cast(lltype.Signed, c_thread_get_ident())

def start_new_thread(x, y):
    """In RPython, no argument can be passed.  You have to use global
    variables to pass information to the new thread.  That's not very
    nice, but at least it avoids some levels of GC issues.
    """
    assert len(y) == 0
    return rffi.cast(lltype.Signed, ll_start_new_thread(x))

class Lock(object):
    """ Container for low-level implementation
    of a lock object
    """
    def __init__(self, ll_lock):
        self._lock = ll_lock

    def acquire(self, flag):
        res = c_thread_acquirelock(self._lock, int(flag))
        res = rffi.cast(lltype.Signed, res)
        return bool(res)

    def release(self):
        # Sanity check: the lock must be locked
        if self.acquire(False):
            c_thread_releaselock(self._lock)
            raise error("bad lock")
        else:
            c_thread_releaselock(self._lock)

    def __del__(self):
        free_ll_lock(self._lock)

    def __enter__(self):
        self.acquire(True)
        
    def __exit__(self, *args):
        self.release()

# ____________________________________________________________
#
# Stack size

get_stacksize = llexternal('RPyThreadGetStackSize', [], lltype.Signed)
set_stacksize = llexternal('RPyThreadSetStackSize', [lltype.Signed],
                           lltype.Signed)

# ____________________________________________________________
#
# Hack

thread_after_fork = llexternal('RPyThreadAfterFork', [], lltype.Void)

# ____________________________________________________________
#
# GIL support wrappers

null_ll_lock = lltype.nullptr(TLOCKP.TO)

def allocate_ll_lock():
    # track_allocation=False here; be careful to lltype.free() it.  The
    # reason it is set to False is that we get it from all app-level
    # lock objects, as well as from the GIL, which exists at shutdown.
    ll_lock = lltype.malloc(TLOCKP.TO, flavor='raw', track_allocation=False)
    res = c_thread_lock_init(ll_lock)
    if rffi.cast(lltype.Signed, res) <= 0:
        lltype.free(ll_lock, flavor='raw', track_allocation=False)
        raise error("out of resources")
    return ll_lock

def free_ll_lock(ll_lock):
    lltype.free(ll_lock, flavor='raw', track_allocation=False)

def acquire_NOAUTO(ll_lock, flag):
    flag = rffi.cast(rffi.INT, int(flag))
    res = c_thread_acquirelock_NOAUTO(ll_lock, flag)
    res = rffi.cast(lltype.Signed, res)
    return bool(res)

def release_NOAUTO(ll_lock):
    if not we_are_translated():
        ll_assert(not acquire_NOAUTO(ll_lock, False), "NOAUTO lock not held!")
    c_thread_releaselock_NOAUTO(ll_lock)

# ____________________________________________________________
#
# Thread integration.
# These are six completely ad-hoc operations at the moment.

def gc_thread_prepare():
    """To call just before thread.start_new_thread().  This
    allocates a new shadow stack to be used by the future
    thread.  If memory runs out, this raises a MemoryError
    (which can be handled by the caller instead of just getting
    ignored if it was raised in the newly starting thread).
    """
    if we_are_translated():
        llop.gc_thread_prepare(lltype.Void)

def gc_thread_run():
    """To call whenever the current thread (re-)acquired the GIL.
    """
    if we_are_translated():
        llop.gc_thread_run(lltype.Void)
gc_thread_run._always_inline_ = True

def gc_thread_start():
    """To call at the beginning of a new thread.
    """
    if we_are_translated():
        llop.gc_thread_start(lltype.Void)

def gc_thread_die():
    """To call just before the final GIL release done by a dying
    thread.  After a thread_die(), no more gc operation should
    occur in this thread.
    """
    if we_are_translated():
        llop.gc_thread_die(lltype.Void)
gc_thread_die._always_inline_ = True

def gc_thread_before_fork():
    """To call just before fork().  Prepares for forking, after
    which only the current thread will be alive.
    """
    if we_are_translated():
        return llop.gc_thread_before_fork(llmemory.Address)
    else:
        return llmemory.NULL

def gc_thread_after_fork(result_of_fork, opaqueaddr):
    """To call just after fork().
    """
    if we_are_translated():
        llop.gc_thread_after_fork(lltype.Void, result_of_fork, opaqueaddr)
    else:
        assert opaqueaddr == llmemory.NULL

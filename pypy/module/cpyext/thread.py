
from pypy.module.thread import ll_thread
from pypy.module.cpyext.api import CANNOT_FAIL, cpython_api
from pypy.rpython.lltypesystem import lltype, rffi

@cpython_api([], rffi.LONG, error=CANNOT_FAIL)
def PyThread_get_thread_ident(space):
    return ll_thread.get_ident()

LOCKP = rffi.COpaquePtr(typedef='PyThread_type_lock')

@cpython_api([], LOCKP)
def PyThread_allocate_lock(space):
    lock = ll_thread.allocate_ll_lock()
    return rffi.cast(LOCKP, lock)

@cpython_api([LOCKP], lltype.Void)
def PyThread_free_lock(space, lock):
    lock = rffi.cast(ll_thread.TLOCKP, lock)
    ll_thread.free_ll_lock(lock)

@cpython_api([LOCKP, rffi.INT], rffi.INT, error=CANNOT_FAIL)
def PyThread_acquire_lock(space, lock, waitflag):
    lock = rffi.cast(ll_thread.TLOCKP, lock)
    return ll_thread.c_thread_acquirelock(lock, waitflag)

@cpython_api([LOCKP], lltype.Void)
def PyThread_release_lock(space, lock):
    lock = rffi.cast(ll_thread.TLOCKP, lock)
    ll_thread.c_thread_releaselock(lock)



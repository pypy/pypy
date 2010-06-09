
from pypy.module.thread import ll_thread
from pypy.module.cpyext.gateway import CANNOT_FAIL, cpython_api
from pypy.rpython.lltypesystem import rffi

@cpython_api([], rffi.LONG, error=CANNOT_FAIL)
def PyThread_get_thread_ident(space):
    return ll_thread.get_ident()


# @cpython_api([ll_thread.TLOCKP, rffi.INT], rffi.INT, error=CANNOT_FAIL)
# def PyThread_acquire_lock(space, lock, waitflag):
#     return ll_thread.Lock(lock).acquire(waitflag)

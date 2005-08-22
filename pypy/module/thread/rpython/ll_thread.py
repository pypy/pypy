"""
Dummy low-level implementations for the external functions of the 'thread'
module.
"""

import thread
from pypy.rpython.lltype import malloc
from pypy.rpython.module.support import init_opaque_object, from_opaque_object
from pypy.module.thread.rpython.exttable import locktypeinfo

LOCKCONTAINERTYPE = locktypeinfo.get_lltype()


def ll_thread_start_new_thread(funcptr, argtuple):
    # wrapper around ll_thread_start, to extract the single argument
    # from the argtuple.
    argument = argtuple.item0   # expects a single argument
    return ll_thread_start(funcptr, argument)

def ll_thread_start(funcptr, argument):
    return thread.start_new_thread(funcptr, (argument,))
ll_thread_start.suggested_primitive = True

def ll_thread_get_ident():
    return thread.get_ident()
ll_thread_get_ident.suggested_primitive = True


def newlock(opaqueptr):
    init_opaque_object(opaqueptr, thread.allocate_lock())
newlock.suggested_primitive = True

def acquirelock(opaqueptr, waitflag):
    lock = from_opaque_object(opaqueptr)
    return lock.acquire(waitflag)
acquirelock.suggested_primitive = True

def releaselock(opaqueptr):
    lock = from_opaque_object(opaqueptr)
    lock.release()
releaselock.suggested_primitive = True

def ll_thread_allocate_lock():
    lockcontainer = malloc(LOCKCONTAINERTYPE)
    newlock(lockcontainer.obj)
    return lockcontainer

def ll_thread_acquire_lock(lockcontainer, waitflag):
    return acquirelock(lockcontainer.obj, waitflag)

def ll_thread_release_lock(lockcontainer):
    releaselock(lockcontainer.obj)

"""
Dummy low-level implementations for the external functions of the 'thread'
module.
"""

import thread
from pypy.rpython.lltypesystem.lltype import malloc
from pypy.rpython.module.support import init_opaque_object, from_opaque_object
from pypy.module.thread.rpython.exttable import locktypeinfo

LOCKCONTAINERTYPE = locktypeinfo.get_lltype()


def ll_thread_start_new_thread(funcptr, argtuple):
    # wrapper around ll_thread_start, to extract the single argument
    # from the argtuple.
    argument = argtuple.item0   # expects a single argument
    return ll_thread_start(funcptr, argument)

def ll_thread_start(funcptr, argument):
    #return thread.start_new_thread(funcptr, (argument,))
    # XXX we just return an integer here, because we cannot really call back
    # XXX into thread.start_new_thread().  Indeed, 'funcptr' is not a normal
    # XXX function object, but a low-level pointer to a _func.  This also
    # XXX confuses the annotator.
    # note that running this won't really work, but anyway llinterpreter
    # is probably quite confused if we start multiple threads
    return 1234
ll_thread_start.suggested_primitive = True

def ll_thread_get_ident():
    return thread.get_ident()
ll_thread_get_ident.suggested_primitive = True


def ll_newlock(opaqueptr):
    init_opaque_object(opaqueptr, thread.allocate_lock())
ll_newlock.suggested_primitive = True

def ll_acquirelock(opaqueptr, waitflag):
    lock = from_opaque_object(opaqueptr)
    return lock.acquire(waitflag)
ll_acquirelock.suggested_primitive = True

def ll_releaselock(opaqueptr):
    lock = from_opaque_object(opaqueptr)
    lock.release()
ll_releaselock.suggested_primitive = True

def ll_thread_allocate_lock():
    lockcontainer = malloc(LOCKCONTAINERTYPE)
    ll_newlock(lockcontainer.obj)
    return lockcontainer

def ll_thread_acquire_lock(lockcontainer, waitflag):
    return ll_acquirelock(lockcontainer.obj, waitflag)

def ll_thread_release_lock(lockcontainer):
    ll_releaselock(lockcontainer.obj)

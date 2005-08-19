"""
Dummy low-level implementations for the external functions of the 'thread'
module.
"""

import thread
from pypy.rpython.module.support import from_rexternalobj, to_rexternalobj

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


def ll_thread_allocate_lock():
    lock = thread.allocate_lock()
    return to_rexternalobj(lock)
ll_thread_allocate_lock.suggested_primitive = True

def ll_thread_acquire_lock(lockptr, waitflag):
    lock = from_rexternalobj(lockptr)
    return lock.acquire(waitflag)
ll_thread_acquire_lock.suggested_primitive = True

def ll_thread_release_lock(lockptr):
    lock = from_rexternalobj(lockptr)
    lock.release()
ll_thread_release_lock.suggested_primitive = True

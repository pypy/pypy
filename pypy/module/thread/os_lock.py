"""
Python locks, based on true threading locks provided by the OS.
"""

import time
from rpython.rlib import rthread
from pypy.module.thread.error import wrap_thread_error
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.error import oefmt
from rpython.rlib.rarithmetic import r_longlong, ovfcheck_float_to_longlong


RPY_LOCK_FAILURE, RPY_LOCK_ACQUIRED, RPY_LOCK_INTR = range(3)

def parse_acquire_args(space, blocking, timeout):
    if not blocking and timeout != -1.0:
        raise oefmt(space.w_ValueError,
                    "can't specify a timeout for a non-blocking call")
    if timeout < 0.0 and timeout != -1.0:
        raise oefmt(space.w_ValueError,
                    "timeout value must be strictly positive")
    if not blocking:
        microseconds = 0
    elif timeout == -1.0:
        microseconds = -1
    else:
        timeout *= 1e6
        try:
            microseconds = ovfcheck_float_to_longlong(timeout)
        except OverflowError:
            raise oefmt(space.w_OverflowError, "timeout value is too large")
    return microseconds


def acquire_timed(space, lock, microseconds):
    """Helper to acquire an interruptible lock with a timeout."""
    endtime = (time.time() * 1e6) + microseconds
    while True:
        result = lock.acquire_timed(microseconds)
        if result == RPY_LOCK_INTR:
            # Run signal handlers if we were interrupted
            space.getexecutioncontext().checksignals()
            if microseconds >= 0:
                microseconds = r_longlong((endtime - (time.time() * 1e6))
                                          + 0.999)
                # Check for negative values, since those mean block
                # forever
                if microseconds <= 0:
                    result = RPY_LOCK_FAILURE
        if result != RPY_LOCK_INTR:
            break
    return result


class Lock(W_Root):
    "A box around an interp-level lock object."

    _immutable_fields_ = ["lock"]

    def __init__(self, space):
        self.space = space
        try:
            self.lock = rthread.allocate_lock()
        except rthread.error:
            raise wrap_thread_error(space, "out of resources")

    @unwrap_spec(blocking=int)
    def descr_lock_acquire(self, space, blocking=1):
        """Lock the lock.  With the default argument of True, this blocks
if the lock is already locked (even by the same thread), waiting for
another thread to release the lock, and returns True once the lock is
acquired.  With an argument of False, this will always return immediately
and the return value reflects whether the lock is acquired.
The blocking operation is not interruptible."""
        mylock = self.lock
        result = mylock.acquire(bool(blocking))
        return space.newbool(result)

    @unwrap_spec(blocking=int, timeout=float)
    def descr_lock_py3k_acquire(self, space, blocking=1, timeout=-1.0):
        """(Backport of a Python 3 API for PyPy.  This version takes
a timeout argument and handles signals, like Ctrl-C.)

Lock the lock.  Without argument, this blocks if the lock is already
locked (even by the same thread), waiting for another thread to release
the lock, and return None once the lock is acquired.
With an argument, this will only block if the argument is true,
and the return value reflects whether the lock is acquired.
The blocking operation is interruptible."""
        microseconds = parse_acquire_args(space, blocking, timeout)
        result = acquire_timed(space, self.lock, microseconds)
        return space.newbool(result == RPY_LOCK_ACQUIRED)

    def descr_lock_release(self, space):
        """Release the lock, allowing another thread that is blocked waiting for
the lock to acquire the lock.  The lock must be in the locked state,
but it needn't be locked by the same thread that unlocks it."""
        try:
            self.lock.release()
        except rthread.error:
            raise wrap_thread_error(space, "release unlocked lock")

    def descr_lock_locked(self, space):
        """Return whether the lock is in the locked state."""
        if self.lock.acquire(False):
            self.lock.release()
            return space.w_False
        else:
            return space.w_True

    def descr__enter__(self, space):
        self.descr_lock_acquire(space)
        return self

    def descr__exit__(self, space, __args__):
        self.descr_lock_release(space)

    def __enter__(self):
        self.descr_lock_acquire(self.space)
        return self

    def __exit__(self, *args):
        self.descr_lock_release(self.space)

descr_acquire = interp2app(Lock.descr_lock_acquire)
descr_release = interp2app(Lock.descr_lock_release)
descr_locked  = interp2app(Lock.descr_lock_locked)
descr__enter__ = interp2app(Lock.descr__enter__)
descr__exit__ = interp2app(Lock.descr__exit__)
descr_py3k_acquire = interp2app(Lock.descr_lock_py3k_acquire)


Lock.typedef = TypeDef("thread.lock",
    __doc__ = """\
A lock object is a synchronization primitive.  To create a lock,
call the thread.allocate_lock() function.  Methods are:

acquire() -- lock the lock, possibly blocking until it can be obtained
release() -- unlock of the lock
locked() -- test whether the lock is currently locked

A lock is not owned by the thread that locked it; another thread may
unlock it.  A thread attempting to lock a lock that it has already locked
will block until another thread unlocks it.  Deadlocks may ensue.""",
    acquire = descr_acquire,
    _py3k_acquire = descr_py3k_acquire,
    release = descr_release,
    locked  = descr_locked,
    __enter__ = descr__enter__,
    __exit__ = descr__exit__,
    # Obsolete synonyms
    acquire_lock = descr_acquire,
    release_lock = descr_release,
    locked_lock  = descr_locked,
    )


def allocate_lock(space):
    """Create a new lock object.  (allocate() is an obsolete synonym.)
See LockType.__doc__ for information about locks."""
    return space.wrap(Lock(space))

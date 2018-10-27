"""
Python locks, based on true threading locks provided by the OS.
"""

import time
from rpython.rlib import rthread
from pypy.module.thread.error import wrap_thread_error
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, make_weakref_descr
from pypy.interpreter.error import OperationError, oefmt
from rpython.rlib.rarithmetic import r_longlong, ovfcheck, ovfcheck_float_to_longlong


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

def try_release(space, lock):
    try:
        lock.release()
    except rthread.error:
        raise wrap_thread_error(space, "release unlocked lock")


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
        try_release(space, self.lock)

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
    __weakref__ = make_weakref_descr(Lock),
    # Obsolete synonyms
    acquire_lock = descr_acquire,
    release_lock = descr_release,
    locked_lock  = descr_locked,
    )


def allocate_lock(space):
    """Create a new lock object.  (allocate() is an obsolete synonym.)
See LockType.__doc__ for information about locks."""
    return Lock(space)

class W_RLock(W_Root):
    # Does not exist in CPython 2.x. Back-ported from PyPy3. See issue #2905

    def __init__(self, space, w_active=None):
        self.rlock_count = 0
        self.rlock_owner = 0
        self.w_active = w_active    # dictionary 'threading._active'
        try:
            self.lock = rthread.allocate_lock()
        except rthread.error:
            raise wrap_thread_error(space, "cannot allocate lock")

    def descr__new__(space, w_subtype, w_active=None):
        self = space.allocate_instance(W_RLock, w_subtype)
        W_RLock.__init__(self, space, w_active)
        return self

    def descr__repr__(self, space):
        w_type = space.type(self)
        classname = w_type.name
        if self.rlock_owner == 0:
            owner = "None"
        else:
            owner = str(self.rlock_owner)
            if self.w_active is not None:
                try:
                    w_owner = space.getitem(self.w_active,
                                                space.newint(self.rlock_owner))
                    w_name = space.getattr(w_owner, space.newtext('name'))
                    owner = space.text_w(space.repr(w_name))
                except OperationError as e:
                    if e.async(space):
                        raise
        return space.newtext("<%s owner=%s count=%d>" % (
            classname, owner, self.rlock_count))

    @unwrap_spec(blocking=int)
    def acquire_w(self, space, blocking=1):
        """Acquire a lock, blocking or non-blocking.

        When invoked without arguments: if this thread already owns the lock,
        increment the recursion level by one, and return immediately. Otherwise,
        if another thread owns the lock, block until the lock is unlocked. Once
        the lock is unlocked (not owned by any thread), then grab ownership, set
        the recursion level to one, and return. If more than one thread is
        blocked waiting until the lock is unlocked, only one at a time will be
        able to grab ownership of the lock. There is no return value in this
        case.

        When invoked with the blocking argument set to true, do the same thing
        as when called without arguments, and return true.

        When invoked with the blocking argument set to false, do not block. If a
        call without an argument would block, return false immediately;
        otherwise, do the same thing as when called without arguments, and
        return true.

        """
        tid = rthread.get_ident()
        if tid == self.rlock_owner:
            try:
                self.rlock_count = ovfcheck(self.rlock_count + 1)
            except OverflowError:
                raise oefmt(space.w_OverflowError,
                            "internal lock count overflowed")
            return space.w_True

        rc = self.lock.acquire(blocking != 0)
        if rc:
            self.rlock_owner = tid
            self.rlock_count = 1
        return space.newbool(rc)

    def release_w(self, space):
        """Release a lock, decrementing the recursion level.

        If after the decrement it is zero, reset the lock to unlocked (not owned
        by any thread), and if any other threads are blocked waiting for the
        lock to become unlocked, allow exactly one of them to proceed. If after
        the decrement the recursion level is still nonzero, the lock remains
        locked and owned by the calling thread.

        Only call this method when the calling thread owns the lock. A
        RuntimeError is raised if this method is called when the lock is
        unlocked.

        There is no return value.

        """
        if self.rlock_owner != rthread.get_ident():
            raise oefmt(space.w_RuntimeError,
                        "cannot release un-acquired lock")
        self.rlock_count -= 1
        if self.rlock_count == 0:
            self.rlock_owner = 0
            try_release(space, self.lock)

    def is_owned_w(self, space):
        """For internal use by `threading.Condition`."""
        return space.newbool(self.rlock_owner == rthread.get_ident())

    def acquire_restore_w(self, space, w_count_owner):
        """For internal use by `threading.Condition`."""
        # saved_state is the value returned by release_save()
        w_count, w_owner = space.unpackiterable(w_count_owner, 2)
        count = space.int_w(w_count)
        owner = space.int_w(w_owner)
        self.lock.acquire(True)
        self.rlock_count = count
        self.rlock_owner = owner

    def release_save_w(self, space):
        """For internal use by `threading.Condition`."""
        if self.rlock_count == 0:
            raise oefmt(space.w_RuntimeError,
                        "cannot release un-acquired lock")
        count, self.rlock_count = self.rlock_count, 0
        owner, self.rlock_owner = self.rlock_owner, 0
        try_release(space, self.lock)
        return space.newtuple([space.newint(count), space.newint(owner)])

    def descr__enter__(self, space):
        self.acquire_w(space)
        return self

    def descr__exit__(self, space, __args__):
        self.release_w(space)

    def descr__note(self, space, __args__):
        pass   # compatibility with the _Verbose base class in Python

W_RLock.typedef = TypeDef(
    "thread.RLock",
    __new__ = interp2app(W_RLock.descr__new__.im_func),
    acquire = interp2app(W_RLock.acquire_w),
    release = interp2app(W_RLock.release_w),
    _is_owned = interp2app(W_RLock.is_owned_w),
    _acquire_restore = interp2app(W_RLock.acquire_restore_w),
    _release_save = interp2app(W_RLock.release_save_w),
    __enter__ = interp2app(W_RLock.descr__enter__),
    __exit__ = interp2app(W_RLock.descr__exit__),
    __weakref__ = make_weakref_descr(W_RLock),
    __repr__ = interp2app(W_RLock.descr__repr__),
    _note = interp2app(W_RLock.descr__note),
    )

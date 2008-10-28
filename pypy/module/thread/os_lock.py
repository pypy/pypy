"""
Python locks, based on true threading locks provided by the OS.
"""

from pypy.module.thread import ll_thread as thread
from pypy.module.thread.error import wrap_thread_error
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import ObjSpace, interp2app, Arguments
from pypy.interpreter.typedef import TypeDef

# Force the declaration of the type 'thread.LockType' for RPython
#import pypy.module.thread.rpython.exttable


##import sys
##def debug(msg, n):
##    return
##    tb = []
##    try:
##        for i in range(1, 8):
##            tb.append(sys._getframe(i).f_code.co_name)
##    except:
##        pass
##    tb = ' '.join(tb)
##    msg = '| %6d | %d %s | %s\n' % (thread.get_ident(), n, msg, tb)
##    sys.stderr.write(msg)


class Lock(Wrappable):
    "A wrappable box around an interp-level lock object."

    def __init__(self, space):
        try:
            self.lock = thread.allocate_lock()
        except thread.error:
            raise wrap_thread_error(space, "out of resources")

    def descr_lock_acquire(self, space, waitflag=1):
        """Lock the lock.  Without argument, this blocks if the lock is already
locked (even by the same thread), waiting for another thread to release
the lock, and return None once the lock is acquired.
With an argument, this will only block if the argument is true,
and the return value reflects whether the lock is acquired.
The blocking operation is not interruptible."""
        mylock = self.lock
        result = mylock.acquire(bool(waitflag))
        return space.newbool(result)

    def descr_lock_release(self, space):
        """Release the lock, allowing another thread that is blocked waiting for
the lock to acquire the lock.  The lock must be in the locked state,
but it needn't be locked by the same thread that unlocks it."""
        try:
            self.lock.release()
        except thread.error:
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

descr_acquire = interp2app(Lock.descr_lock_acquire,
                           unwrap_spec=['self', ObjSpace, int])
descr_release = interp2app(Lock.descr_lock_release,
                           unwrap_spec=['self', ObjSpace])
descr_locked  = interp2app(Lock.descr_lock_locked,
                           unwrap_spec=['self', ObjSpace])
descr__enter__ = interp2app(Lock.descr__enter__,
                            unwrap_spec=['self', ObjSpace])
descr__exit__ = interp2app(Lock.descr__exit__,
                            unwrap_spec=['self', ObjSpace, Arguments])


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

def getlocktype(space):
    return space.gettypeobject(Lock.typedef)

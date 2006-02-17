"""
Thread support based on OS-level threads.
"""

import thread
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import NoneNotWrapped
from pypy.interpreter.gateway import ObjSpace, W_Root, Arguments

# Force the declaration of thread.start_new_thread() & co. for RPython
import pypy.module.thread.rpython.exttable


THREAD_STARTUP_LOCK = thread.allocate_lock()


class Bootstrapper:
    def bootstrap(self):
        space = self.space
        THREAD_STARTUP_LOCK.release()
        space.threadlocals.enter_thread(space)
        try:
            self.run()
        finally:
            # release ownership of these objects before we release the GIL
            self.args       = None
            self.w_callable = None
            # at this point the thread should only have a reference to
            # an empty 'self'.  We hold the last reference to 'self'; indeed,
            # the parent thread already forgot about it because the above
            # enter_thread() must have blocked until long after the call to
            # start_new_thread() below returned.
            # (be careful of resetting *all* local variables to None here!)

            # clean up space.threadlocals to remove the ExecutionContext
            # entry corresponding to the current thread
            space.threadlocals.leave_thread(space)

    def run(self):
        space      = self.space
        w_callable = self.w_callable
        args       = self.args
        try:
            space.call_args(w_callable, args)
        except OperationError, e:
            if not e.match(space, space.w_SystemExit):
                ident = thread.get_ident()
                where = 'thread %d started by ' % ident
                e.write_unraisable(space, where, w_callable)
            e.clear(space)


def start_new_thread(space, w_callable, w_args, w_kwargs=NoneNotWrapped):
    """Start a new thread and return its identifier.  The thread will call the
function with positional arguments from the tuple args and keyword arguments
taken from the optional dictionary kwargs.  The thread exits when the
function returns; the return value is ignored.  The thread will also exit
when the function raises an unhandled exception; a stack trace will be
printed unless the exception is SystemExit."""
    if not space.is_true(space.isinstance(w_args, space.w_tuple)): 
        raise OperationError(space.w_TypeError, 
                space.wrap("2nd arg must be a tuple")) 
    if w_kwargs is not None and not space.is_true(space.isinstance(w_kwargs, space.w_dict)): 
        raise OperationError(space.w_TypeError, 
                space.wrap("optional 3rd arg must be a dictionary")) 
    if not space.is_true(space.callable(w_callable)):
        raise OperationError(space.w_TypeError, 
                space.wrap("first arg must be callable"))

    args = Arguments.frompacked(space, w_args, w_kwargs)
    boot = Bootstrapper()
    boot.space      = space
    boot.w_callable = w_callable
    boot.args       = args

    THREAD_STARTUP_LOCK.acquire(True)

    ident = thread.start_new_thread(Bootstrapper.bootstrap, (boot,))

    # wait until the thread has really started and acquired a reference to
    # 'boot'.
    THREAD_STARTUP_LOCK.acquire(True)
    THREAD_STARTUP_LOCK.release()

    return space.wrap(ident)


def get_ident(space):
    """Return a non-zero integer that uniquely identifies the current thread
amongst other threads that exist simultaneously.
This may be used to identify per-thread resources.
Even though on some platforms threads identities may appear to be
allocated consecutive numbers starting at 1, this behavior should not
be relied upon, and the number should be seen purely as a magic cookie.
A thread's identity may be reused for another thread after it exits."""
    ident = thread.get_ident()
    return space.wrap(ident)

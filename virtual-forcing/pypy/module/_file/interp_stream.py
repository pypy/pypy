import py
from pypy.rlib import streamio
from pypy.rlib.streamio import StreamErrors

from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app

import os

def wrap_streamerror(space, e):
    if isinstance(e, streamio.StreamError):
        return OperationError(space.w_ValueError,
                              space.wrap(e.message))
    elif isinstance(e, OSError):
        return wrap_oserror_as_ioerror(space, e)
    else:
        return OperationError(space.w_IOError, space.w_None)

def wrap_oserror_as_ioerror(space, e):
    assert isinstance(e, OSError)
    errno = e.errno
    try:
        msg = os.strerror(errno)
    except ValueError:
        msg = 'error %d' % errno
    w_error = space.call_function(space.w_IOError,
                                  space.wrap(errno),
                                  space.wrap(msg))
    return OperationError(space.w_IOError, w_error)


class W_AbstractStream(Wrappable):
    """Base class for interp-level objects that expose streams to app-level"""
    slock = None
    slockowner = None
    # Locking issues:
    # * Multiple threads can access the same W_AbstractStream in
    #   parallel, because many of the streamio calls eventually
    #   release the GIL in some external function call.
    # * Parallel accesses have bad (and crashing) effects on the
    #   internal state of the buffering levels of the stream in
    #   particular.
    # * We can't easily have a lock on each W_AbstractStream because we
    #   can't translate prebuilt lock objects.
    # We are still protected by the GIL, so the easiest is to create
    # the lock on-demand.

    def __init__(self, space, stream):
        self.space = space
        self.stream = stream

    def _try_acquire_lock(self):
        # this function runs with the GIL acquired so there is no race
        # condition in the creation of the lock
        if self.slock is None:
            self.slock = self.space.allocate_lock()
        me = self.space.getexecutioncontext()   # used as thread ident
        if self.slockowner is me:
            return False    # already acquired by the current thread
        self.slock.acquire(True)
        assert self.slockowner is None
        self.slockowner = me
        return True

    def _release_lock(self):
        self.slockowner = None
        self.slock.release()

    def lock(self):
        if not self._try_acquire_lock():
            raise OperationError(self.space.w_RuntimeError,
                                 self.space.wrap("stream lock already held"))

    def unlock(self):
        me = self.space.getexecutioncontext()   # used as thread ident
        if self.slockowner is not me:
            raise OperationError(self.space.w_RuntimeError,
                                 self.space.wrap("stream lock is not held"))
        self._release_lock()

    def _freeze_(self):
        # remove the lock object, which will be created again as needed at
        # run-time.
        self.slock = None
        assert self.slockowner is None
        return False

    def stream_read(self, n):
        """
        An interface for direct interp-level usage of W_AbstractStream,
        e.g. from interp_marshal.py.
        NOTE: this assumes that the stream lock is already acquired.
        Like os.read(), this can return less than n bytes.
        """
        try:
            return self.stream.read(n)
        except StreamErrors, e:
            raise wrap_streamerror(self.space, e)

    def do_write(self, data):
        """
        An interface for direct interp-level usage of W_Stream,
        e.g. from interp_marshal.py.
        NOTE: this assumes that the stream lock is already acquired.
        """
        try:
            self.stream.write(data)
        except StreamErrors, e:
            raise wrap_streamerror(self.space, e)

# ____________________________________________________________

class W_Stream(W_AbstractStream):
    """A class that exposes the raw stream interface to app-level."""
    # this exists for historical reasons, and kept around in case we want
    # to re-expose the raw stream interface to app-level.

for name, argtypes in streamio.STREAM_METHODS.iteritems():
    numargs = len(argtypes)
    args = ", ".join(["v%s" % i for i in range(numargs)])
    exec py.code.Source("""
    def %(name)s(self, space, %(args)s):
        acquired = self.try_acquire_lock()
        try:
            try:
                result = self.stream.%(name)s(%(args)s)
            except streamio.StreamError, e:
                raise OperationError(space.w_ValueError,
                                     space.wrap(e.message))
            except OSError, e:
                raise wrap_oserror_as_ioerror(space, e)
        finally:
            if acquired:
                self.release_lock()
        return space.wrap(result)
    %(name)s.unwrap_spec = [W_Stream, ObjSpace] + argtypes
    """ % locals()).compile() in globals()

W_Stream.typedef = TypeDef("Stream",
    lock   = interp2app(W_Stream.lock),
    unlock = interp2app(W_Stream.unlock),
    **dict([(name, interp2app(globals()[name]))
                for name, _ in streamio.STREAM_METHODS.iteritems()]))

import py
from pypy.rlib import streamio
from errno import EINTR

from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace, W_Root, NoneNotWrapped, applevel
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.miscutils import Action

import os


def wrap_oserror_as_ioerror(space, e):
    assert isinstance(e, OSError)
    errno = e.errno
    if errno == EINTR:
        # A signal was sent to the process and interupted
        # a systemcall. We want to trigger running of
        # any installed interrupt handlers.
        # XXX: is there a better way?
        ec = space.getexecutioncontext()
        Action.perform_actions(space.pending_actions)
        Action.perform_actions(ec.pending_actions)
    try:
        msg = os.strerror(errno)
    except ValueError:
        msg = 'error %d' % errno
    w_error = space.call_function(space.w_IOError,
                                  space.wrap(errno),
                                  space.wrap(msg))
    return OperationError(space.w_IOError, w_error)


class W_Stream(Wrappable):
    slock = None
    slockowner = None
    # Locking issues:
    # * Multiple threads can access the same W_Stream in
    #   parallel, because many of the streamio calls eventually
    #   release the GIL in some external function call.
    # * Parallel accesses have bad (and crashing) effects on the
    #   internal state of the buffering levels of the stream in
    #   particular.
    # * We can't easily have a lock on each W_Stream because we
    #   can't translate prebuilt lock objects.
    # We are still protected by the GIL, so the easiest is to create
    # the lock on-demand.

    def __init__(self, space, stream):
        self.space = space
        self.stream = stream

    def try_acquire_lock(self):
        # this function runs with the GIL acquired so there is no race
        # condition in the creation of the lock
        if self.slock is None:
            self.slock = self.space.allocate_lock()
        me = self.space.getexecutioncontext()   # used as thread ident
        if self.slockowner is me:
            return False    # already acquired by the current thread
        self.slock.acquire(True)
        self.slockowner = me
        return True

    def release_lock(self):
        self.slockowner = None
        self.slock.release()

    def descr_lock(self):
        if not self.try_acquire_lock():
            raise OperationError(self.space.w_RuntimeError,
                                 self.space.wrap("stream lock already held"))

    def descr_unlock(self):
        me = self.space.getexecutioncontext()   # used as thread ident
        if self.slockowner is not me:
            raise OperationError(self.space.w_RuntimeError,
                                 self.space.wrap("stream lock is not held"))
        self.release_lock()

    def _freeze_(self):
        # remove the lock object, which will be created again as need at
        # run-time.
        self.slock = None
        assert self.slockowner is None
        return False

    def do_read(self, n):
        """
        An interface for direct interp-level usage of W_Stream,
        e.g. from interp_marshal.py.
        NOTE: this assumes that the stream lock is already acquired.
        Like os.read(), this can return less than n bytes.
        """
        try:
            return self.stream.read(n)
        except streamio.StreamError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap(e.message))
        except OSError, e:
            raise wrap_oserror_as_ioerror(space, e)

    def do_write(self, data):
        """
        An interface for direct interp-level usage of W_Stream,
        e.g. from interp_marshal.py.
        NOTE: this assumes that the stream lock is already acquired.
        """
        try:
            self.stream.write(data)
        except streamio.StreamError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap(e.message))
        except OSError, e:
            raise wrap_oserror_as_ioerror(space, e)


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
    lock   = interp2app(W_Stream.descr_lock),
    unlock = interp2app(W_Stream.descr_unlock),
    **dict([(name, interp2app(globals()[name]))
                for name, _ in streamio.STREAM_METHODS.iteritems()]))


def is_mode_ok(space, mode):
    if not mode or mode[0] not in ['r', 'w', 'a', 'U']:
        raise OperationError(
                space.w_IOError,
                space.wrap('invalid mode : %s' % mode))

def open_file_as_stream(space, path, mode="r", buffering=-1):
    is_mode_ok(space, mode)
    try:
        return space.wrap(W_Stream(
            space, streamio.open_file_as_stream(path, mode, buffering)))
    except OSError, e:
        raise wrap_oserror_as_ioerror(space, e)
open_file_as_stream.unwrap_spec = [ObjSpace, str, str, int]

def fdopen_as_stream(space, fd, mode="r", buffering=-1):
    is_mode_ok(space, mode)
    return space.wrap(W_Stream(
            space, streamio.fdopen_as_stream(fd, mode, buffering)))
fdopen_as_stream.unwrap_spec = [ObjSpace, int, str, int]


def file2stream(space, w_f):
    """A hack for direct interp-level access to W_Stream objects,
    for better performance e.g. when marshalling directly from/to a
    real file object.  This peels off the app-level layers of the file class
    defined in app_file.py.  It complains if the file is already closed.
    """
    w_stream = space.findattr(w_f, space.wrap('stream'))
    if w_stream is None:
        return None
    w_stream = space.interpclass_w(w_stream)
    if not isinstance(w_stream, W_Stream):
        return None
    if space.is_true(space.getattr(w_f, space.wrap('_closed'))):
        raise OperationError(space.w_ValueError,
                             space.wrap('I/O operation on closed file'))
    return w_stream

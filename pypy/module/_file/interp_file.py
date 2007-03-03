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
    def __init__(self, space, stream):
        self.stream = stream

for name, argtypes in streamio.STREAM_METHODS.iteritems():
    numargs = len(argtypes)
    args = ", ".join(["v%s" % i for i in range(numargs)])
    exec py.code.Source("""
    def %(name)s(self, space, %(args)s):
        try:
            return space.wrap(self.stream.%(name)s(%(args)s))
        except streamio.StreamError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap(e.message))
        except OSError, e:
            raise wrap_oserror_as_ioerror(space, e)
    %(name)s.unwrap_spec = [W_Stream, ObjSpace] + argtypes
    """ % locals()).compile() in globals()

W_Stream.typedef = TypeDef("Stream",
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


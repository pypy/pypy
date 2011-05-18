import math
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import (
    OperationError, operationerrfmt, wrap_oserror)
from pypy.rlib import rpoll
import errno

defaultevents = rpoll.POLLIN | rpoll.POLLOUT | rpoll.POLLPRI

class Cache:
    def __init__(self, space):
        self.w_error = space.new_exception_class("select.error")

def poll(space):
    """Returns a polling object, which supports registering and
unregistering file descriptors, and then polling them for I/O events."""
    return Poll()

class Poll(Wrappable):
    def __init__(self):
        self.fddict = {}

    @unwrap_spec(events=int)
    def register(self, space, w_fd, events=defaultevents):
        fd = space.c_filedescriptor_w(w_fd)
        self.fddict[fd] = events

    @unwrap_spec(events=int)
    def modify(self, space, w_fd, events):
        fd = space.c_filedescriptor_w(w_fd)
        if fd not in self.fddict:
            raise wrap_oserror(space, OSError(errno.ENOENT, "poll.modify"),
                               exception_name='w_IOError')
        self.fddict[fd] = events

    def unregister(self, space, w_fd):
        fd = space.c_filedescriptor_w(w_fd)
        try:
            del self.fddict[fd]
        except KeyError:
            raise OperationError(space.w_KeyError,
                                 space.wrap(fd)) # XXX should this maybe be w_fd?

    def poll(self, space, w_timeout=None):
        if space.is_w(w_timeout, space.w_None):
            timeout = -1
        else:
            # we want to be compatible with cpython and also accept things
            # that can be casted to integer (I think)
            try:
                # compute the integer
                timeout = space.int_w(space.int(w_timeout))
            except (OverflowError, ValueError):
                raise OperationError(space.w_ValueError,
                                     space.wrap("math range error"))

        try:
            retval = rpoll.poll(self.fddict, timeout)
        except rpoll.PollError, e:
            w_errortype = space.fromcache(Cache).w_error
            message = e.get_msg()
            raise OperationError(w_errortype,
                                 space.newtuple([space.wrap(e.errno),
                                                 space.wrap(message)]))

        retval_w = []
        for fd, revents in retval:
            retval_w.append(space.newtuple([space.wrap(fd),
                                            space.wrap(revents)]))
        return space.newlist(retval_w)

pollmethods = {}
for methodname in 'register modify unregister poll'.split():
    pollmethods[methodname] = interp2app(getattr(Poll, methodname))
Poll.typedef = TypeDef('select.poll', **pollmethods)

def select(space, w_iwtd, w_owtd, w_ewtd, w_timeout=None):
    """Wait until one or more file descriptors are ready for some kind of I/O.
The first three arguments are sequences of file descriptors to be waited for:
rlist -- wait until ready for reading
wlist -- wait until ready for writing
xlist -- wait for an ``exceptional condition''
If only one kind of condition is required, pass [] for the other lists.
A file descriptor is either a socket or file object, or a small integer
gotten from a fileno() method call on one of those.

The optional 4th argument specifies a timeout in seconds; it may be
a floating point number to specify fractions of seconds.  If it is absent
or None, the call will never time out.

The return value is a tuple of three lists corresponding to the first three
arguments; each contains the subset of the corresponding file descriptors
that are ready.

*** IMPORTANT NOTICE ***
On Windows, only sockets are supported; on Unix, all file descriptors.
"""

    iwtd_w = space.listview(w_iwtd)
    owtd_w = space.listview(w_owtd)
    ewtd_w = space.listview(w_ewtd)
    iwtd = [space.c_filedescriptor_w(w_f) for w_f in iwtd_w]
    owtd = [space.c_filedescriptor_w(w_f) for w_f in owtd_w]
    ewtd = [space.c_filedescriptor_w(w_f) for w_f in ewtd_w]
    iwtd_d = {}
    owtd_d = {}
    ewtd_d = {}
    for i in range(len(iwtd)):
        iwtd_d[iwtd[i]] = iwtd_w[i]
    for i in range(len(owtd)):
        owtd_d[owtd[i]] = owtd_w[i]
    for i in range(len(ewtd)):
        ewtd_d[ewtd[i]] = ewtd_w[i]
    try:
        if space.is_w(w_timeout, space.w_None):
            iwtd, owtd, ewtd = rpoll.select(iwtd, owtd, ewtd)
        else:
            iwtd, owtd, ewtd = rpoll.select(iwtd, owtd, ewtd, space.float_w(w_timeout))
    except rpoll.SelectError, s:
        w_errortype = space.fromcache(Cache).w_error
        raise OperationError(w_errortype, space.newtuple([
            space.wrap(s.errno), space.wrap(s.get_msg())]))
    
    return space.newtuple([
        space.newlist([iwtd_d[i] for i in iwtd]),
        space.newlist([owtd_d[i] for i in owtd]),
        space.newlist([ewtd_d[i] for i in ewtd])])

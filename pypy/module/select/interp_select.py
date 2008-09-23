import math
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import W_Root, ObjSpace, interp2app
from pypy.interpreter.error import OperationError
from pypy.rlib import rpoll

defaultevents = rpoll.POLLIN | rpoll.POLLOUT | rpoll.POLLPRI

def poll(space):
    """Returns a polling object, which supports registering and
unregistering file descriptors, and then polling them for I/O events."""
    return Poll()

def as_fd_w(space, w_fd):
    if not space.is_true(space.isinstance(w_fd, space.w_int)):
        try:
            w_fileno = space.getattr(w_fd, space.wrap('fileno'))
        except OperationError, e:
            if e.match(space, space.w_AttributeError):
                raise OperationError(space.w_TypeError,
                                     space.wrap("argument must be an int, or have a fileno() method."))
            raise
        w_fd = space.call_function(w_fileno)
        if not space.is_true(space.isinstance(w_fd, space.w_int)):
            raise OperationError(space.w_TypeError,
                                 space.wrap('filneo() return a non-integer'))
        
    fd = space.int_w(w_fd)
    if fd < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("file descriptor cannot be a negative integer (%d)"%fd))
    return fd

class Poll(Wrappable):
    def __init__(self):
        self.fddict = {}

    def register(self, space, w_fd, events=defaultevents):
        fd = as_fd_w(space, w_fd)
        self.fddict[fd] = events
    register.unwrap_spec = ['self', ObjSpace, W_Root, int]

    def unregister(self, space, w_fd):
        fd = as_fd_w(space, w_fd)
        try:
            del self.fddict[fd]
        except KeyError:
            raise OperationError(space.w_KeyError,
                                 space.wrap(fd))
    unregister.unwrap_spec = ['self', ObjSpace, W_Root]

    def poll(self, space, w_timeout=None):
        if space.is_w(w_timeout, space.w_None):
            timeout = -1
        else:
            timeout = space.float_w(w_timeout)
            # round non-integral floats upwards (in theory, with timeout=2.5
            # we should wait at least 2.5ms, so 2ms is not enough)
            try:
                timeout = int(math.ceil(timeout))
            except (OverflowError, ValueError):
                raise OperationError(space.w_ValueError,
                                     space.wrap("math range error"))

        try:
            retval = rpoll.poll(self.fddict, timeout)
        except rpoll.PollError, e:
            w_module = space.getbuiltinmodule('select')
            w_errortype = space.getattr(w_module, space.wrap('error'))
            message = e.get_msg()
            raise OperationError(w_errortype,
                                 space.newtuple([space.wrap(e.errno),
                                                 space.wrap(message)]))

        retval_w = []
        for fd, revents in retval:
            retval_w.append(space.newtuple([space.wrap(fd),
                                            space.wrap(revents)]))
        return space.newlist(retval_w)
    poll.unwrap_spec = ['self', ObjSpace, W_Root]

pollmethods = {}
for methodname in 'register unregister poll'.split():
    method = getattr(Poll, methodname)
    assert hasattr(method,'unwrap_spec'), methodname
    assert method.im_func.func_code.co_argcount == len(method.unwrap_spec), methodname
    pollmethods[methodname] = interp2app(method, unwrap_spec=method.unwrap_spec)
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

    iwtd_w = space.unpackiterable(w_iwtd)
    owtd_w = space.unpackiterable(w_owtd)
    ewtd_w = space.unpackiterable(w_ewtd)
    iwtd = [as_fd_w(space, w_f) for w_f in iwtd_w]
    owtd = [as_fd_w(space, w_f) for w_f in owtd_w]
    ewtd = [as_fd_w(space, w_f) for w_f in ewtd_w]
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
        w_module = space.getbuiltinmodule('select')
        w_errortype = space.getattr(w_module, space.wrap('error'))
        raise OperationError(w_errortype, space.newtuple([
            space.wrap(s.errno), space.wrap(s.get_msg())]))
    
    return space.newtuple([
        space.newlist([iwtd_d[i] for i in iwtd]),
        space.newlist([owtd_d[i] for i in owtd]),
        space.newlist([ewtd_d[i] for i in ewtd])])

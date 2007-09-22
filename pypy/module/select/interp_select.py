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
            timeout = space.int_w(w_timeout)

        try:
            retval = rpoll.poll(self.fddict, timeout)
        except rpoll.PollError, e:
            w_module = space.getbuiltinmodule('select')
            w_errortype = space.getattr(w_module, space.wrap('error'))
            message = e.get_msg()
            raise OperationError(w_errortype,
                                 space.newtuple([space.wrap(errno),
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

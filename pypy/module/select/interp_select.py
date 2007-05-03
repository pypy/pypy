from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import W_Root, ObjSpace, interp2app
from pypy.rlib import _rsocket_ctypes as _c
from ctypes import POINTER, byref
from pypy.rpython.rctypes.aerrno import geterrno
from pypy.interpreter.error import OperationError

defaultevents = _c.POLLIN | _c.POLLOUT | _c.POLLPRI

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

    if hasattr(_c, 'poll'):
        def poll(self, space, w_timeout=None):
            if space.is_w(w_timeout, space.w_None):
                timeout = -1
            else:
                timeout = space.int_w(w_timeout)

            numfd = len(self.fddict)
            buf = _c.create_string_buffer(_c.sizeof(_c.pollfd) * numfd)
            pollfds = _c.cast(buf, POINTER(_c.pollfd))
            i = 0
            for fd, events in self.fddict.iteritems():
                pollfds[i].fd = fd
                pollfds[i].events = events
                i += 1

            # XXX Temporary hack for releasing the GIL
            GIL = space.threadlocals.getGIL()
            if GIL is not None: GIL.release()
            ret = _c.poll(pollfds, numfd, timeout)
            if GIL is not None: GIL.acquire(True)

            if ret < 0:
                errno = geterrno()
                w_module = space.getbuiltinmodule('select')
                w_errortype = space.getattr(w_module, space.wrap('error'))
                message = _c.strerror(errno)
                raise OperationError(w_errortype,
                                     space.newtuple([space.wrap(errno),
                                                     space.wrap(message)]))

            retval_w = []
            for i in range(numfd):
                pollfd = pollfds[i]
                if pollfd.revents:
                    retval_w.append(space.newtuple([space.wrap(pollfd.fd),
                                                    space.wrap(pollfd.revents)]))
            return space.newlist(retval_w)

    elif hasattr(_c, 'WSAEventSelect'):
        # win32 implementation
        def poll(self, space, w_timeout=None):
            numfd = len(self.fddict)

            socketevents = _c.ARRAY(_c.WSAEVENT, numfd)()

            numevents = 0
            eventdict = {}

            for fd, events in self.fddict.iteritems():
                # select desired events
                wsaEvents = 0
                if events & _c.POLLIN:
                    wsaEvents |= _c.FD_READ | _c.FD_ACCEPT | _c.FD_CLOSE
                if events & _c.POLLOUT:
                    wsaEvents |= _c.FD_WRITE | _c.FD_CONNECT | _c.FD_CLOSE

                # if no events then ignore socket
                if wsaEvents == 0:
                    continue

 		# select socket for desired events
                event = _c.WSACreateEvent()
                _c.WSAEventSelect(fd, event, wsaEvents)

                eventdict[fd] = event
 		socketevents[numevents] = event
                numevents += 1

            # if no sockets then return immediately
            if numevents == 0:
                return space.newlist([])

            # prepare timeout
            if space.is_w(w_timeout, space.w_None):
                timeout = -1
            else:
                timeout = space.int_w(w_timeout)
            if timeout < 0:
                timeout = _c.INFINITE

            # XXX Temporary hack for releasing the GIL
            GIL = space.threadlocals.getGIL()
            if GIL is not None: GIL.release()
            ret = _c.WSAWaitForMultipleEvents(numevents, socketevents,
                                              False, timeout, False)
            if GIL is not None: GIL.acquire(True)

            if ret == _c.WSA_WAIT_TIMEOUT:
                return space.newlist([])

            if ret < 0: # WSA_WAIT_FAILED is unsigned...
                from pypy.rlib._rsocket_ctypes import socket_strerror, geterrno
                errno = geterrno()
                w_module = space.getbuiltinmodule('select')
                w_errortype = space.getattr(w_module, space.wrap('error'))
                message = socket_strerror(errno)
                raise OperationError(w_errortype,
                                     space.newtuple([space.wrap(errno),
                                                     space.wrap(message)]))

            retval_w = []
            info = _c.WSANETWORKEVENTS()
            for fd, event in eventdict.iteritems():
                if _c.WSAEnumNetworkEvents(fd, event, byref(info)) < 0:
                    continue
                revents = 0
                if info.lNetworkEvents & _c.FD_READ:
                    revents |= _c.POLLIN
                if info.lNetworkEvents & _c.FD_ACCEPT:
                    revents |= _c.POLLIN
                if info.lNetworkEvents & _c.FD_WRITE:
                    revents |= _c.POLLOUT
                if info.lNetworkEvents & _c.FD_CONNECT:
                    if info.iErrorCode[_c.FD_CONNECT_BIT]:
                        revents |= _c.POLLERR
                    else:
                        revents |= _c.POLLOUT
                if info.lNetworkEvents & _c.FD_CLOSE:
                    if info.iErrorCode[_c.FD_CLOSE_BIT]:
                        revents |= _c.POLLERR
                    else:
                        if self.fddict[fd] & _c.POLLIN:
                            revents |= _c.POLLIN
                        if self.fddict[fd] & _c.POLLOUT:
                            revents |= _c.POLLOUT
                if revents:
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

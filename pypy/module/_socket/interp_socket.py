from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, make_weakref_descr
from pypy.interpreter.gateway import ObjSpace, W_Root, NoneNotWrapped
from pypy.interpreter.gateway import interp2app
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.rsocket import RSocket, AF_INET, SOCK_STREAM
from pypy.rlib.rsocket import SocketError, SocketErrorWithErrno
from pypy.interpreter.error import OperationError
from pypy.interpreter import gateway

class W_RSocket(Wrappable, RSocket):
    def __del__(self):
        self.clear_all_weakrefs()
        self.close()

    def accept_w(self, space):
        """accept() -> (socket object, address info)

        Wait for an incoming connection.  Return a new socket representing the
        connection, and the address of the client.  For IP sockets, the address
        info is a pair (hostaddr, port).
        """
        try:
            sock, addr = self.accept(W_RSocket)
            return space.newtuple([space.wrap(sock),
                                   addr.as_object(space)])
        except SocketError, e:
            raise converted_error(space, e)
    accept_w.unwrap_spec = ['self', ObjSpace]

    def bind_w(self, space, w_addr):
        """bind(address)
        
        Bind the socket to a local address.  For IP sockets, the address is a
        pair (host, port); the host must refer to the local host. For raw packet
        sockets the address is a tuple (ifname, proto [,pkttype [,hatype]])
        """
        try:
            self.bind(self.addr_from_object(space, w_addr))
        except SocketError, e:
            raise converted_error(space, e)
    bind_w.unwrap_spec = ['self', ObjSpace, W_Root]

    def close_w(self, space):
        """close()

        Close the socket.  It cannot be used after this call.
        """
        try:
            self.close()
        except SocketError, e:
            raise converted_error(space, e)
    close_w.unwrap_spec = ['self', ObjSpace]

    def connect_w(self, space, w_addr):
        """connect(address)

        Connect the socket to a remote address.  For IP sockets, the address
        is a pair (host, port).
        """
        try:
            self.connect(self.addr_from_object(space, w_addr))
        except SocketError, e:
            raise converted_error(space, e)
        except TypeError, e:
            raise OperationError(space.w_TypeError,
                                 space.wrap(str(e)))
    connect_w.unwrap_spec = ['self', ObjSpace, W_Root]

    def connect_ex_w(self, space, w_addr):
        """connect_ex(address) -> errno
        
        This is like connect(address), but returns an error code (the errno value)
        instead of raising an exception when an error occurs.
        """
        error = self.connect_ex(self.addr_from_object(space, w_addr))
        return space.wrap(error)
    connect_ex_w.unwrap_spec = ['self', ObjSpace, W_Root]

    def dup_w(self, space):
        try:
            return self.dup(W_RSocket)
        except SocketError, e:
            raise converted_error(space, e)
    dup_w.unwrap_spec = ['self', ObjSpace]
    
    def fileno_w(self, space):
        """fileno() -> integer

        Return the integer file descriptor of the socket.
        """
        try:
            fd = self.fileno()
        except SocketError, e:
            raise converted_error(space, e)
        return space.wrap(intmask(fd))
    fileno_w.unwrap_spec = ['self', ObjSpace]

    def getpeername_w(self, space):
        """getpeername() -> address info

        Return the address of the remote endpoint.  For IP sockets, the address
        info is a pair (hostaddr, port).
        """
        try:
            addr = self.getpeername()
            return addr.as_object(space)
        except SocketError, e:
            raise converted_error(space, e)
    getpeername_w.unwrap_spec = ['self', ObjSpace]

    def getsockname_w(self, space):
        """getsockname() -> address info

        Return the address of the local endpoint.  For IP sockets, the address
        info is a pair (hostaddr, port).
        """
        try:
            addr = self.getsockname()
            return addr.as_object(space)
        except SocketError, e:
            raise converted_error(space, e)
    getsockname_w.unwrap_spec = ['self', ObjSpace]

    def getsockopt_w(self, space, level, optname, w_buflen=NoneNotWrapped):
        """getsockopt(level, option[, buffersize]) -> value

        Get a socket option.  See the Unix manual for level and option.
        If a nonzero buffersize argument is given, the return value is a
        string of that length; otherwise it is an integer.
        """
        if w_buflen is None:
            try:
                return space.wrap(self.getsockopt_int(level, optname))
            except SocketError, e:
                raise converted_error(space, e)
        buflen = space.int_w(w_buflen)
        return space.wrap(self.getsockopt(level, optname, buflen))
    getsockopt_w.unwrap_spec = ['self', ObjSpace, int, int, W_Root]

    def gettimeout_w(self, space):
        """gettimeout() -> timeout

        Returns the timeout in floating seconds associated with socket
        operations. A timeout of None indicates that timeouts on socket
        """
        timeout = self.gettimeout()
        if timeout < 0.0:
            return space.w_None
        return space.wrap(timeout)
    gettimeout_w.unwrap_spec = ['self', ObjSpace]
    
    def listen_w(self, space, backlog):
        """listen(backlog)

        Enable a server to accept connections.  The backlog argument must be at
        least 1; it specifies the number of unaccepted connection that the system
        will allow before refusing new connections.
        """
        try:
            self.listen(backlog)
        except SocketError, e:
            raise converted_error(space, e)
    listen_w.unwrap_spec = ['self', ObjSpace, int]

    def makefile_w(self, space, w_mode="r", w_buffsize=-1):
        """makefile([mode[, buffersize]]) -> file object

        Return a regular file object corresponding to the socket.
        The mode and buffersize arguments are as for the built-in open() function.
        """
        return app_makefile(space, self, w_mode, w_buffsize)
    makefile_w.unwrap_spec = ['self', ObjSpace, W_Root, W_Root]
        
        
                   
    def recv_w(self, space, buffersize, flags=0):
        """recv(buffersize[, flags]) -> data

        Receive up to buffersize bytes from the socket.  For the optional flags
        argument, see the Unix manual.  When no data is available, block until
        at least one byte is available or until the remote end is closed.  When
        the remote end is closed and all data is read, return the empty string.
        """
        try:
            data = self.recv(buffersize, flags)
        except SocketError, e:
            raise converted_error(space, e)
        return space.wrap(data)
    recv_w.unwrap_spec = ['self', ObjSpace, int, int]

    def recvfrom_w(self, space, buffersize, flags=0):
        """recvfrom(buffersize[, flags]) -> (data, address info)

        Like recv(buffersize, flags) but also return the sender's address info.
        """
        try:
            data, addr = self.recvfrom(buffersize, flags)
            if addr:
                w_addr = addr.as_object(space)
            else:
                w_addr = space.w_None
            return space.newtuple([space.wrap(data), w_addr])
        except SocketError, e:
            raise converted_error(space, e)
    recvfrom_w.unwrap_spec = ['self', ObjSpace, int, int]

    def send_w(self, space, data, flags=0):
        """send(data[, flags]) -> count

        Send a data string to the socket.  For the optional flags
        argument, see the Unix manual.  Return the number of bytes
        sent; this may be less than len(data) if the network is busy.
        """
        try:
            count = self.send(data, flags)
        except SocketError, e:
            raise converted_error(space, e)
        return space.wrap(count)
    send_w.unwrap_spec = ['self', ObjSpace, 'bufferstr', int]

    def sendall_w(self, space, data, flags=0):
        """sendall(data[, flags])

        Send a data string to the socket.  For the optional flags
        argument, see the Unix manual.  This calls send() repeatedly
        until all data is sent.  If an error occurs, it's impossible
        to tell how much data has been sent.
        """
        try:
            count = self.sendall(data, flags)
        except SocketError, e:
            raise converted_error(space, e)
    sendall_w.unwrap_spec = ['self', ObjSpace, 'bufferstr', int]

    def sendto_w(self, space, data, w_param2, w_param3=NoneNotWrapped):
        """sendto(data[, flags], address) -> count

        Like send(data, flags) but allows specifying the destination address.
        For IP sockets, the address is a pair (hostaddr, port).
        """
        if w_param3 is None:
            # 2 args version
            flags = 0
            w_addr = w_param2
        else:
            # 3 args version
            flags = space.int_w(w_param2)
            w_addr = w_param3
        try:
            addr = self.addr_from_object(space, w_addr)
            count = self.sendto(data, flags, addr)
        except SocketError, e:
            raise converted_error(space, e)
        return space.wrap(count)
    sendto_w.unwrap_spec = ['self', ObjSpace, 'bufferstr', W_Root, W_Root]

    def setblocking_w(self, space, flag):
        """setblocking(flag)

        Set the socket to blocking (flag is true) or non-blocking (false).
        setblocking(True) is equivalent to settimeout(None);
        setblocking(False) is equivalent to settimeout(0.0).
        """
        self.setblocking(bool(flag))
    setblocking_w.unwrap_spec = ['self', ObjSpace, int]

    def setsockopt_w(self, space, level, optname, w_optval):
        """setsockopt(level, option, value)

        Set a socket option.  See the Unix manual for level and option.
        The value argument can either be an integer or a string.
        """
        try:
            optval = space.int_w(w_optval)
        except:
            optval = space.str_w(w_optval)
            try:
                self.setsockopt(level, optname, optval)
            except SocketError, e:
                raise converted_error(space, e)
            return
        try:
            self.setsockopt_int(level, optname, optval)
        except SocketError, e:
            raise converted_error(space, e)
            
    setsockopt_w.unwrap_spec = ['self', ObjSpace, int, int, W_Root]
    
    def settimeout_w(self, space, w_timeout):
        """settimeout(timeout)

        Set a timeout on socket operations.  'timeout' can be a float,
        giving in seconds, or None.  Setting a timeout of None disables
        the timeout feature and is equivalent to setblocking(1).
        Setting a timeout of zero is the same as setblocking(0).
        """
        if space.is_w(w_timeout, space.w_None):
            timeout = -1.0
        else:
            timeout = space.float_w(w_timeout)
            if timeout < 0.0:
                raise OperationError(space.w_ValueError,
                                     space.wrap('Timeout value out of range'))
        self.settimeout(timeout)
    settimeout_w.unwrap_spec = ['self', ObjSpace, W_Root]
    
    def shutdown_w(self, space, how):
        """shutdown(flag)

        Shut down the reading side of the socket (flag == SHUT_RD), the
        writing side of the socket (flag == SHUT_WR), or both ends
        (flag == SHUT_RDWR).
        """
        try:
            self.shutdown(how)
        except SocketError, e:
            raise converted_error(space, e)
    shutdown_w.unwrap_spec = ['self', ObjSpace, int]

    #------------------------------------------------------------
    # Support functions for socket._socketobject
    usecount = 1
    def _reuse_w(self):
        """_resue()

        Increase the usecount of the socketobject.
        Intended only to be used by socket._socketobject
        """
        self.usecount += 1
    _reuse_w.unwrap_spec = ['self']

    def _drop_w(self, space):
        """_drop()

        Decrease the usecount of the socketobject. If the
        usecount reaches 0 close the socket.
        Intended only to be used by socket._socketobject
        """
        self.usecount -= 1
        if self.usecount > 0:
            return
        self.close_w(space)
    _drop_w.unwrap_spec = ['self', ObjSpace]

app_makefile = gateway.applevel(r'''
def makefile(self, mode="r", buffersize=-1):
    """makefile([mode[, buffersize]]) -> file object

    Return a regular file object corresponding to the socket.
    The mode and buffersize arguments are as for the built-in open() function.
    """
    import os
    newfd = os.dup(self.fileno())
    return os.fdopen(newfd, mode, buffersize)
''', filename =__file__).interphook('makefile')

def newsocket(space, w_subtype, family=AF_INET,
              type=SOCK_STREAM, proto=0):
    # XXX If we want to support subclassing the socket type we will need
    # something along these lines. But allocate_instance is only defined
    # on the standard object space, so this is not really correct.
    #sock = space.allocate_instance(W_RSocket, w_subtype)
    #Socket.__init__(sock, space, fd, family, type, proto)
    try:
        sock = W_RSocket(family, type, proto)
    except SocketError, e:
        raise converted_error(space, e)
    return space.wrap(sock)
descr_socket_new = interp2app(newsocket,
                               unwrap_spec=[ObjSpace, W_Root, int, int, int])

# ____________________________________________________________
# Error handling

def converted_error(space, e):
    message = e.get_msg()
    w_module = space.getbuiltinmodule('_socket')
    w_exception_class = space.getattr(w_module, space.wrap(e.applevelerrcls))
    if isinstance(e, SocketErrorWithErrno):
        w_exception = space.call_function(w_exception_class, space.wrap(e.errno),
                                      space.wrap(message))
    else:
        w_exception = space.call_function(w_exception_class, space.wrap(message))
    return OperationError(w_exception_class, w_exception)

# ____________________________________________________________

socketmethodnames = """
accept bind close connect connect_ex dup fileno
getpeername getsockname getsockopt gettimeout listen makefile
recv recvfrom send sendall sendto setblocking
setsockopt settimeout shutdown _reuse _drop
""".split()
# Remove non-implemented methods
for name in ('dup',):
    if not hasattr(RSocket, name):
        socketmethodnames.remove(name)

socketmethods = {}
for methodname in socketmethodnames:
    method = getattr(W_RSocket, methodname + '_w')
    assert hasattr(method,'unwrap_spec'), methodname
    assert method.im_func.func_code.co_argcount == len(method.unwrap_spec), methodname
    socketmethods[methodname] = interp2app(method, unwrap_spec=method.unwrap_spec)

W_RSocket.typedef = TypeDef("_socket.socket",
    __doc__ = """\
socket([family[, type[, proto]]]) -> socket object

Open a socket of the given type.  The family argument specifies the
address family; it defaults to AF_INET.  The type argument specifies
whether this is a stream (SOCK_STREAM, this is the default)
or datagram (SOCK_DGRAM) socket.  The protocol argument defaults to 0,
specifying the default protocol.  Keyword arguments are accepted.

A socket object represents one endpoint of a network connection.

Methods of socket objects (keyword arguments not allowed):

accept() -- accept a connection, returning new socket and client address
bind(addr) -- bind the socket to a local address
close() -- close the socket
connect(addr) -- connect the socket to a remote address
connect_ex(addr) -- connect, return an error code instead of an exception
dup() -- return a new socket object identical to the current one [*]
fileno() -- return underlying file descriptor
getpeername() -- return remote address [*]
getsockname() -- return local address
getsockopt(level, optname[, buflen]) -- get socket options
gettimeout() -- return timeout or None
listen(n) -- start listening for incoming connections
makefile([mode, [bufsize]]) -- return a file object for the socket [*]
recv(buflen[, flags]) -- receive data
recvfrom(buflen[, flags]) -- receive data and sender's address
sendall(data[, flags]) -- send all data
send(data[, flags]) -- send data, may not send all of it
sendto(data[, flags], addr) -- send data to a given address
setblocking(0 | 1) -- set or clear the blocking I/O flag
setsockopt(level, optname, value) -- set socket options
settimeout(None | float) -- set or clear the timeout
shutdown(how) -- shut down traffic in one or both directions

 [*] not available on all platforms!""",
    __new__ = descr_socket_new,
    __weakref__ = make_weakref_descr(W_RSocket),
    ** socketmethods
    )

from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, make_weakref_descr,\
     interp_attrproperty
from pypy.interpreter.gateway import NoneNotWrapped, interp2app, unwrap_spec
from pypy.rlib.rarithmetic import intmask
from pypy.rlib import rsocket
from pypy.rlib.rsocket import RSocket, AF_INET, SOCK_STREAM
from pypy.rlib.rsocket import SocketError, SocketErrorWithErrno
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter import gateway

class SignalChecker:
    def __init__(self, space):
        self.space = space

    def check(self):
        self.space.getexecutioncontext().checksignals()

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
                                   addr.as_object(sock.fd, space)])
        except SocketError, e:
            raise converted_error(space, e)

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

    def close_w(self, space):
        """close()

        Close the socket.  It cannot be used after this call.
        """
        try:
            self.close()
        except SocketError, e:
            raise converted_error(space, e)

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

    def connect_ex_w(self, space, w_addr):
        """connect_ex(address) -> errno
        
        This is like connect(address), but returns an error code (the errno value)
        instead of raising an exception when an error occurs.
        """
        try:
            addr = self.addr_from_object(space, w_addr)
        except SocketError, e:
            raise converted_error(space, e)
        error = self.connect_ex(addr)
        return space.wrap(error)

    def dup_w(self, space):
        try:
            return self.dup(W_RSocket)
        except SocketError, e:
            raise converted_error(space, e)
    
    def fileno_w(self, space):
        """fileno() -> integer

        Return the integer file descriptor of the socket.
        """
        return space.wrap(intmask(self.fd))

    def getpeername_w(self, space):
        """getpeername() -> address info

        Return the address of the remote endpoint.  For IP sockets, the address
        info is a pair (hostaddr, port).
        """
        try:
            addr = self.getpeername()
            return addr.as_object(self.fd, space)
        except SocketError, e:
            raise converted_error(space, e)

    def getsockname_w(self, space):
        """getsockname() -> address info

        Return the address of the local endpoint.  For IP sockets, the address
        info is a pair (hostaddr, port).
        """
        try:
            addr = self.getsockname()
            return addr.as_object(self.fd, space)
        except SocketError, e:
            raise converted_error(space, e)

    @unwrap_spec(level=int, optname=int)
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

    def gettimeout_w(self, space):
        """gettimeout() -> timeout

        Returns the timeout in floating seconds associated with socket
        operations. A timeout of None indicates that timeouts on socket
        """
        timeout = self.gettimeout()
        if timeout < 0.0:
            return space.w_None
        return space.wrap(timeout)

    @unwrap_spec(backlog=int)
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

    def makefile_w(self, space, w_mode="r", w_buffsize=-1):
        """makefile([mode[, buffersize]]) -> file object

        Return a regular file object corresponding to the socket.
        The mode and buffersize arguments are as for the built-in open() function.
        """
        return app_makefile(space, self, w_mode, w_buffsize)

    @unwrap_spec(buffersize='nonnegint', flags=int)
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

    @unwrap_spec(buffersize='nonnegint', flags=int)
    def recvfrom_w(self, space, buffersize, flags=0):
        """recvfrom(buffersize[, flags]) -> (data, address info)

        Like recv(buffersize, flags) but also return the sender's address info.
        """
        try:
            data, addr = self.recvfrom(buffersize, flags)
            if addr:
                w_addr = addr.as_object(self.fd, space)
            else:
                w_addr = space.w_None
            return space.newtuple([space.wrap(data), w_addr])
        except SocketError, e:
            raise converted_error(space, e)

    @unwrap_spec(data='bufferstr', flags=int)
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

    @unwrap_spec(data='bufferstr', flags=int)
    def sendall_w(self, space, data, flags=0):
        """sendall(data[, flags])

        Send a data string to the socket.  For the optional flags
        argument, see the Unix manual.  This calls send() repeatedly
        until all data is sent.  If an error occurs, it's impossible
        to tell how much data has been sent.
        """
        try:
            count = self.sendall(data, flags, SignalChecker(space))
        except SocketError, e:
            raise converted_error(space, e)

    @unwrap_spec(data='bufferstr')
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

    @unwrap_spec(flag=bool)
    def setblocking_w(self, flag):
        """setblocking(flag)

        Set the socket to blocking (flag is true) or non-blocking (false).
        setblocking(True) is equivalent to settimeout(None);
        setblocking(False) is equivalent to settimeout(0.0).
        """
        self.setblocking(flag)

    @unwrap_spec(level=int, optname=int)
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

    @unwrap_spec(nbytes=int, flags=int)
    def recv_into_w(self, space, w_buffer, nbytes=0, flags=0):
        rwbuffer = space.rwbuffer_w(w_buffer)
        lgt = rwbuffer.getlength()
        if nbytes == 0 or nbytes > lgt:
            nbytes = lgt
        try:
            return space.wrap(self.recvinto(rwbuffer, nbytes, flags))
        except SocketError, e:
            raise converted_error(space, e)

    @unwrap_spec(nbytes=int, flags=int)
    def recvfrom_into_w(self, space, w_buffer, nbytes=0, flags=0):
        rwbuffer = space.rwbuffer_w(w_buffer)
        lgt = rwbuffer.getlength()
        if nbytes == 0 or nbytes > lgt:
            nbytes = lgt
        try:
            readlgt, addr = self.recvfrom_into(rwbuffer, nbytes, flags)
            if addr:
                w_addr = addr.as_object(self.fd, space)
            else:
                w_addr = space.w_None
            return space.newtuple([space.wrap(readlgt), w_addr])
        except SocketError, e:
            raise converted_error(space, e)        

    @unwrap_spec(cmd=int)
    def ioctl_w(self, space, cmd, w_option):
        from pypy.rpython.lltypesystem import rffi, lltype
        from pypy.rlib import rwin32
        from pypy.rlib.rsocket import _c

        recv_ptr = lltype.malloc(rwin32.LPDWORD.TO, 1, flavor='raw')
        try:
            if cmd == _c.SIO_RCVALL:
                value_size = rffi.sizeof(rffi.INTP)
            elif cmd == _c.SIO_KEEPALIVE_VALS:
                value_size = rffi.sizeof(_c.tcp_keepalive)
            else:
                raise operationerrfmt(space.w_ValueError,
                                      "invalid ioctl command %d", cmd)

            value_ptr = lltype.malloc(rffi.VOIDP.TO, value_size, flavor='raw')
            try:
                if cmd == _c.SIO_RCVALL:
                    option_ptr = rffi.cast(rffi.INTP, value_ptr)
                    option_ptr[0] = space.int_w(w_option)
                elif cmd == _c.SIO_KEEPALIVE_VALS:
                    w_onoff, w_time, w_interval = space.unpackiterable(w_option)
                    option_ptr = rffi.cast(lltype.Ptr(_c.tcp_keepalive), value_ptr)
                    option_ptr.c_onoff = space.uint_w(w_onoff)
                    option_ptr.c_keepalivetime = space.uint_w(w_time)
                    option_ptr.c_keepaliveinterval = space.uint_w(w_interval)

                res = _c.WSAIoctl(
                    self.fd, cmd, value_ptr, value_size,
                    rffi.NULL, 0, recv_ptr, rffi.NULL, rffi.NULL)
                if res < 0:
                    raise converted_error(space, rsocket.last_error())
            finally:
                if value_ptr:
                    lltype.free(value_ptr, flavor='raw')

            return space.wrap(recv_ptr[0])
        finally:
            lltype.free(recv_ptr, flavor='raw')

    @unwrap_spec(how=int)
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

    #------------------------------------------------------------
    # Support functions for socket._socketobject
    usecount = 1
    def _reuse_w(self):
        """_resue()

        Increase the usecount of the socketobject.
        Intended only to be used by socket._socketobject
        """
        self.usecount += 1

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

@unwrap_spec(family=int, type=int, proto=int)
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
descr_socket_new = interp2app(newsocket)

# ____________________________________________________________
# Error handling

class SocketAPI:
    def __init__(self, space):
        self.w_error = space.new_exception_class(
            "_socket.error", space.w_IOError)
        self.w_herror = space.new_exception_class(
            "_socket.herror", self.w_error)
        self.w_gaierror = space.new_exception_class(
            "_socket.gaierror", self.w_error)
        self.w_timeout = space.new_exception_class(
            "_socket.timeout", self.w_error)

        self.errors_w = {'error': self.w_error,
                         'herror': self.w_herror,
                         'gaierror': self.w_gaierror,
                         'timeout': self.w_timeout,
                         }

    def get_exception(self, applevelerrcls):
        return self.errors_w[applevelerrcls]

def get_error(space, name):
    return space.fromcache(SocketAPI).get_exception(name)

def converted_error(space, e):
    message = e.get_msg()
    w_exception_class = get_error(space, e.applevelerrcls)
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
setsockopt settimeout shutdown _reuse _drop recv_into recvfrom_into
""".split()
# Remove non-implemented methods
for name in ('dup',):
    if not hasattr(RSocket, name):
        socketmethodnames.remove(name)
if hasattr(rsocket._c, 'WSAIoctl'):
    socketmethodnames.append('ioctl')

socketmethods = {}
for methodname in socketmethodnames:
    method = getattr(W_RSocket, methodname + '_w')
    socketmethods[methodname] = interp2app(method)

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
    type = interp_attrproperty('type', W_RSocket),
    proto = interp_attrproperty('proto', W_RSocket),
    family = interp_attrproperty('family', W_RSocket),
    ** socketmethods
    )

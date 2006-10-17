from pypy.interpreter.gateway import ObjSpace, W_Root, NoneNotWrapped
from pypy.module.rsocket.interp_socket import converted_error, W_RSocket
from pypy.module.rsocket import rsocket
from pypy.module.rsocket.rsocket import _c


def gethostname(space):
    """gethostname() -> string

    Return the current host name.
    """
    try:
        res = rsocket.gethostname()
    except SocketError, e:
        raise converted_error(space, e)
    return space.wrap(namebuff.value)
gethostname.unwrap_spec = [ObjSpace]

def gethostbyname(space, name):
    """gethostbyname(host) -> address

    Return the IP address (a string of the form '255.255.255.255') for a host.
    """
    try:
        addr = rsocket.gethostbyname(name)
        hostname = addr.get_host()
    except SocketError, e:
        raise converted_error(space, e)
    return space.wrap(hostname)
gethostbyname.unwrap_spec = [ObjSpace, str]

##def gethostbyname_ex(space, name):
##    """gethostbyname_ex(host) -> (name, aliaslist, addresslist)

##    Return the true host name, a list of aliases, and a list of IP addresses,
##    for a host.  The host argument is a string giving a host name or IP number.
##    """
##gethostbyname_ex.unwrap_spec = [ObjSpace, str]
    
##def gethostbyaddr(space, name):
##    """gethostbyaddr(host) -> (name, aliaslist, addresslist)

##    Return the true host name, a list of aliases, and a list of IP addresses,
##    for a host.  The host argument is a string giving a host name or IP number.
##    """
##gethostbyaddr.unwrap_spec = [ObjSpace, str]

##def getservbyname(space, name, w_proto=NoneNotWrapped):
##    """getservbyname(servicename[, protocolname]) -> integer

##    Return a port number from a service name and protocol name.
##    The optional protocol name, if given, should be 'tcp' or 'udp',
##    otherwise any protocol will match.
##    """
##getservbyname.unwrap_spec = [ObjSpace, str, W_Root]

##def getservbyport(space, port, w_proto=NoneNotWrapped):
##    """getservbyport(port[, protocolname]) -> string

##    Return the service name from a port number and protocol name.
##    The optional protocol name, if given, should be 'tcp' or 'udp',
##    otherwise any protocol will match.
##    """
##getservbyport.unwrap_spec = [ObjSpace, int, W_Root]

##def getprotobyname(space, name):
##    """getprotobyname(name) -> integer

##    Return the protocol number for the named protocol.  (Rarely used.)
##    """
##getprotobyname.unwrap_spec = [ObjSpace, str]

def fromfd(space, fd, family, type, proto=0):
    """fromfd(fd, family, type[, proto]) -> socket object

    Create a socket object from the given file descriptor.
    The remaining arguments are the same as for socket().
    """
    try:
        sock = rsocket.fromfd(fd, family, type, proto, W_RSocket)
    except SocketError, e:
        raise converted_error(space, e)
    return space.wrap(sock)
fromfd.unwrap_spec = [ObjSpace, int, int, int, int]

def socketpair(space, family = rsocket.socketpair_default_family,
                      type   = _c.SOCK_STREAM,
                      proto  = 0):
    """socketpair([family[, type[, proto]]]) -> (socket object, socket object)

    Create a pair of socket objects from the sockets returned by the platform
    socketpair() function.
    The arguments are the same as for socket() except the default family is
    AF_UNIX if defined on the platform; otherwise, the default is AF_INET.
    """
    try:
        sock1, sock2 = rsocket.socketpair(family, type, proto)
    except SocketError, e:
        raise converted_error(space, e)
    return space.newtuple([space.wrap(sock1), space.wrap(sock2)])
socketpair.unwrap_spec = [ObjSpace, int, int, int]

def ntohs(space, x):
    """ntohs(integer) -> integer

    Convert a 16-bit integer from network to host byte order.
    """
    return space.wrap(_c.ntohs(x))
ntohs.unwrap_spec = [ObjSpace, int]

def ntohl(space, w_x):
    """ntohl(integer) -> integer

    Convert a 32-bit integer from network to host byte order.
    """
    if space.is_true(space.isinstance(w_x, space.w_int)):
        x = space.int_w(w_x)
    elif space.is_true(space.isinstance(w_x, space.w_long)):
        x = space.uint_w(w_x)
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("expected int/long, %s found" %
                                        (space.type(w_x).getname(space, "?"))))

    return space.wrap(_c.ntohl(x))
ntohl.unwrap_spec = [ObjSpace, W_Root]

def htons(space, x):
    """htons(integer) -> integer

    Convert a 16-bit integer from host to network byte order.
    """
    return space.wrap(_c.htons(x))
htons.unwrap_spec = [ObjSpace, int]

def htonl(space, w_x):
    """htonl(integer) -> integer

    Convert a 32-bit integer from host to network byte order.
    """
    if space.is_true(space.isinstance(w_x, space.w_int)):
        x = space.int_w(w_x)
    elif space.is_true(space.isinstance(w_x, space.w_long)):
        x = space.uint_w(w_x)
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("expected int/long, %s found" %
                                        (space.type(w_x).getname(space, "?"))))

    return space.wrap(_c.htonl(x))
htonl.unwrap_spec = [ObjSpace, W_Root]

def inet_aton(space, ip):
    """inet_aton(string) -> packed 32-bit IP representation

    Convert an IP address in string format (123.45.67.89) to the 32-bit packed
    binary format used in low-level network functions.
    """
    try:
        buf = rsocket.inet_aton(ip)
    except SocketError, e:
        raise converted_error(space, e)
    return space.wrap(buf)
inet_aton.unwrap_spec = [ObjSpace, str]

def inet_ntoa(space, packed):
    """inet_ntoa(packed_ip) -> ip_address_string

    Convert an IP address from 32-bit packed binary format to string format
    """
    try:
        ip = rsocket.inet_ntoa(packed)
    except SocketError, e:
        raise converted_error(space, e)
    return space.wrap(ip)
inet_ntoa.unwrap_spec = [ObjSpace, str]

def inet_pton(space, family, ip):
    """inet_pton(family, ip) -> packed IP address string

    Convert an IP address from string format to a packed string suitable
    for use with low-level network functions.
    """
    try:
        buf = rsocket.inet_pton(family, ip)
    except SocketError, e:
        raise converted_error(space, e)
    return space.wrap(buf)
inet_pton.unwrap_spec = [ObjSpace, int, str]

def inet_ntop(space, family, packed):
    """inet_ntop(family, packed_ip) -> string formatted IP address

    Convert a packed IP address of the given family to string format.
    """
    try:
        ip = rsocket.inet_ntop(family, packed)
    except SocketError, e:
        raise converted_error(space, e)
    return space.wrap(ip)
inet_ntop.unwrap_spec = [ObjSpace, int, str]

MARKER MARKER

def getaddrinfo(space, w_host, w_port, family=0, socktype=0, proto=0, flags=0):
    """getaddrinfo(host, port [, family, socktype, proto, flags])
        -> list of (family, socktype, proto, canonname, sockaddr)

    Resolve host and port into addrinfo struct.
    """
    # host can be None, string or unicode
    if space.is_w(w_host, space.w_None):
        host = None
    elif space.is_true(space.isinstance(w_host, space.w_str)):
        host = space.str_w(w_host)
    elif space.is_true(space.isinstance(w_host, space.w_unicode)):
        w_shost = space.call_method(w_host, "encode", space.wrap("idna"))
        host = space.str_w(w_shost)
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap(
            "getaddrinfo() argument 1 must be string or None"))

    # port can be None, int or string
    if space.is_w(w_port, space.w_None):
        port = None
    elif space.is_true(space.isinstance(w_port, space.w_int)):
        port = str(space.int_w(w_port))
    elif space.is_true(space.isinstance(w_port, space.w_str)):
        port = space.str_w(w_port)
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("Int or String expected"))

    res = _c.addrinfo_ptr()
    hints = _c.addrinfo()
    hints.ai_flags = flags
    hints.ai_family = family
    hints.ai_socktype = socktype
    hints.ai_protocol = proto
    retval = _c.getaddrinfo(host, port, _c.pointer(hints), _c.pointer(res))
    if retval != 0:
        raise w_get_socketgaierror(space, None, retval)

    result = []
    next = None
    if res:
        info = res.contents
        next = info.ai_next
        try:
            w_family = space.wrap(info.ai_family)
            w_socktype = space.wrap(info.ai_socktype)
            w_proto = space.wrap(info.ai_protocol)
            if info.ai_canonname:
                w_canonname = space.wrap(info.ai_canonname)
            else:
                w_canonname = space.wrap('')
            w_addr = w_makesockaddr(space,
            _c.cast(info.ai_addr, _c.sockaddr_ptr),
                    info.ai_addrlen, info.ai_protocol)
            result.append(space.newtuple([w_family, w_socktype, w_proto,
                                w_canonname, w_addr]))
        except:
            _c.freeaddrinfo(res)
            raise
    while next:
        info = next.contents
        next = info.ai_next
        try:
            w_family = space.wrap(info.ai_family)
            w_socktype = space.wrap(info.ai_socktype)
            w_proto = space.wrap(info.ai_protocol)
            if info.ai_canonname:
                w_canonname = space.wrap(info.ai_canonname)
            else:
                w_canonname = space.wrap('')
            w_addr = w_makesockaddr(space,
            _c.cast(info.ai_addr, _c.sockaddr_ptr),
                    info.ai_addrlen, info.ai_protocol)
            result.append(space.newtuple([w_family, w_socktype, w_proto,
                                w_canonname, w_addr]))
        except:
            _c.freeaddrinfo(res)
            raise
    result = space.newlist(result)
    _c.freeaddrinfo(res)
    return result
getaddrinfo.unwrap_spec = [ObjSpace, W_Root, W_Root, int, int, int, int]

def getnameinfo(space, w_sockaddr, flags):
    """getnameinfo(sockaddr, flags) --> (host, port)

    Get host and port for a sockaddr."""
    w_flowinfo = w_scope_id = space.wrap(0)
    sockaddr_len = space.int_w(space.len(w_sockaddr))
    if sockaddr_len == 2:
        w_host, w_port = space.unpackiterable(w_sockaddr, 2)
    elif sockaddr_len == 3:
        w_host, w_port, w_flowinfo = space.unpackiterable(w_sockaddr, 3)
    elif sockaddr_len == 4:
        w_host, w_port, w_flowinfo, w_scope_id = space.unpackiterable(w_sockaddr, 4)
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap('argument 1 should be 2-4 items (%d given)' % sockaddr_len))
    host = space.str_w(w_host)
    port = space.int_w(w_port)
    flowinfo = space.int_w(w_flowinfo)
    scope_id = space.int_w(w_scope_id)

    res = _c.addrinfo_ptr()
    hints = _c.addrinfo()
    hints.ai_family = _c.AF_UNSPEC
    hints.ai_socktype = _c.SOCK_DGRAM
    retval = _c.getaddrinfo(host, str(port), ctypes.pointer(hints), ctypes.pointer(res))
    if retval != 0:
        raise w_get_socketgaierror(space, None, retval)
    family = res.contents.ai_family
    if family == _c.AF_INET:
        if sockaddr_len != 2:
            if res:
                _c.freeaddrinfo(res)
            raise OperationError(space.w_TypeError,
                                 space.wrap('argument 1 should be 2 items (%d given)' % sockaddr_len))
            
    elif family == _c.AF_INET6:
        sin6_ptr = ctypes.cast(res.contents.ai_addr, ctypes.POINTER(_c.sockaddr_in6))
        sin6_ptr.contents.sin6_flowinfo = flowinfo
        sin6_ptr.contents.sin6_scope_id = scope_id

    hostbuf = ctypes.create_string_buffer(_c.NI_MAXHOST)
    portbuf = ctypes.create_string_buffer(_c.NI_MAXSERV)
    maxhost = _c.size_t(_c.NI_MAXHOST)
    error = _c.getnameinfo(res.contents.ai_addr, res.contents.ai_addrlen,
                        hostbuf, maxhost,
                        portbuf, _c.size_t(_c.NI_MAXSERV), flags)

    if res:
        _c.freeaddrinfo(res)
    if error:
        raise w_get_socketgaierror(space, None, error)
    return space.newtuple([space.wrap(hostbuf.value),
                           space.wrap(portbuf.value)])
getnameinfo.unwrap_spec = [ObjSpace, W_Root, int]

# _____________________________________________________________
#
# Timeout management

class State:
    def __init__(self, space):
        self.space = space

        self.defaulttimeout = -1 # Default timeout for new sockets

def getstate(space):
    return space.fromcache(State)

def setdefaulttimeout(space, w_timeout):
    if space.is_w(w_timeout, space.w_None):
        timeout = -1.0
    else:
        timeout = space.float_w(w_timeout)
        if timeout < 0.0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("Timeout value out of range"))

    getstate(space).defaulttimeout = timeout
setdefaulttimeout.unwrap_spec = [ObjSpace, W_Root]

def getdefaulttimeout(space):
    timeout = getstate(space).defaulttimeout

    if timeout < 0.0:
        return space.wrap(None)
    else:
        return space.wrap(timeout)
getdefaulttimeout.unwrap_spec = [ObjSpace]

# _____________________________________________________________
#
# The socket type

def newsocket(space, w_subtype, family=_c.AF_INET,
              type=_c.SOCK_STREAM, proto=0):
    fd = _c.socket(family, type, proto)
    if fd < 0:
        raise w_get_socketerror(space, None, _c.geterrno())
    # XXX If we want to support subclassing the socket type we will need
    # something along these lines. But allocate_instance is only defined
    # on the standard object space, so this is not really correct.
    #sock = space.allocate_instance(Socket, w_subtype)
    #Socket.__init__(sock, space, fd, family, type, proto)
    #return space.wrap(sock)
    return space.wrap(Socket(space, fd, family, type, proto))
descr_socket_new = interp2app(newsocket,
                               unwrap_spec=[ObjSpace, W_Root, int, int, int])

def setblocking(fd, block):
    delay_flag = _c.fcntl(fd, _c.F_GETFL, 0)
    if block:
        delay_flag &= ~_c.O_NONBLOCK
    else:
        delay_flag |= _c.O_NONBLOCK
    _c.fcntl(fd, _c.F_SETFL, delay_flag)
    
class Socket(Wrappable):
    "A wrappable box around an interp-level socket object."

    def __init__(self, space, fd, family, type, proto=0):
        self.fd = fd
        self.family = family
        self.type = type
        self.proto = proto
        self.closed = False
        self.timeout = getstate(space).defaulttimeout
        if self.timeout >= 0.0:
            setblocking(self.fd, False)

    def _getsockaddr(self, space, w_addr):
        """Returns a pointer to a sockaddr"""
        if self.family == _c.AF_INET:
            try:
                w_host, w_port = space.unpackiterable(w_addr, 2)
            except UnpackValueError:
                e_msg = space.wrap("getsockaddrarg: AF_INET address must be a tuple of two elements")
                raise OperationError(space.w_TypeError, e_msg)
             
            port = space.int_w(w_port)
            host = space.str_w(w_host)
            res = _c.addrinfo_ptr()
            hints = _c.addrinfo()
            hints.ai_family = self.family
            hints.ai_socktype = self.type
            hints.ai_protocol = self.proto
            retval = _c.getaddrinfo(host, str(port), ctypes.pointer(hints), ctypes.pointer(res))
            if retval != 0:
                raise w_get_socketgaierror(space, None, retval)
            addrinfo = res.contents
            addrlen = addrinfo.ai_addrlen
            caddr_buf = ctypes.create_string_buffer(intmask(addrlen)) # XXX forcing a long to an int
            _c.memcpy(caddr_buf, addrinfo.ai_addr, addrlen)
            
            sockaddr_ptr = ctypes.cast(caddr_buf, _c.sockaddr_ptr)
            return sockaddr_ptr, addrlen

        else:
            raise NotImplementedError('Unsupported address family') # XXX

    def accept(self, space):
        """accept() -> (socket object, address info)

        Wait for an incoming connection.  Return a new socket representing the
        connection, and the address of the client.  For IP sockets, the address
        info is a pair (hostaddr, port).
        """
        peeraddr = _c.pointer(_c.sockaddr())
        peeraddrlen = _c.socklen_t(_c.sockaddr_size)

        # XXX Temporary hack for releasing the GIL
        GIL = space.threadlocals.getGIL()
        if GIL is not None: GIL.release()
        newfd = _c.socketaccept(self.fd, peeraddr,
                                _c.pointer(peeraddrlen))
        if GIL is not None: GIL.acquire(True)
        
        if newfd < 0:
            raise w_get_socketerror(space, None, _c.geterrno())
        newsocket = Socket(space, newfd, self.family, self.type, self.proto)
        return space.newtuple([newsocket, w_makesockaddr(space, peeraddr, peeraddrlen.value, self.proto)])
    accept.unwrap_spec = ['self', ObjSpace]

    def bind(self, space, w_addr):
        """bind(address)
        
        Bind the socket to a local address.  For IP sockets, the address is a
        pair (host, port); the host must refer to the local host. For raw packet
        sockets the address is a tuple (ifname, proto [,pkttype [,hatype]])
        """
        caddr_ptr, caddr_len = self._getsockaddr(space, w_addr)
        res = _c.socketbind(self.fd, caddr_ptr, caddr_len)
        if res < 0:
            raise w_get_socketerror(space, None, _c.geterrno())
    bind.unwrap_spec = ['self', ObjSpace, W_Root]

    def __del__(self):
        if not self.closed:
            _c.close(self.fd)

    def close(self, space):
        """close()

        Close the socket.  It cannot be used after this call.
        """
        if not self.closed:
            res = _c.close(self.fd)
            if res < 0:
                errno = _c.geterrno()
                raise w_get_socketerror(space, None, errno)
            self.closed = True
    close.unwrap_spec = ['self', ObjSpace]

    def connect(self, space, w_addr):
        """connect(address)

        Connect the socket to a remote address.  For IP sockets, the address
        is a pair (host, port).
        """
        errno = self._connect_ex(space, w_addr)
        if errno:
            raise w_get_socketerror(space, None, errno)
    connect.unwrap_spec = ['self', ObjSpace, W_Root]

    def _connect_ex(self, space, w_addr):
        """connect_ex(address) -> errno
        
        This is like connect(address), but returns an error code (the errno value)
        instead of raising an exception when an error occurs.
        """
        sockaddr_ptr, sockaddr_len = self._getsockaddr(space, w_addr)

        # XXX Temporary hack for releasing the GIL
        GIL = space.threadlocals.getGIL()
        if GIL is not None: GIL.release()
        err = _c.socketconnect(self.fd, sockaddr_ptr, sockaddr_len)
        if GIL is not None: GIL.acquire(True)

        if err:
            errno = _c.geterrno()
            if self.timeout > 0.0:
                # XXX timeout doesn't really work at the moment
                pass
            return errno
        return 0
    
    def connect_ex(self, space, w_addr):
        return space.wrap(self._connect_ex(space, w_addr))
    connect_ex.unwrap_spec = ['self', ObjSpace, W_Root]

    def dup(self, space):
        """dup() -> socket object

        Return a new socket object connected to the same system resource.
        """
        newfd = _c.dup(self.fd)
        if newfd < 0:
            raise w_get_socketerror(space, None, _c.geterrno())
        return Socket(space, newfd, self.family, self.type, self.proto)

    dup.unwrap_spec = ['self', ObjSpace]

    def fileno(self, space):
        """fileno() -> integer

        Return the integer file descriptor of the socket.
        """
        if not self.closed:
            return space.wrap(self.fd)
        else:
            raise w_get_socketerror(space, "Bad file descriptor", errno.EBADF)
    fileno.unwrap_spec = ['self', ObjSpace]

    def getpeername(self, space):
        """getpeername() -> address info

        Return the address of the remote endpoint.  For IP sockets, the address
        info is a pair (hostaddr, port).
        """
    def getpeername(self, space):
        peeraddr = ctypes.pointer(_c.sockaddr())
        peeraddrlen = _c.socklen_t(_c.sockaddr_size)
        res = _c.socketgetpeername(self.fd, peeraddr,
                                   ctypes.pointer(peeraddrlen))
        if res < 0:
            raise w_get_socketerror(space, None, _c.geterrno())
        return w_makesockaddr(space, peeraddr, peeraddrlen.value, self.proto)
    getpeername.unwrap_spec = ['self', ObjSpace]

    def getsockname(self, space):
        """getsockname() -> address info

        Return the address of the local endpoint.  For IP sockets, the address
        info is a pair (hostaddr, port).
        """
        peeraddr = ctypes.pointer(_c.sockaddr())
        peeraddrlen = _c.socklen_t(_c.sockaddr_size)
        res = _c.socketgetsockname(self.fd, peeraddr,
                                   ctypes.pointer(peeraddrlen))
        if res < 0:
            raise w_get_socketerror(space, None, _c.geterrno())
        return w_makesockaddr(space, peeraddr, peeraddrlen.value, self.proto)
    getsockname.unwrap_spec = ['self', ObjSpace]

    def getsockopt(self, space, level, option, w_buffersize=NoneNotWrapped):
        """getsockopt(level, option[, buffersize]) -> value

        Get a socket option.  See the Unix manual for level and option.
        If a nonzero buffersize argument is given, the return value is a
        string of that length; otherwise it is an integer.
        """
        if w_buffersize is not None:
            buffersize = space.int_w(w_buffersize)
            c_buffersize = _c.socklen_t(buffersize)
            buffer = ctypes.create_string_buffer(buffersize)
            err = _c.socketgetsockopt(self.fd, level, option, buffer,
                                ctypes.pointer(c_buffersize))
            if err:
                raise w_get_socketerror(space, None, _c.geterrno())
            return space.wrap(buffer[:c_buffersize.value])
        # Assume integer option
        optval = _c.c_int()
        optlen = _c.socklen_t(_c.c_int_size)
        err = _c.socketgetsockopt(self.fd, level, option, _c.pointer(optval),
                                  ctypes.pointer(optlen))
        if err:
            raise w_get_socketerror(space, None, _c.geterrno())
        return space.wrap(optval.value)
    getsockopt.unwrap_spec = ['self', ObjSpace, int, int, W_Root]

    def listen(self, space, backlog):
        """listen(backlog)

        Enable a server to accept connections.  The backlog argument must be at
        least 1; it specifies the number of unaccepted connection that the system
        will allow before refusing new connections.
        """
        if backlog < 1:
            backlog = 1
        res = _c.socketlisten(self.fd, backlog)
        if res == -1:
            raise w_get_socketerror(space, None, _c.geterrno())
    listen.unwrap_spec = ['self', ObjSpace, int]

    def makefile(self, space, w_mode='r', w_buffsize=-1):
        return app_makefile(space, self, w_mode, w_buffsize)
    makefile.unwrap_spec = ['self', ObjSpace, W_Root, W_Root]

    def recv(self, space, buffersize, flags=0):
        """recv(buffersize[, flags]) -> data

        Receive up to buffersize bytes from the socket.  For the optional flags
        argument, see the Unix manual.  When no data is available, block until
        at least one byte is available or until the remote end is closed.  When
        the remote end is closed and all data is read, return the empty string.
        """
        buf = _c.create_string_buffer(buffersize)

        # XXX Temporary hack for releasing the GIL
        GIL = space.threadlocals.getGIL()
        if GIL is not None: GIL.release()
        read_bytes = _c.socketrecv(self.fd, buf, buffersize, flags)
        if GIL is not None: GIL.acquire(True)

        if read_bytes < 0:
            raise w_get_socketerror(space, None, _c.geterrno())
        return space.wrap(buf[:read_bytes])
        
    recv.unwrap_spec = ['self', ObjSpace, int, int]

    def recvfrom(self, space, buffersize, flags=0):
        """recvfrom(buffersize[, flags]) -> (data, address info)

        Like recv(buffersize, flags) but also return the sender's address info.
        """
        buf = _c.create_string_buffer(buffersize)
        sockaddr = _c.sockaddr()
        sockaddr_size = _c.socklen_t(_c.sockaddr_size)

        # XXX Temporary hack for releasing the GIL
        GIL = space.threadlocals.getGIL()
        if GIL is not None: GIL.release()
        read_bytes = _c.recvfrom(self.fd, buf, buffersize, flags,
                                 _c.pointer(sockaddr), _c.pointer(sockaddr_size))
        if GIL is not None: GIL.acquire(True)

        if read_bytes < 0:
            raise w_get_socketerror(space, None, _c.geterrno())
        w_addr = w_makesockaddr(space, _c.pointer(sockaddr), sockaddr_size.value, self.proto)
        return space.newtuple([space.wrap(buf[:read_bytes]), w_addr])
    recvfrom.unwrap_spec = ['self', ObjSpace, int, int]

    def send(self, space, data, flags=0):
        """send(data[, flags]) -> count

        Send a data string to the socket.  For the optional flags
        argument, see the Unix manual.  Return the number of bytes
        sent; this may be less than len(data) if the network is busy.
        """

        # XXX Temporary hack for releasing the GIL
        GIL = space.threadlocals.getGIL()
        if GIL is not None: GIL.release()
        res = _c.send(self.fd, data, len(data), flags)
        if GIL is not None: GIL.acquire(True)

        if res < 0:
            raise w_get_socketerror(space, None, _c.geterrno())
        return space.wrap(res)
    send.unwrap_spec = ['self', ObjSpace, str, int]

    def sendall(self, space, data, flags=0):
        """sendall(data[, flags])

        Send a data string to the socket.  For the optional flags
        argument, see the Unix manual.  This calls send() repeatedly
        until all data is sent.  If an error occurs, it's impossible
        to tell how much data has been sent.
        """
        while data:

            # XXX Temporary hack for releasing the GIL
            GIL = space.threadlocals.getGIL()
            if GIL is not None: GIL.release()
            res = _c.send(self.fd, data, len(data), flags)
            if GIL is not None: GIL.acquire(True)

            if res < 0:
                raise w_get_socketerror(space, None, _c.geterrno())
            data = data[res:]
    sendall.unwrap_spec = ['self', ObjSpace, str, int]

    def sendto(self, space, data, w_param2, w_param3=NoneNotWrapped):
        """sendto(data[, flags], address) -> count

        Like send(data, flags) but allows specifying the destination address.
        For IP sockets, the address is a pair (hostaddr, port).
        """
        if w_param3 is None:
            # 2 args version
            flags = 0
            addr, addr_len = self._getsockaddr(space, w_param2)
        else:
            # 3 args version
            flags = space.int_w(w_param2)
            addr, addr_len = self._getsockaddr(space, w_param3)

        # XXX Temporary hack for releasing the GIL
        GIL = space.threadlocals.getGIL()
        if GIL is not None: GIL.release()
        res = _c.sendto(self.fd, data, len(data), flags, addr, addr_len)
        if GIL is not None: GIL.acquire(True)

        if res < 0:
            raise w_get_socketerror(space, None, _c.geterrno())
        return space.wrap(res)
    sendto.unwrap_spec = ['self', ObjSpace, str, W_Root, W_Root]

    def setblocking(self, space, flag):
        """setblocking(flag)

        Set the socket to blocking (flag is true) or non-blocking (false).
        setblocking(True) is equivalent to settimeout(None);
        setblocking(False) is equivalent to settimeout(0.0).
        """
        setblocking(self.fd, bool(flag))
    setblocking.unwrap_spec = ['self', ObjSpace, int]

    def setsockopt(self, space, level, option, w_value):
        """setsockopt(level, option, value)

        Set a socket option.  See the Unix manual for level and option.
        The value argument can either be an integer or a string.
        """
        if space.is_true(space.isinstance(w_value, space.w_str)):
            strvalue = space.str_w(w_value)
            size = _c.socklen_t(len(strvalue))
            _c.socketsetsockopt(self.fd, level, option, strvalue,
                          size)
        else:
            intvalue = ctypes.c_int(space.int_w(w_value))
            size = _c.socklen_t(_c.c_int_size)
            _c.socketsetsockopt(self.fd, level, option, _c.pointer(intvalue),
                           size)
    setsockopt.unwrap_spec = ['self', ObjSpace, int, int, W_Root]

    def gettimeout(self, space):
        """gettimeout() -> timeout

        Returns the timeout in floating seconds associated with socket
        operations. A timeout of None indicates that timeouts on socket
        operations are disabled.
        """
        if self.timeout < 0.0:
            return space.w_None
        else:
            return space.wrap(self.timeout)
    gettimeout.unwrap_spec = ['self', ObjSpace]

    def settimeout(self, space, w_timeout):
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
                                     space.wrap("Timeout value out of range"))
        self.timeout = timeout
        setblocking(self.fd, timeout < 0.0)
    settimeout.unwrap_spec = ['self', ObjSpace, W_Root]

    def shutdown(self, space, how):
        """shutdown(flag)

        Shut down the reading side of the socket (flag == SHUT_RD), the
        writing side of the socket (flag == SHUT_WR), or both ends
        (flag == SHUT_RDWR).
        """
        err = _c.shutdown(self.fd, how)
        if err:
            raise w_get_socketerror(space, None, _c.geterrno())
        
    shutdown.unwrap_spec = ['self', ObjSpace, int]



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

socketmethodnames = """
accept bind close connect connect_ex dup fileno
getpeername getsockname getsockopt listen makefile recv
recvfrom send sendall sendto setblocking setsockopt gettimeout
settimeout shutdown
""".split()
socketmethods = {}
for methodname in socketmethodnames:
    method = getattr(Socket, methodname)
    assert hasattr(method,'unwrap_spec'), methodname
    assert method.im_func.func_code.co_argcount == len(method.unwrap_spec), methodname
    socketmethods[methodname] = interp2app(method, unwrap_spec=method.unwrap_spec)

Socket.typedef = TypeDef("_socket.socket",
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
    ** socketmethods
    )

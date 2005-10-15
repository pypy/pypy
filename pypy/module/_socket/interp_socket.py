
import socket, errno, sys
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import W_Root, NoneNotWrapped
from pypy.interpreter.gateway import ObjSpace, interp2app

if sys.platform == 'win32':
    WIN32_ERROR_MESSAGES = {
        errno.WSAEINTR:  "Interrupted system call",
        errno.WSAEBADF:  "Bad file descriptor",
        errno.WSAEACCES: "Permission denied",
        errno.WSAEFAULT: "Bad address",
        errno.WSAEINVAL: "Invalid argument",
        errno.WSAEMFILE: "Too many open files",
        errno.WSAEWOULDBLOCK:
          "The socket operation could not complete without blocking",
        errno.WSAEINPROGRESS: "Operation now in progress",
        errno.WSAEALREADY: "Operation already in progress",
        errno.WSAENOTSOCK: "Socket operation on non-socket",
        errno.WSAEDESTADDRREQ: "Destination address required",
        errno.WSAEMSGSIZE: "Message too long",
        errno.WSAEPROTOTYPE: "Protocol wrong type for socket",
        errno.WSAENOPROTOOPT: "Protocol not available",
        errno.WSAEPROTONOSUPPORT: "Protocol not supported",
        errno.WSAESOCKTNOSUPPORT: "Socket type not supported",
        errno.WSAEOPNOTSUPP: "Operation not supported",
        errno.WSAEPFNOSUPPORT: "Protocol family not supported",
        errno.WSAEAFNOSUPPORT: "Address family not supported",
        errno.WSAEADDRINUSE: "Address already in use",
        errno.WSAEADDRNOTAVAIL: "Can't assign requested address",
        errno.WSAENETDOWN: "Network is down",
        errno.WSAENETUNREACH: "Network is unreachable",
        errno.WSAENETRESET: "Network dropped connection on reset",
        errno.WSAECONNABORTED: "Software caused connection abort",
        errno.WSAECONNRESET: "Connection reset by peer",
        errno.WSAENOBUFS: "No buffer space available",
        errno.WSAEISCONN: "Socket is already connected",
        errno.WSAENOTCONN: "Socket is not connected",
        errno.WSAESHUTDOWN: "Can't send after socket shutdown",
        errno.WSAETOOMANYREFS: "Too many references: can't splice",
        errno.WSAETIMEDOUT: "Operation timed out",
        errno.WSAECONNREFUSED: "Connection refused",
        errno.WSAELOOP: "Too many levels of symbolic links",
        errno.WSAENAMETOOLONG: "File name too long",
        errno.WSAEHOSTDOWN: "Host is down",
        errno.WSAEHOSTUNREACH: "No route to host",
        errno.WSAENOTEMPTY: "Directory not empty",
        errno.WSAEPROCLIM: "Too many processes",
        errno.WSAEUSERS: "Too many users",
        errno.WSAEDQUOT: "Disc quota exceeded",
        errno.WSAESTALE: "Stale NFS file handle",
        errno.WSAEREMOTE: "Too many levels of remote in path",
        errno.WSASYSNOTREADY: "Network subsystem is unvailable",
        errno.WSAVERNOTSUPPORTED: "WinSock version is not supported",
        errno.WSANOTINITIALISED: "Successful WSAStartup() not yet performed",
        errno.WSAEDISCON: "Graceful shutdown in progress",

        # Resolver errors
        # XXX Not exported by errno. Replace by the values in winsock.h
        # errno.WSAHOST_NOT_FOUND: "No such host is known",
        # errno.WSATRY_AGAIN: "Host not found, or server failed",
        # errno.WSANO_RECOVERY: "Unexpected server error encountered",
        # errno.WSANO_DATA: "Valid name without requested data",
        # errno.WSANO_ADDRESS: "No address, look for MX record",
        }

    def socket_strerror(errno):
        return WIN32_ERROR_MESSAGES.get(errno, "winsock error")
else:
    import os
    def socket_strerror(errno):
        return os.strerror(errno)

def wrap_socketerror(space, e):
    assert isinstance(e, socket.error)
    errno = e.args[0]
    msg = socket_strerror(errno)
    
    w_module = space.getbuiltinmodule('_socket')
    if isinstance(e, socket.gaierror):
        w_errortype = space.getattr(w_module, space.wrap('gaierror'))
    elif isinstance(e, socket.herror):
        w_errortype = space.getattr(w_module, space.wrap('herror'))
    else:
        w_errortype = space.getattr(w_module, space.wrap('error'))
        
    return OperationError(w_errortype,
                          space.wrap(errno),
                          space.wrap(msg))

def wrap_timeouterror(space):
    
    w_module = space.getbuiltinmodule('_socket')
    w_error = space.getattr(w_module, space.wrap('timeout'))
        
    w_error = space.call_function(w_error,
                                  space.wrap("timed out"))
    return w_error

def gethostname(space):
    """gethostname() -> string

    Return the current host name.
    """
    try:
        return space.wrap(socket.gethostname())
    except socket.error, e:
        raise wrap_socketerror(space, e)
gethostname.unwrap_spec = [ObjSpace]

def gethostbyname(space, name):
    """gethostbyname(host) -> address

    Return the IP address (a string of the form '255.255.255.255') for a host.
    """
    try:
        return space.wrap(socket.gethostbyname(name))
    except socket.error, e:
        raise wrap_socketerror(space, e)
gethostbyname.unwrap_spec = [ObjSpace, str]

def gethostbyname_ex(space, name):
    """gethostbyname_ex(host) -> (name, aliaslist, addresslist)

    Return the true host name, a list of aliases, and a list of IP addresses,
    for a host.  The host argument is a string giving a host name or IP number.
    """
    try:
        return space.wrap(socket.gethostbyname_ex(name))
    except socket.error, e:
        raise wrap_socketerror(space, e)
gethostbyname_ex.unwrap_spec = [ObjSpace, str]

def gethostbyaddr(space, ip_num):
    """gethostbyaddr(host) -> (name, aliaslist, addresslist)

    Return the true host name, a list of aliases, and a list of IP addresses,
    for a host.  The host argument is a string giving a host name or IP number.
    """
    try:
        return space.wrap(socket.gethostbyaddr(ip_num))
    except socket.error, e:
        raise wrap_socketerror(space, e)
gethostbyaddr.unwrap_spec = [ObjSpace, str]

def getservbyname(space, name, w_proto=NoneNotWrapped):
    """getservbyname(servicename[, protocolname]) -> integer

    Return a port number from a service name and protocol name.
    The optional protocol name, if given, should be 'tcp' or 'udp',
    otherwise any protocol will match.
    """
    try:
        if w_proto is None:
            return space.wrap(socket.getservbyname(name))
        else:
            return space.wrap(socket.getservbyname(name, space.str_w(w_proto)))
    except socket.error, e:
        raise wrap_socketerror(space, e)
getservbyname.unwrap_spec = [ObjSpace, str, W_Root]

def getservbyport(space, port, w_proto=NoneNotWrapped):
    """getservbyport(port[, protocolname]) -> string

    Return the service name from a port number and protocol name.
    The optional protocol name, if given, should be 'tcp' or 'udp',
    otherwise any protocol will match.
    """
    try:
        if w_proto is None:
            return space.wrap(socket.getservbyport(port))
        else:
            return space.wrap(socket.getservbyport(port, space.str_w(w_proto)))
    except socket.error, e:
        raise wrap_socketerror(space, e)
getservbyport.unwrap_spec = [ObjSpace, int, W_Root]

def getprotobyname(space, name):
    """getprotobyname(name) -> integer

    Return the protocol number for the named protocol.  (Rarely used.)
    """
    try:
        return space.wrap(socket.getprotobyname(name))
    except socket.error, e:
        raise wrap_socketerror(space, e)
getprotobyname.unwrap_spec = [ObjSpace, str]

def fromfd(space, fd, family, type, w_proto=NoneNotWrapped):
    """fromfd(fd, family, type[, proto]) -> socket object

    Create a socket object from the given file descriptor.
    The remaining arguments are the same as for socket().
    """
    try:
        if w_proto is None:
            return space.wrap(socket.fromfd(fd, family, type))
        else:
            return space.wrap(socket.fromfd(fd, family, type, space.int_w(w_proto)))
    except socket.error, e:
        raise wrap_socketerror(space, e)
fromfd.unwrap_spec = [ObjSpace, int, int, int, W_Root]

def socketpair(space, w_family=NoneNotWrapped, w_type=NoneNotWrapped, w_proto=NoneNotWrapped):
    """socketpair([family[, type[, proto]]]) -> (socket object, socket object)

    Create a pair of socket objects from the sockets returned by the platform
    socketpair() function.
    The arguments are the same as for socket() except the default family is
    AF_UNIX if defined on the platform; otherwise, the default is AF_INET.
    """
    try:
        if w_family is None:
            return space.wrap(socket.socketpair())
        elif w_type is None:
            return space.wrap(socket.socketpair(space.int_w(w_family)))
        elif w_proto is None:
            return space.wrap(socket.socketpair(space.int_w(w_family),
                                                space.int_w(w_type)))
        else:
            return space.wrap(socket.socketpair(space.int_w(w_family),
                                                space.int_w(w_type),
                                                space.int_w(w_proto)))
    except socket.error, e:
        raise wrap_socketerror(space, e)
socketpair.unwrap_spec = [ObjSpace, W_Root, W_Root, W_Root]

def ntohs(space, x):
    """ntohs(integer) -> integer

    Convert a 16-bit integer from network to host byte order.
    """
    try:
        return space.wrap(socket.ntohs(x))
    except socket.error, e:
        raise wrap_socketerror(space, e)
ntohs.unwrap_spec = [ObjSpace, int]

def ntohl(space, x):
    """ntohl(integer) -> integer

    Convert a 32-bit integer from network to host byte order.
    """
    try:
        return space.wrap(socket.ntohl(x))
    except socket.error, e:
        raise wrap_socketerror(space, e)
ntohl.unwrap_spec = [ObjSpace, int]
    
def htons(space, x):
    """htons(integer) -> integer

    Convert a 16-bit integer from host to network byte order.
    """
    try:
        return space.wrap(socket.htons(x))
    except socket.error, e:
        raise wrap_socketerror(space, e)
htons.unwrap_spec = [ObjSpace, int]
    
def htonl(space, x):
    """htonl(integer) -> integer

    Convert a 32-bit integer from host to network byte order.
    """
    try:
        return space.wrap(socket.htonl(x))
    except socket.error, e:
        raise wrap_socketerror(space, e)
htonl.unwrap_spec = [ObjSpace, int]

def inet_aton(space, ip):
    """inet_aton(string) -> packed 32-bit IP representation

    Convert an IP address in string format (123.45.67.89) to the 32-bit packed
    binary format used in low-level network functions.
    """
    try:
        return space.wrap(socket.inet_aton(ip))
    except socket.error, e:
        raise wrap_socketerror(space, e)
inet_aton.unwrap_spec = [ObjSpace, str]

def inet_ntoa(space, packed):
    """inet_ntoa(packed_ip) -> ip_address_string

    Convert an IP address from 32-bit packed binary format to string format
    """
    try:
        return space.wrap(socket.inet_ntoa(packed))
    except socket.error, e:
        raise wrap_socketerror(space, e)
inet_ntoa.unwrap_spec = [ObjSpace, str]

def inet_pton(space, af, ip):
    """inet_pton(af, ip) -> packed IP address string

    Convert an IP address from string format to a packed string suitable
    for use with low-level network functions.
    """
    try:
        return space.wrap(socket.inet_pton(af, ip))
    except socket.error, e:
        raise wrap_socketerror(space, e)
inet_pton.unwrap_spec = [ObjSpace, int, str]

def inet_ntop(space, af, packed):
    """inet_ntop(af, packed_ip) -> string formatted IP address

    Convert a packed IP address of the given family to string format.
    """
    try:
        return space.wrap(socket.inet_ntop(af, packed))
    except socket.error, e:
        raise wrap_socketerror(space, e)
inet_ntop.unwrap_spec = [ObjSpace, int, str]

def getaddrinfo(space, w_host, w_port, family=0, socktype=0, proto=0, flags=0):
    """getaddrinfo(host, port [, family, socktype, proto, flags])
        -> list of (family, socktype, proto, canonname, sockaddr)

    Resolve host and port into addrinfo struct.
    """
    if space.is_true(space.isinstance(w_host, space.w_unicode)):
        w_host = space.call_method(w_host, "encode", space.wrap("idna"))
    host = space.unwrap(w_host)

    if space.is_true(space.isinstance(w_port, space.w_int)):
        port = str(space.int_w(w_port))
    else:
        port = space.str_w(w_port)
    
    try:
        return space.wrap(socket.getaddrinfo(host, port, family, socktype, proto, flags))
    except socket.error, e:
        raise wrap_socketerror(space, e)
getaddrinfo.unwrap_spec = [ObjSpace, W_Root, W_Root, int, int, int, int]

def getnameinfo(space, w_sockaddr, flags):
    """getnameinfo(sockaddr, flags) --> (host, port)

    Get host and port for a sockaddr."""
    sockaddr = space.unwrap(w_sockaddr)
    try:
        return space.wrap(socket.getnameinfo(sockaddr, flags))
    except socket.error, e:
        raise wrap_socketerror(space, e)
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

def getsockettype(space):
    return space.gettypeobject(Socket.typedef)

def newsocket(space, w_subtype, family=socket.AF_INET,
              type=socket.SOCK_STREAM, proto=0):
    # sets the timeout for the CPython implementation
    timeout = getstate(space).defaulttimeout
    if timeout < 0.0:
        socket.setdefaulttimeout(None)
    else:
        socket.setdefaulttimeout(timeout)
            
    try:
        fd = socket.socket(family, type, proto)
    except socket.error, e:
        raise wrap_socketerror(space, e)
    sock = space.allocate_instance(Socket, w_subtype)
    Socket.__init__(sock, space, fd, family, type, proto)
    return space.wrap(sock)
descr_socket_new = interp2app(newsocket,
                               unwrap_spec=[ObjSpace, W_Root, int, int, int])
    
class Socket(Wrappable):
    "A wrappable box around an interp-level socket object."

    def __init__(self, space, fd, family, type, proto):
        self.fd = fd
        self.family = family
        self.type = type
        self.proto = proto
        self.timeout = getstate(space).defaulttimeout

    def accept(self, space):
        """accept() -> (socket object, address info)

        Wait for an incoming connection.  Return a new socket representing the
        connection, and the address of the client.  For IP sockets, the address
        info is a pair (hostaddr, port).
        """
        try:
            newfd, address = self.fd.accept()
        except socket.error, e:
            raise wrap_socketerror(space, e)
        newsock = Socket(newfd, self.family, self.type, self.proto)
        return space.wrap((newsock, address))
    accept.unwrap_spec = ['self', ObjSpace]
        
    def bind(self, space, w_addr):
        """bind(address)
        
        Bind the socket to a local address.  For IP sockets, the address is a
        pair (host, port); the host must refer to the local host. For raw packet
        sockets the address is a tuple (ifname, proto [,pkttype [,hatype]])
        """
        addr = space.unwrap(w_addr)
        try:
            self.fd.bind(addr)
        except socket.error, e:
            raise wrap_socketerror(space, e)
    bind.unwrap_spec = ['self', ObjSpace, W_Root]
        
    def close(self, space):
        """close()

        Close the socket.  It cannot be used after this call.
        """
        if self.fd is not None:
            fd = self.fd
            self.fd = None
            fd.close()
    close.unwrap_spec = ['self', ObjSpace]

    def connect(self, space, w_addr):
        """connect(address)

        Connect the socket to a remote address.  For IP sockets, the address
        is a pair (host, port).
        """
        addr = space.unwrap(w_addr)
        try:
            self.fd.connect(addr)
        except timeout:
            raise wrap_timeout(space)
        except socket.error, e:
            raise wrap_socketerror(space, e)
    connect.unwrap_spec = ['self', ObjSpace, W_Root]
        
    def connect_ex(self, space, w_addr):
        """connect_ex(address) -> errno
        
        This is like connect(address), but returns an error code (the errno value)
        instead of raising an exception when an error occurs.
        """
        addr = space.unwrap(w_addr)
        try:
            self.fd.connect(addr)
        except socket.error, e:
            return space.wrap(e.errno)
    connect_ex.unwrap_spec = ['self', ObjSpace, W_Root]
        
    def dup(self, space):
        """dup() -> socket object

        Return a new socket object connected to the same system resource.
        """
        try:
            newfd = self.fd.dup()
        except socket.error, e:
            raise wrap_socketerror(space, e)
        newsock = Socket(newfd, self.family, self.type, self.proto)
        return space.wrap(newsock)
    dup.unwrap_spec = ['self', ObjSpace]

    def fileno(self, space):
        """fileno() -> integer

        Return the integer file descriptor of the socket.
        """
        return space.wrap(self.fd.fileno())
    fileno.unwrap_spec = ['self', ObjSpace]

    def getpeername(self, space):
        """getpeername() -> address info

        Return the address of the remote endpoint.  For IP sockets, the address
        info is a pair (hostaddr, port).
        """
        try:
            return space.wrap(self.fd.getpeername())
        except socket.error, e:
            raise wrap_socketerror(space, e)
    getpeername.unwrap_spec = ['self', ObjSpace]

    def getsockname(self, space):
        """getsockname() -> address info

        Return the address of the local endpoint.  For IP sockets, the address
        info is a pair (hostaddr, port).
        """
        try:
            return space.wrap(self.fd.getsockname())
        except socket.error, e:
            raise wrap_socketerror(space, e)
    getsockname.unwrap_spec = ['self', ObjSpace]
        
    def getsockopt(self, space, level, option, w_buffersize=NoneNotWrapped):
        """getsockopt(level, option[, buffersize]) -> value

        Get a socket option.  See the Unix manual for level and option.
        If a nonzero buffersize argument is given, the return value is a
        string of that length; otherwise it is an integer.
        """
        try:
            if w_buffersize is None:
                return space.wrap(self.fd.getsockopt(level, option))
            else:
                buffersize = space.int_w(w_buffersize)
                return space.wrap(self.fd.getsockopt(level, option, buffersize))
        except socket.error, e:
            raise wrap_socketerror(space, e)
    getsockopt.unwrap_spec = ['self', ObjSpace, int, int, W_Root]
        
    def listen(self, space, backlog):
        """listen(backlog)

        Enable a server to accept connections.  The backlog argument must be at
        least 1; it specifies the number of unaccepted connection that the system
        will allow before refusing new connections.
        """
        try:
            self.fd.listen(backlog)
        except socket.error, e:
            raise wrap_socketerror(space, e)
    listen.unwrap_spec = ['self', ObjSpace, int]
        
    def makefile(self, space, mode="r", buffersize=-1):
        """makefile([mode[, buffersize]]) -> file object

        Return a regular file object corresponding to the socket.
        The mode and buffersize arguments are as for the built-in open() function.
        """
        try:
            f = self.fd.makefile(mode, buffersize)
        except socket.error, e:
            raise wrap_socketerror(space, e)
        return f
    makefile.unwrap_spec = ['self', ObjSpace, str, int]

    def recv(self, space, buffersize, flags=0):
        """recv(buffersize[, flags]) -> data

        Receive up to buffersize bytes from the socket.  For the optional flags
        argument, see the Unix manual.  When no data is available, block until
        at least one byte is available or until the remote end is closed.  When
        the remote end is closed and all data is read, return the empty string.
        """
        try:
            return space.wrap(self.fd.recv(buffersize, flags))
        except socket.error, e:
            raise wrap_socketerror(space, e)
    recv.unwrap_spec = ['self', ObjSpace, int, int]

    def recvfrom(self, space, buffersize, flags=0):
        """recvfrom(buffersize[, flags]) -> (data, address info)

        Like recv(buffersize, flags) but also return the sender's address info.
        """
        try:
            return space.wrap(self.fd.recvfrom(buffersize, flags))
        except socket.error, e:
            raise wrap_socketerror(space, e)
    recvfrom.unwrap_spec = ['self', ObjSpace, int, int]

    def send(self, space, data, flags=0):
        """send(data[, flags]) -> count

        Send a data string to the socket.  For the optional flags
        argument, see the Unix manual.  Return the number of bytes
        sent; this may be less than len(data) if the network is busy.
        """
        try:
            return space.wrap(self.fd.send(data, flags))
        except socket.error, e:
            raise wrap_socketerror(space, e)
    send.unwrap_spec = ['self', ObjSpace, str, int]
        
    def sendall(self, space, data, flags=0):
        """sendall(data[, flags])

        Send a data string to the socket.  For the optional flags
        argument, see the Unix manual.  This calls send() repeatedly
        until all data is sent.  If an error occurs, it's impossible
        to tell how much data has been sent.
        """
        try:
            self.fd.sendall(data, flags)
        except socket.error, e:
            raise wrap_socketerror(space, e)
    sendall.unwrap_spec = ['self', ObjSpace, str, int]
    
    def sendto(self, space, data, w_param2, w_param3=NoneNotWrapped):
        """sendto(data[, flags], address) -> count

        Like send(data, flags) but allows specifying the destination address.
        For IP sockets, the address is a pair (hostaddr, port).
        """
        if w_param3 is None:
            # 2 args version
            flags = 0
            addr = space.str_w(w_param2)
        else:
            # 3 args version
            flags = space.int_w(w_param2)
            addr = space.str_w(w_param3)
        try:
            self.fd.sendto(data, flags, addr)
        except socket.error, e:
            raise wrap_socketerror(space, e)
    sendto.unwrap_spec = ['self', ObjSpace, str, W_Root, W_Root]
    
    def setblocking(self, space, flag):
        """setblocking(flag)

        Set the socket to blocking (flag is true) or non-blocking (false).
        setblocking(True) is equivalent to settimeout(None);
        setblocking(False) is equivalent to settimeout(0.0).
        """
        if flag:
            self.settimeout(space, None)
        else:
            self.settimeout(space, 0.0)
    setblocking.unwrap_spec = ['self', ObjSpace, int]

    def setsockopt(self, space, level, option, w_value):
        """setsockopt(level, option, value)

        Set a socket option.  See the Unix manual for level and option.
        The value argument can either be an integer or a string.
        """
        
        if space.is_true(space.isinstance(w_value, space.w_str)):
            strvalue = space.str_w(w_value)
            self.fd.setsockopt(level, option, strvalue)
        else:
            intvalue = space.int_w(w_value)
            self.fd.setsockopt(level, option, intvalue)
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
        self.fd.settimeout(timeout)
    settimeout.unwrap_spec = ['self', ObjSpace, W_Root]

    def shutdown(self, space, how):
        """shutdown(flag)

        Shut down the reading side of the socket (flag == SHUT_RD), the
        writing side of the socket (flag == SHUT_WR), or both ends
        (flag == SHUT_RDWR).
        """
        self.fd.shutdown(how)
    shutdown.unwrap_spec = ['self', ObjSpace, int]

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
    socketmethods[methodname] = interp2app(method, method.unwrap_spec)

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
    **socketmethods
    )

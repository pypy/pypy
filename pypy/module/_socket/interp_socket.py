
import socket, errno, sys
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import W_Root
from pypy.interpreter.gateway import ObjSpace, NoneNotWrapped

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
    def socket_strerror(errno):
        return os.strerror(errno)

def wrap_socketerror(space, e):
    assert isinstance(e, socket.error)
    errno = e.args[0]
    msg = socket_strerror(errno)
    
    w_module = space.getbuiltinmodule('_socket')
    if isinstance(e, socket.gaierror):
        w_error = space.getattr(w_module, space.wrap('gaierror'))
    elif isinstance(e, socket.herror):
        w_error = space.getattr(w_module, space.wrap('gaierror'))
    else:
        w_error = space.getattr(w_module, space.wrap('error'))
        
    w_error = space.call_function(w_error,
                                  space.wrap(errno),
                                  space.wrap(msg))
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



import socket
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import W_Root
from pypy.interpreter.gateway import ObjSpace, NoneNotWrapped

def gethostname(space):
    """gethostname() -> string

    Return the current host name.
    """
    return space.wrap(socket.gethostname())
gethostname.unwrap_spec = [ObjSpace]

def gethostbyname(space, name):
    """gethostbyname(host) -> address

    Return the IP address (a string of the form '255.255.255.255') for a host.
    """
    return space.wrap(socket.gethostbyname(name))
gethostbyname.unwrap_spec = [ObjSpace, str]

def gethostbyname_ex(space, name):
    """gethostbyname_ex(host) -> (name, aliaslist, addresslist)

    Return the true host name, a list of aliases, and a list of IP addresses,
    for a host.  The host argument is a string giving a host name or IP number.
    """
    return space.wrap(socket.gethostbyname_ex(name))
gethostbyname_ex.unwrap_spec = [ObjSpace, str]

def gethostbyaddr(space, ip_num):
    """gethostbyaddr(host) -> (name, aliaslist, addresslist)

    Return the true host name, a list of aliases, and a list of IP addresses,
    for a host.  The host argument is a string giving a host name or IP number.
    """
    return space.wrap(socket.gethostbyaddr(ip_num))
gethostbyaddr.unwrap_spec = [ObjSpace, str]

def getservbyname(space, name, w_proto=NoneNotWrapped):
    """getservbyname(servicename[, protocolname]) -> integer

    Return a port number from a service name and protocol name.
    The optional protocol name, if given, should be 'tcp' or 'udp',
    otherwise any protocol will match.
    """
    if w_proto is None:
        return space.wrap(socket.getservbyname(name))
    else:
        return space.wrap(socket.getservbyname(name, space.str_w(w_proto)))
getservbyname.unwrap_spec = [ObjSpace, str, W_Root]

def getservbyport(space, port, w_proto=NoneNotWrapped):
    """getservbyport(port[, protocolname]) -> string

    Return the service name from a port number and protocol name.
    The optional protocol name, if given, should be 'tcp' or 'udp',
    otherwise any protocol will match.
    """
    if w_proto is None:
        return space.wrap(socket.getservbyport(port))
    else:
        return space.wrap(socket.getservbyport(port, space.str_w(w_proto)))
getservbyport.unwrap_spec = [ObjSpace, int, W_Root]

def getprotobyname(space, name):
    """getprotobyname(name) -> integer

    Return the protocol number for the named protocol.  (Rarely used.)
    """
    return space.wrap(socket.getprotobyname(name))
getprotobyname.unwrap_spec = [ObjSpace, str]

def fromfd(space, fd, family, type, w_proto=NoneNotWrapped):
    """fromfd(fd, family, type[, proto]) -> socket object

    Create a socket object from the given file descriptor.
    The remaining arguments are the same as for socket().
    """
    if w_proto is None:
        return space.wrap(socket.fromfd(fd, family, type))
    else:
        return space.wrap(socket.fromfd(fd, family, type, space.int_w(w_proto)))
fromfd.unwrap_spec = [ObjSpace, int, int, int, W_Root]

def socketpair(space, w_family=NoneNotWrapped, w_type=NoneNotWrapped, w_proto=NoneNotWrapped):
    """socketpair([family[, type[, proto]]]) -> (socket object, socket object)

    Create a pair of socket objects from the sockets returned by the platform
    socketpair() function.
    The arguments are the same as for socket() except the default family is
    AF_UNIX if defined on the platform; otherwise, the default is AF_INET.
    """
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
socketpair.unwrap_spec = [ObjSpace, W_Root, W_Root, W_Root]

def ntohs(space, x):
    """ntohs(integer) -> integer

    Convert a 16-bit integer from network to host byte order.
    """
    return space.wrap(socket.ntohs(x))
ntohs.unwrap_spec = [ObjSpace, int]

def ntohl(space, x):
    """ntohl(integer) -> integer

    Convert a 32-bit integer from network to host byte order.
    """
    return space.wrap(socket.ntohl(x))
ntohl.unwrap_spec = [ObjSpace, int]
    
def htons(space, x):
    """htons(integer) -> integer

    Convert a 16-bit integer from host to network byte order.
    """
    return space.wrap(socket.htons(x))
htons.unwrap_spec = [ObjSpace, int]
    
def htonl(space, x):
    """htonl(integer) -> integer

    Convert a 32-bit integer from host to network byte order.
    """
    return space.wrap(socket.htonl(x))
htonl.unwrap_spec = [ObjSpace, int]

def inet_aton(space, ip):
    """inet_aton(string) -> packed 32-bit IP representation

    Convert an IP address in string format (123.45.67.89) to the 32-bit packed
    binary format used in low-level network functions.
    """
    return space.wrap(socket.inet_aton(ip))
inet_aton.unwrap_spec = [ObjSpace, str]

def inet_ntoa(space, packed):
    """inet_ntoa(packed_ip) -> ip_address_string

    Convert an IP address from 32-bit packed binary format to string format
    """
    return space.wrap(socket.inet_ntoa(packed))
inet_ntoa.unwrap_spec = [ObjSpace, str]

def inet_pton(space, af, ip):
    """inet_pton(af, ip) -> packed IP address string

    Convert an IP address from string format to a packed string suitable
    for use with low-level network functions.
    """
    return space.wrap(socket.inet_pton(af, ip))
inet_pton.unwrap_spec = [ObjSpace, int, str]

def inet_ntop(space, af, packed):
    """inet_ntop(af, packed_ip) -> string formatted IP address

    Convert a packed IP address of the given family to string format.
    """
    return space.wrap(socket.inet_ntop(af, packed))
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
    
    return space.wrap(socket.getaddrinfo(host, port, family, socktype, proto, flags))
getaddrinfo.unwrap_spec = [ObjSpace, W_Root, W_Root, int, int, int, int]

def getnameinfo(space, w_sockaddr, flags):
    """getnameinfo(sockaddr, flags) --> (host, port)

    Get host and port for a sockaddr."""
    sockaddr = space.unwrap(w_sockaddr)
    return space.wrap(socket.getnameinfo(sockaddr, flags))
getnameinfo.unwrap_spec = [ObjSpace, W_Root, int]

def getdefaulttimeout(space):
    """getdefaulttimeout() -> timeout

    Returns the default timeout in floating seconds for new socket objects.
    A value of None indicates that new socket objects have no timeout.
    When the socket module is first imported, the default is None.
    """
    return space.wrap(socket.getdefaulttimeout())
getdefaulttimeout.unwrap_spec = [ObjSpace]
    
def setdefaulttimeout(space, w_timeout):
    """setdefaulttimeout(timeout)

    Set the default timeout in floating seconds for new socket objects.
    A value of None indicates that new socket objects have no timeout.
    When the socket module is first imported, the default is None.
    """
    timeout = space.unwrap(w_timeout)
    return space.wrap(socket.setdefaulttimeout(timeout))
setdefaulttimeout.unwrap_spec = [ObjSpace, W_Root]


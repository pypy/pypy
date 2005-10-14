
import socket
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace, W_Root, NoneNotWrapped

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

#    fromfd socketpair
#    ntohs ntohl htons htonl inet_aton inet_ntoa inet_pton inet_ntop
#    getaddrinfo getnameinfo
#    getdefaulttimeout setdefaulttimeout

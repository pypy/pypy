from pypy.interpreter.gateway import NoneNotWrapped, unwrap_spec
from pypy.module._socket.interp_socket import converted_error, W_RSocket
from pypy.rlib import rsocket
from pypy.rlib.rsocket import SocketError
from pypy.rlib.rarithmetic import r_uint
from pypy.interpreter.error import OperationError, operationerrfmt

def gethostname(space):
    """gethostname() -> string

    Return the current host name.
    """
    try:
        res = rsocket.gethostname()
    except SocketError, e:
        raise converted_error(space, e)
    return space.wrap(res)

@unwrap_spec(host=str)
def gethostbyname(space, host):
    """gethostbyname(host) -> address

    Return the IP address (a string of the form '255.255.255.255') for a host.
    """
    try:
        addr = rsocket.gethostbyname(host)
        ip = addr.get_host()
    except SocketError, e:
        raise converted_error(space, e)
    return space.wrap(ip)

def common_wrapgethost(space, (name, aliases, address_list)):
    aliases = [space.wrap(alias) for alias in aliases]
    address_list = [space.wrap(addr.get_host()) for addr in address_list]
    return space.newtuple([space.wrap(name),
                           space.newlist(aliases),
                           space.newlist(address_list)])

@unwrap_spec(host=str)
def gethostbyname_ex(space, host):
    """gethostbyname_ex(host) -> (name, aliaslist, addresslist)

    Return the true host name, a list of aliases, and a list of IP addresses,
    for a host.  The host argument is a string giving a host name or IP number.
    """
    try:
        res = rsocket.gethostbyname_ex(host)
    except SocketError, e:
        raise converted_error(space, e)
    return common_wrapgethost(space, res)

@unwrap_spec(host=str)
def gethostbyaddr(space, host):
    """gethostbyaddr(host) -> (name, aliaslist, addresslist)

    Return the true host name, a list of aliases, and a list of IP addresses,
    for a host.  The host argument is a string giving a host name or IP number.
    """
    try:
        res = rsocket.gethostbyaddr(host)
    except SocketError, e:
        raise converted_error(space, e)
    return common_wrapgethost(space, res)

@unwrap_spec(name=str)
def getservbyname(space, name, w_proto=None):
    """getservbyname(servicename[, protocolname]) -> integer

    Return a port number from a service name and protocol name.
    The optional protocol name, if given, should be 'tcp' or 'udp',
    otherwise any protocol will match.
    """
    if space.is_w(w_proto, space.w_None):
        proto = None
    else:
        proto = space.str_w(w_proto)
    try:
        port = rsocket.getservbyname(name, proto)
    except SocketError, e:
        raise converted_error(space, e)
    return space.wrap(port)

@unwrap_spec(port=int)
def getservbyport(space, port, w_proto=None):
    """getservbyport(port[, protocolname]) -> string

    Return the service name from a port number and protocol name.
    The optional protocol name, if given, should be 'tcp' or 'udp',
    otherwise any protocol will match.
    """
    if space.is_w(w_proto, space.w_None):
        proto = None
    else:
        proto = space.str_w(w_proto)

    if port < 0 or port > 0xffff:
        raise OperationError(space.w_ValueError, space.wrap(
            "getservbyport: port must be 0-65535."))

    try:
        service = rsocket.getservbyport(port, proto)
    except SocketError, e:
        raise converted_error(space, e)
    return space.wrap(service)

@unwrap_spec(name=str)
def getprotobyname(space, name):
    """getprotobyname(name) -> integer

    Return the protocol number for the named protocol.  (Rarely used.)
    """
    try:
        proto = rsocket.getprotobyname(name)
    except SocketError, e:
        raise converted_error(space, e)
    return space.wrap(proto)

@unwrap_spec(flags=int)
def getnameinfo(space, w_sockaddr, flags):
    """getnameinfo(sockaddr, flags) --> (host, port)

    Get host and port for a sockaddr."""
    try:
        addr = rsocket.ipaddr_from_object(space, w_sockaddr)
        host, servport = rsocket.getnameinfo(addr, flags)
    except SocketError, e:
        raise converted_error(space, e)
    return space.newtuple([space.wrap(host), space.wrap(servport)])

@unwrap_spec(fd=int, family=int, type=int, proto=int)
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

@unwrap_spec(family=int, type=int, proto=int)
def socketpair(space, family=rsocket.socketpair_default_family,
                      type  =rsocket.SOCK_STREAM,
                      proto =0):
    """socketpair([family[, type[, proto]]]) -> (socket object, socket object)

    Create a pair of socket objects from the sockets returned by the platform
    socketpair() function.
    The arguments are the same as for socket() except the default family is
    AF_UNIX if defined on the platform; otherwise, the default is AF_INET.
    """
    try:
        sock1, sock2 = rsocket.socketpair(family, type, proto, W_RSocket)
    except SocketError, e:
        raise converted_error(space, e)
    return space.newtuple([space.wrap(sock1), space.wrap(sock2)])

# The following 4 functions refuse all negative numbers, like CPython 2.6.
# They could also check that the argument is not too large, but CPython 2.6
# is not doing that consistently.
@unwrap_spec(x="c_uint")
def ntohs(space, x):
    """ntohs(integer) -> integer

    Convert a 16-bit integer from network to host byte order.
    """
    return space.wrap(rsocket.ntohs(x))

@unwrap_spec(x="c_uint")
def ntohl(space, x):
    """ntohl(integer) -> integer

    Convert a 32-bit integer from network to host byte order.
    """
    return space.wrap(rsocket.ntohl(x))

@unwrap_spec(x="c_uint")
def htons(space, x):
    """htons(integer) -> integer

    Convert a 16-bit integer from host to network byte order.
    """
    return space.wrap(rsocket.htons(x))

@unwrap_spec(x="c_uint")
def htonl(space, x):
    """htonl(integer) -> integer

    Convert a 32-bit integer from host to network byte order.
    """
    return space.wrap(rsocket.htonl(x))

@unwrap_spec(ip=str)
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

@unwrap_spec(packed=str)
def inet_ntoa(space, packed):
    """inet_ntoa(packed_ip) -> ip_address_string

    Convert an IP address from 32-bit packed binary format to string format
    """
    try:
        ip = rsocket.inet_ntoa(packed)
    except SocketError, e:
        raise converted_error(space, e)
    return space.wrap(ip)

@unwrap_spec(family=int, ip=str)
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

@unwrap_spec(family=int, packed=str)
def inet_ntop(space, family, packed):
    """inet_ntop(family, packed_ip) -> string formatted IP address

    Convert a packed IP address of the given family to string format.
    """
    try:
        ip = rsocket.inet_ntop(family, packed)
    except SocketError, e:
        raise converted_error(space, e)
    except ValueError, e:     # XXX the message is lost in RPython
        raise OperationError(space.w_ValueError,
                  space.wrap(str(e)))
    return space.wrap(ip)

@unwrap_spec(family=int, socktype=int, proto=int, flags=int)
def getaddrinfo(space, w_host, w_port,
                family=rsocket.AF_UNSPEC, socktype=0, proto=0, flags=0):
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
    try:
        lst = rsocket.getaddrinfo(host, port, family, socktype,
                                  proto, flags)
    except SocketError, e:
        raise converted_error(space, e)
    lst1 = [space.newtuple([space.wrap(family),
                            space.wrap(socktype),
                            space.wrap(protocol),
                            space.wrap(canonname),
                            addr.as_object(-1, space)]) # -1 as per cpython
            for (family, socktype, protocol, canonname, addr) in lst]
    return space.newlist(lst1)

def getdefaulttimeout(space):
    """getdefaulttimeout() -> timeout

    Returns the default timeout in floating seconds for new socket objects.
    A value of None indicates that new socket objects have no timeout.
    When the socket module is first imported, the default is None.
    """
    timeout = rsocket.getdefaulttimeout()
    if timeout < 0.0:
        return space.w_None
    return space.wrap(timeout)

def setdefaulttimeout(space, w_timeout):
    if space.is_w(w_timeout, space.w_None):
        timeout = -1.0
    else:
        timeout = space.float_w(w_timeout)
        if timeout < 0.0:
            raise OperationError(space.w_ValueError,
                                 space.wrap('Timeout value out of range'))
    rsocket.setdefaulttimeout(timeout)

import sys
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import W_Root, NoneNotWrapped
from pypy.interpreter.gateway import ObjSpace, interp2app
from pypy.rpython.rctypes.socketmodule import ctypes_socket as _c
import ctypes

IPV4_ADDRESS_SIZE = 4
IPV6_ADDRESS_SIZE = 16

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
        return _c.strerror(errno)

def w_get_socketerror(space, message, errno=-1):
    w_module = space.getbuiltinmodule('_socket')
    w_errortype = space.getattr(w_module, space.wrap('error'))
    if errno > -1:
        return OperationError(w_errortype, space.wrap(errno), space.wrap(message))
    else:
        return OperationError(w_errortype, space.wrap(message))

def w_get_socketgaierror(space, message, errno=-1):
    w_module = space.getbuiltinmodule('_socket')
    w_errortype = space.getattr(w_module, space.wrap('gaierror'))
    if errno > -1:
        return OperationError(w_errortype, space.wrap(errno), space.wrap(message))
    else:
        return OperationError(w_errortype, space.wrap(message))

def w_get_socketherror(space, message, errno=-1):
    w_module = space.getbuiltinmodule('_socket')
    w_errortype = space.getattr(w_module, space.wrap('herror'))
    if errno > -1:
        return OperationError(w_errortype, space.wrap(errno), space.wrap(message))
    else:
        return OperationError(w_errortype, space.wrap(message))

def wrap_timeouterror(space):

    w_module = space.getbuiltinmodule('_socket')
    w_error = space.getattr(w_module, space.wrap('timeout'))

    w_error = space.call_function(w_error,
                                  space.wrap("timed out"))
    return w_error

def setipaddr(space, name, addr_ret, addr_ret_size, af):
    hints = _c.addr_info
    hints.ai_family = af
    hints.ai_socktype = _c.SOCK_DGRAM
    hints.ai_flags = _c.AI_PASSIVE
    res = _c.addr_info_ptr
    err = _c.getaddrinfo( None, "0", pointer(hints), pointer(res))
    if err:
        raise w_get_socketgaierror(_c.errno)
    if res.contents.ai_next:
        raise OperationError(_socket.error, space.wrap("wildcard resolved to multiple address"))
    addr = res.contents.ai_addr
    _c.freeaddrinfo(res)
    return addr
		
def w_makesockaddr(space, caddr, caddrlen, proto):
    if caddr.contents.sa_family == _c.AF_INET:
        a = _c.cast(caddr, ctypes.POINTER(_c.sockaddr_in))
        return space.newtuple([space.wrap(_c.inet_ntoa(a.contents.sin_addr)),
                                space.wrap(_c.ntohs(a.contents.sin_port))])
    else:
        raise OperationError(space.w_NotImplementedError,
                             space.wrap("Unsupported address family %d" % caddr.contents.sa_family))

def gethostname(space):
    """gethostname() -> string

    Return the current host name.
    """
    BUFFLEN = 1024
    namebuff = ctypes.create_string_buffer(BUFFLEN)
    res = _c.gethostname(namebuff, BUFFLEN - 1)
    if res < 0:
        raise w_get_socketerror(_c.errno.value)
    return space.wrap(namebuff.value)
gethostname.unwrap_spec = [ObjSpace]

def gethostbyname(space, name):
    """gethostbyname(host) -> address

    Return the IP address (a string of the form '255.255.255.255') for a host.
    """
    hostent = _c.gethostbyname(name)
    if not hostent:
        raise  w_get_socketherror(_c.h_errno.value)
    return space.wrap(hostent.contents.h_addr)
gethostbyname.unwrap_spec = [ObjSpace, str]

def gethostbyname_ex(space, name):
    """gethostbyname_ex(host) -> (name, aliaslist, addresslist)

    Return the true host name, a list of aliases, and a list of IP addresses,
    for a host.  The host argument is a string giving a host name or IP number.
    """
    hostent = _c.gethostbyname(name)
    if not hostent:
        raise  w_get_socketherror(_c.h_errno.value)
    aliases = []
    for alias in hostent.contents.h_aliases:
         if alias is None:
             break
         aliases.append(space.wrap(alias))
    address_list = []
    h_addr_list = ctypes.cast(hostent.contents.h_addr_list, ctypes.POINTER(ctypes.POINTER(_c.in_addr)))
    for addr in h_addr_list:
         if not addr:
             break
         address_list.append(space.wrap(_c.inet_ntoa(addr.contents)))

    return space.newtuple([space.wrap(hostent.contents.h_name), space.newlist(aliases), 
                            space.newlist(address_list)])
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
    # XXX POSIX says inet_aton/inet_addr shall accept octal- and hexadecimal-
    # dotted notation as well as CIDR, which we don't do currently.
    packed = inet_pton_ipv4(space, ip)
    if len(packed) == 0 or packed == "\xff\xff\xff\xff":
        # NB: The broadcast address 255.255.255.255 is illegal because it's the
        # error value in the C API
        raise w_get_socketerror(space,
                                "illegal IP address string passed to inet_aton")
    else:
        return space.wrap(packed)
inet_aton.unwrap_spec = [ObjSpace, str]

def inet_ntoa(space, packed):
    """inet_ntoa(packed_ip) -> ip_address_string

    Convert an IP address from 32-bit packed binary format to string format
    """
    try:
        return space.wrap(inet_ntop_ipv4(space, packed))
    except OperationError, e:
        if not e.match(space, space.w_ValueError):
            raise
        raise w_get_socketerror(space, "packed IP wrong length for inet_ntoa")
inet_ntoa.unwrap_spec = [ObjSpace, str]

def inet_pton(space, family, ip):
    """inet_pton(family, ip) -> packed IP address string

    Convert an IP address from string format to a packed string suitable
    for use with low-level network functions.
    """
    if family == _c.AF_INET:
        packed = inet_pton_ipv4(space, ip)
        if len(packed) == 0:
            raise w_get_socketerror(space,
                            "illegal IP address string passed to inet_pton")
        else:
            return space.wrap(packed)
    elif _c.has_ipv6 and family == _c.AF_INET6:
        packed = inet_pton_ipv6(space, ip)
        if len(packed) == 0:
            raise w_get_socketerror(space,
                            "illegal IP address string passed to inet_pton")
        else:
            return space.wrap(packed)
    else:
        raise w_get_socketerror(space,
            "Address family not supported by protocol family", errno.EAFNOSUPPORT)
inet_pton.unwrap_spec = [ObjSpace, int, str]

def inet_pton_ipv4(space, ip):
    # NB: Some platforms accept leading and trailing whitespace in the IP
    # representation. We don't.
    zero_ord = ord("0")
    nine_ord = ord("9")
    packed = ""
    number = 0
    pos = 0
    for char in ip:
        char_ord = ord(char)
        if char == ".":
            if len(packed) >= IPV4_ADDRESS_SIZE - 1 or pos == 0:
                return ""
            packed += chr(number)
            number = 0
            pos = 0
        elif char_ord >= zero_ord and char_ord <= nine_ord:
            number = number * 10 + char_ord - zero_ord
            pos += 1
            if number > 0xff or pos > 3:
                return ""
        else:
            return ""
    packed += chr(number)
    return packed

def inet_pton_ipv6(space, ip):
    zero_ord = ord("0")
    a_ord = ord("a")
    A_ord = ord("A")
    packed = ""
    number = 0
    pos = 0
    abbrev_index = -1
    i = 0

    if ip[:2] == "::":
        abbrev_index = 0
        i = 2

    while i < len(ip):
        char = ip[i]
        char_ord = ord(char)
        if char == ":":
            if pos == 0: # Abbrevation
                if abbrev_index >= 0:
                    return ""
                abbrev_index = len(packed)
            else:
                if len(packed) >= IPV6_ADDRESS_SIZE - 2:
                    return ""
                packed += chr((number & 0xff00) >> 8) + chr(number & 0xff)
                number = 0
                pos = 0
        elif char_ord >= zero_ord and char_ord < zero_ord + 10:
            number = number * 16 + char_ord - zero_ord
            pos += 1
        elif char_ord >= a_ord and char_ord < a_ord + 6:
            number = number * 16 + (char_ord - a_ord) + 10
            pos += 1
        elif char_ord >= A_ord and char_ord < A_ord + 6:
            number = number * 16 + (char_ord - A_ord) + 10
            pos += 1
        elif char == ".":
            if i - pos == 0:
                return ""
            packed_v4 = inet_pton_ipv4(space, ip[i - pos:])
            if len(packed_v4) == 0:
                return ""
            packed += packed_v4
            break
        else:
            return ""
        if pos > 4:
            return ""
        i += 1

    if i == len(ip) and not (abbrev_index == len(packed) and pos == 0):
        # The above means: No IPv4 compatibility and abbrevation not at end.
        # We need to append the last 16 bits.
        packed += chr((number & 0xff00) >> 8) + chr(number & 0xff)

    if abbrev_index >= 0:
        if len(packed) >= IPV6_ADDRESS_SIZE:
            return ""
        zeros = "\x00" * (IPV6_ADDRESS_SIZE - len(packed))
        packed = packed[:abbrev_index] + zeros + packed[abbrev_index:]

    return packed

def inet_ntop(space, family, packed):
    """inet_ntop(family, packed_ip) -> string formatted IP address

    Convert a packed IP address of the given family to string format.
    """
    if family == _c.AF_INET:
        return space.wrap(inet_ntop_ipv4(space, packed))
    elif _c.has_ipv6 and family == _c.AF_INET6:
        return space.wrap(inet_ntop_ipv6(space, packed))
    else:
        raise OperationError(space.w_ValueError,
                             space.wrap("unknown address family %s" % family))
inet_ntop.unwrap_spec = [ObjSpace, int, str]

def inet_ntop_ipv4(space, packed):
    if len(packed) != IPV4_ADDRESS_SIZE:
        raise OperationError(space.w_ValueError,
                             space.wrap("invalid length of packed IP address string"))
    numbers = ord(packed[0]), ord(packed[1]), ord(packed[2]), ord(packed[3])
    return "%d.%d.%d.%d" % numbers

def inet_ntop_ipv6(space, packed):
    # XXX Currently does abbrevation of consecutive zeros only for leading zeros
    if len(packed) != IPV6_ADDRESS_SIZE:
        raise OperationError(space.w_ValueError,
                             space.wrap("invalid length of packed IP address string"))
    numbers = []
    for byte in packed:
        numbers.append(ord(byte))
    
    # Skip leading zeros
    pos = 0
    part = 0
    while part == 0 and pos < IPV6_ADDRESS_SIZE:
        part = (numbers[pos] << 8) + numbers[pos + 1]
        if part == 0:
            pos += 2

    # All zeros
    if pos == IPV6_ADDRESS_SIZE:
        return "::"

    # IPv4-compatible address
    elif pos >= IPV6_ADDRESS_SIZE - 4:
        ipv4 = inet_ntop_ipv4(space, packed[IPV6_ADDRESS_SIZE - 4:])
        return "::" + ipv4

    # IPv4-mapped IPv6 address
    elif pos == IPV6_ADDRESS_SIZE - 6 and numbers[pos] == 0xff and numbers[pos + 1] == 0xff:
        ipv4 = inet_ntop_ipv4(space, packed[IPV6_ADDRESS_SIZE - 4:])
        return "::ffff:" + ipv4

    # Standard IPv6 address
    else:
        if pos > 0:
            ip = ":" # there were leading zeros
        else:
            ip = ""
        for pos in range(pos, IPV6_ADDRESS_SIZE, 2):
            if len(ip) > 0:
                ip += ":"
            part = (numbers[pos] << 8) + numbers[pos + 1]
            ip += "%x" % part
        return ip

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
    retval = _c.getaddrinfo(host, port, ctypes.pointer(hints), ctypes.pointer(res))
    if retval < 0:
        raise w_get_socketgaierror(_c.gai_strerror(_c.errno), _c.errno.value)

    try:
        result = []
        next = res
        while next:
            info = next.contents
            next = info.ai_next
            w_family = space.wrap(info.ai_family)
            w_socktype = space.wrap(info.ai_socktype)
            w_proto = space.wrap(info.ai_protocol)
            if info.ai_canonname:
                w_canonname = space.wrap(info.ai_canonname)
            else:
                w_canonname = space.wrap('')
            w_addr = w_makesockaddr(space, info.ai_addr, info.ai_addrlen,
                                    info.ai_protocol)
            result.append(space.newtuple([w_family, w_socktype, w_proto,
                                           w_canonname, w_addr]))
        return space.newlist(result)
    finally:
        _c.freeaddrinfo(res)
getaddrinfo.unwrap_spec = [ObjSpace, W_Root, W_Root, int, int, int, int]

def getnameinfo(space, w_sockaddr, flags):
    """getnameinfo(sockaddr, flags) --> (host, port)

    Get host and port for a sockaddr."""
    sockaddr = space.unwrap(w_sockaddr)
    try:
        return space.wrap(_c.getnameinfo(sockaddr, flags))
    except _c.error, e:
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

def newsocket(space, w_subtype, family=_c.AF_INET,
              type=_c.SOCK_STREAM, proto=0):
    # sets the timeout for the CPython implementation
    timeout = getstate(space).defaulttimeout
    if timeout < 0.0:
        _c.setdefaulttimeout(None)
    else:
        _c.setdefaulttimeout(timeout)

    try:
        fd = _c.socket(family, type, proto)
    except _c.error, e: # On untranslated PyPy
        raise wrap_socketerror(space, e)
    except OSError, e: # On translated PyPy
        raise w_get_socketerror(space, e.strerror, e.errno)
    # XXX If we want to support subclassing the socket type we will need
    # something along these lines. But allocate_instance is only defined
    # on the standard object space, so this is not really correct.
    #sock = space.allocate_instance(Socket, w_subtype)
    #Socket.__init__(sock, space, fd, family, type, proto)
    #return space.wrap(sock)
    return space.wrap(Socket(space, fd, family, type, proto))
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
        self.closed = False

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
        if not self.closed:
            res = _c.close(self.fd)
            if res < 0:
                errno = _c.errno.value
                raise w_get_socketerror(space, socket_strerror(errno), errno)
            self.closed = True
    close.unwrap_spec = ['self', ObjSpace]

    def connect(self, space, w_addr):
        """connect(address)

        Connect the socket to a remote address.  For IP sockets, the address
        is a pair (host, port).
        """
        if self.family == socket.AF_INET:
            if not (space.is_true(space.isinstance(w_addr, space.w_tuple)) and
                space.int_w(space.len(w_addr)) == 2):
                raise OperationError(space.w_TypeError,
                    space.wrap("AF_INET address must be tuple of length 2"))
            addr_w = space.unpackiterable(w_addr)
            if not (space.is_true(space.isinstance(addr_w[0], space.w_str))
                    and space.is_true(space.isinstance(addr_w[1], space.w_int))):
                raise OperationError(space.w_TypeError,
                    space.wrap("tuple of a string and an int required"))
            host = space.str_w(addr_w[0])
            port = space.int_w(addr_w[1])
            sockname = (host, port, 0, 0)
        else:
            # XXX IPv6 and Unix sockets missing here
            pass
        try:
            rsocket.connect(self.fd, sockname, self.family)
        except OSError, ex:
            raise w_get_socketerror(space, e.strerror, e.errno)
        # XXX timeout doesn't really work at the moment
        except socket.timeout:
            raise wrap_timeouterror(space)
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
        try:
            name = rsocket.getpeername(self.fd)
            # XXX IPv4 only
            return space.newtuple([space.wrap(name[0]), space.wrap(name[1])])
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

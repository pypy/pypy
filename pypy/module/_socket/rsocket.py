"""
An RPython implementation of sockets based on ctypes.
Note that the interface has to be slightly different - this is not
a drop-in replacement for the 'socket' module.
"""

#                ------------ IN - PROGRESS -----------

from pypy.rpython.objectmodel import instantiate
from pypy.rpython.rctypes.socketmodule import ctypes_socket as _c   # MOVE ME
from ctypes import cast, POINTER, c_char, c_char_p, pointer, byref
from ctypes import create_string_buffer, sizeof
from pypy.rpython.rctypes.astruct import offsetof


class Address(object):
    """The base class for RPython-level objects representing addresses.
    Fields:  addr    - a _c.sockaddr structure
             addrlen - size used within 'addr'
    """
    def __init__(self, addr, addrlen):
        self.addr = addr
        self.addrlen = addrlen

    def as_object(self, space):
        """Convert the address to an app-level object."""
        # If we don't know the address family, don't raise an
        # exception -- return it as a tuple.
        family = self.addr.sa_family
        buf = copy_buffer(cast(pointer(self.addr.sa_data), POINTER(c_char)),
                          self.addrlen - offsetof(_c.sockaddr_un, 'sa_data'))
        return space.newtuple([space.wrap(family),
                               space.wrap(buf.raw)])

    def from_object(space, w_address):
        """Convert an app-level object to an Address."""
        # It's a static method but it's overridden and must be called
        # on the correct subclass.
        raise SocketError("unknown address family")
    from_object = staticmethod(from_object)

    def eq(self, other):   # __eq__() is not called by RPython :-/
        if self.family != other.family:
            return False
        elif self.addrlen != other.addrlen:
            return False
        else:
            return equal_buffers(cast(pointer(self.addr),  POINTER(c_char)),
                                 cast(pointer(other.addr), POINTER(c_char)),
                                 self.addrlen)

# ____________________________________________________________

def makeipaddr(name, result=None):
    # Convert a string specifying a host name or one of a few symbolic
    # names to an IPAddress instance.  This usually calls getaddrinfo()
    # to do the work; the names "" and "<broadcast>" are special.
    # If 'result' is specified it must be a prebuilt INETAddress or
    # INET6Address that is filled; otherwise a new INETXAddress is returned.
    if result is None:
        family = _c.AF_UNSPEC
    else:
        family = result.family

    if len(name) == 0:
        hints = _c.addrinfo(ai_family   = family,
                            ai_socktype = _c.SOCK_DGRAM,   # dummy
                            ai_flags    = _c.AI_PASSIVE)
        res = _c.addrinfo_ptr()
        error = _c.getaddrinfo(None, "0", byref(hints), byref(res))
        if error:
            raise GAIError(error)
        try:
            info = res.contents
            if info.ai_next:
                raise SocketError("wildcard resolved to "
                                  "multiple addresses")
            return make_address(info.ai_addr, info.ai_addrlen, result)
        finally:
            _c.freeaddrinfo(res)

    # IPv4 also supports the special name "<broadcast>".
    if name == '<broadcast>':
        return makeipv4addr(_c.INADDR_BROADCAST, result)

    # "dd.dd.dd.dd" format.
    digits = name.split('.')
    if len(digits) == 4:
        try:
            d0 = int(digits[0])
            d1 = int(digits[1])
            d2 = int(digits[2])
            d3 = int(digits[3])
        except ValueError:
            pass
        else:
            if (0 <= d0 <= 255 and
                0 <= d1 <= 255 and
                0 <= d2 <= 255 and
                0 <= d3 <= 255):
                return makeipv4addr(_c.htonl(
                    (d0 << 24) | (d1 << 16) | (d2 << 8) | (d3 << 0)),
                                    result)

    # generic host name to IP conversion
    hints = _c.addrinfo(ai_family = family)
    res = _c.addrinfo_ptr()
    error = _c.getaddrinfo(name, None, byref(hints), byref(res))
    # PLAT EAI_NONAME
    if error:
        raise GAIError(error)
    try:
        info = res.contents
        return make_address(info.ai_addr, info.ai_addrlen, result)
    finally:
        _c.freeaddrinfo(res)

class IPAddress(Address):
    """AF_INET and AF_INET6 addresses"""

    def get_host(self):
        # Create a string object representing an IP address.
        # For IPv4 this is always a string of the form 'dd.dd.dd.dd'
        # (with variable size numbers).
        buf = create_string_buffer(_c.NI_MAXHOST)
        error = _c.getnameinfo(byref(self.addr), self.addrlen,
                               buf, _c.NI_MAXHOST,
                               None, 0, _c.NI_NUMERICHOST)
        if error:
            raise GAIError(error)
        return buf.value

# ____________________________________________________________

class INETAddress(IPAddress):
    family = _c.AF_INET
    struct = _c.sockaddr_in
    maxlen = sizeof(struct)

    def __init__(self, host, port):
        makeipaddr(host, self)
        a = self.as_sockaddr_in()
        a.sin_port = _c.htons(port)

    def as_sockaddr_in(self):
        if self.addrlen != INETAddress.maxlen:
            raise ValueError("invalid address")
        return cast(pointer(self.addr), POINTER(_c.sockaddr_in)).contents

    def __repr__(self):
        try:
            return '<INETAddress %s:%d>' % (self.get_host(), self.get_port())
        except (ValueError, GAIError):
            return '<INETAddress ?>'

    def get_port(self):
        a = self.as_sockaddr_in()
        return _c.ntohs(a.sin_port)

    def as_object(self, space):
        return space.newtuple([space.wrap(self.get_host()),
                               space.wrap(self.get_port())])

    def from_object(space, w_address):
        # Parse an app-level object representing an AF_INET address
        w_host, w_port = space.unpackiterable(w_address, 2)
        host = space.str_w(w_host)
        port = space.int_w(w_port)
        return INETAddress(host, port)
    from_object = staticmethod(from_object)

# ____________________________________________________________

class INET6Address(IPAddress):
    family = _c.AF_INET6
    struct = _c.sockaddr_in6
    maxlen = sizeof(struct)

    def __init__(self, host, port, flowinfo=0, scope_id=0):
        makeipaddr(host, self)
        a = self.as_sockaddr_in6()
        a.sin6_port = _c.htons(port)
        a.sin6_flowinfo = flowinfo
        a.sin6_scope_id = scope_id

    def as_sockaddr_in6(self):
        if self.addrlen != INET6Address.maxlen:
            raise ValueError("invalid address")
        return cast(pointer(self.addr), POINTER(_c.sockaddr_in6)).contents

    def __repr__(self):
        try:
            return '<INET6Address %s:%d %d %d>' % (self.get_host(),
                                                   self.get_port(),
                                                   self.get_flowinfo(),
                                                   self.get_scope_id())
        except (ValueError, GAIError):
            return '<INET6Address ?>'

    def get_port(self):
        a = self.as_sockaddr_in6()
        return _c.ntohs(a.sin6_port)

    def get_flowinfo(self):
        a = self.as_sockaddr_in6()
        return a.sin6_flowinfo

    def get_scope_id(self):
        a = self.as_sockaddr_in6()
        return a.sin6_scope_id

    def as_object(self, space):
        return space.newtuple([space.wrap(self.get_host()),
                               space.wrap(self.get_port()),
                               space.wrap(self.get_flowinfo()),
                               space.wrap(self.get_scope_id())])

    def from_object(space, w_address):
        pieces_w = space.unpackiterable(w_address)
        if not (2 <= len(pieces_w) <= 4):
            raise SocketError("AF_INET6 address must be a tuple of length 2 "
                              "to 4, not %d" % len(pieces))
        host = space.str_w(pieces_w[0])
        port = space.int_w(pieces_w[1])
        if len(pieces_w) > 2: flowinfo = space.int_w(pieces_w[2])
        else:                 flowinfo = 0
        if len(pieces_w) > 3: scope_id = space.int_w(pieces_w[3])
        else:                 scope_id = 0
        return INET6Address(host, port, flowinfo, scope_id)
    from_object = staticmethod(from_object)

# ____________________________________________________________

class UNIXAddress(Address):
    family = _c.AF_UNIX
    struct = _c.sockaddr_un
    maxlen = sizeof(struct)

    def __init__(self, path):
        addr = _c.sockaddr_un(sun_family = _c.AF_UNIX)
        if _c.linux and path.startswith('\x00'):
            # Linux abstract namespace extension
            if len(path) > sizeof(addr.sun_path):
                raise SocketError("AF_UNIX path too long")
        else:
            # regular NULL-terminated string
            if len(path) >= sizeof(addr.sun_path):
                raise SocketError("AF_UNIX path too long")
            addr.sun_path[len(path)] = 0
        for i in range(len(path)):
            addr.sun_path[i] = ord(path[i])
        self.addr = cast(pointer(addr), _c.sockaddr_ptr).contents
        self.addrlen = offsetof(_c.sockaddr_un, 'sun_path') + len(path)

    def as_sockaddr_un(self):
        if self.addrlen <= offsetof(_c.sockaddr_un, 'sun_path'):
            raise ValueError("invalid address")
        return cast(pointer(self.addr), POINTER(_c.sockaddr_un)).contents

    def __repr__(self):
        try:
            return '<UNIXAddress %r>' % (self.get_path(),)
        except ValueError:
            return '<UNIXAddress ?>'

    def get_path(self):
        a = self.as_sockaddr_un()
        if _c.linux and a.sun_path[0] == 0:
            # Linux abstract namespace
            buf = copy_buffer(cast(pointer(a.sun_path), POINTER(c_char)),
                           self.addrlen - offsetof(_c.sockaddr_un, 'sun_path'))
            return buf.raw
        else:
            # regular NULL-terminated string
            return cast(pointer(a.sun_path), c_char_p).value

    def as_object(self, space):
        return space.wrap(self.get_path())

    def from_object(space, w_address):
        return UNIXAddress(space.str_w(w_address))
    from_object = staticmethod(from_object)

# ____________________________________________________________

_FAMILIES = {}
for klass in [INETAddress,
              INET6Address,
              UNIXAddress]:
    if klass.family is not None:
        _FAMILIES[klass.family] = klass

def familyclass(family):
    return _FAMILIES.get(family, Address)

def make_address(addrptr, addrlen, result=None):
    family = addrptr.contents.sa_family
    if result is None:
        result = instantiate(familyclass(family))
    elif result.family != family:
        raise SocketError("address family mismatched")
    paddr = copy_buffer(cast(addrptr, POINTER(c_char)), addrlen)
    result.addr = cast(paddr, _c.sockaddr_ptr).contents
    result.addrlen = addrlen
    return result

def makeipv4addr(s_addr, result=None):
    if result is None:
        result = instantiate(INETAddress)
    elif result.family != _c.AF_INET:
        raise SocketError("address family mismatched")
    sin = _c.sockaddr_in(sin_family = _c.AF_INET)   # PLAT sin_len
    sin.sin_addr.s_addr = s_addr
    paddr = cast(pointer(sin), _c.sockaddr_ptr)
    result.addr = paddr.contents
    result.addrlen = sizeof(_c.sockaddr_in)
    return result

##def make_null_address(klass):
##    result = instantiate(klass)
##    result.addr = cast(pointer(klass.struct()), _c.sockaddr_ptr).contents
##    result.addrlen = 0
##    return result
##make_null_address._annspecialcase_ = 'specialize:arg(0)'

def copy_buffer(ptr, size):
    buf = create_string_buffer(size)
    for i in range(size):
        buf[i] = ptr[i]
    return buf

def equal_buffers(ptr1, ptr2, size):
    for i in range(size):
        if ptr1[i] != ptr2[i]:
            return False
    return True

# ____________________________________________________________

class RSocket(object):
    """RPython-level socket object.
    """

    def __init__(self, family=_c.AF_INET, type=_c.SOCK_STREAM, proto=0):
        """Create a new socket."""
        fd = _c.socket(family, type, proto)
        if _c.invalid_socket(fd):
            raise self.error_handler()
        # PLAT RISCOS
        self.fd = fd
        self.family = family
        self.type = type
        self.proto = proto

    def error_handler(self):
        return last_error()

    # convert an Address into an app-level object
    def addr_as_object(self, space, address):
        return address.as_object(space)

    # convert an app-level object into an Address
    # based on the current socket's family
    def addr_from_object(self, space, w_address):
        return af_get(self.family).from_object(space, w_address)

    def _addrbuf(self):
        klass = familyclass(self.family)
        buf = create_string_buffer(klass.maxlen)
        result = instantiate(klass)
        result.addr = cast(buf, _c.sockaddr_ptr).contents
        result.addrlen = 0
        return result, _c.socklen_t(len(buf))

    def accept(self):
        """Wait for an incoming connection.
        Return (new socket object, client address)."""
        address, addrlen = self._addrbuf()
        newfd = _c.socketaccept(self.fd, byref(address.addr), byref(addrlen))
        if _c.invalid_socket(newfd):
            raise self.error_handler()
        address.addrlen = addrlen.value
        sock = make_socket(newfd, self.family, self.type, self.proto)
        return (sock, address)

    def bind(self, address):
        """Bind the socket to a local address."""
        res = _c.socketbind(self.fd, byref(address.addr), address.addrlen)
        if res < 0:
            raise self.error_handler()

    def close(self):
        """Close the socket.  It cannot be used after this call."""
        fd = self.fd
        if fd != _c.INVALID_SOCKET:
            self.fd = _c.INVALID_SOCKET
            _c.socketclose(fd)

    def connect(self, address):
        """Connect the socket to a remote address."""
        res = _c.socketconnect(self.fd, byref(address.addr), address.addrlen)
        if res != 0:
            raise self.error_handler()

    def connect_ex(self, address):
        """This is like connect(address), but returns an error code (the errno
        value) instead of raising an exception when an error occurs."""
        return _c.socketconnect(self.fd, byref(address.addr), address.addrlen)

    def fileno(self):
        return self.fd

    def getsockname(self):
        """Return the address of the local endpoint."""
        address, addrlen = self._addrbuf()
        res = _c.socketgetsockname(self.fd, byref(address.addr),
                                            byref(addrlen))
        if res < 0:
            raise self.error_handler()
        address.addrlen = addrlen.value
        return address

    def getpeername(self):
        """Return the address of the remote endpoint."""
        address, addrlen = self._addrbuf()
        res = _c.socketgetpeername(self.fd, byref(address.addr),
                                            byref(addrlen))
        if res < 0:
            raise self.error_handler()
        address.addrlen = addrlen.value
        return address

    def listen(self, backlog):
        """Enable a server to accept connections.  The backlog argument
        must be at least 1; it specifies the number of unaccepted connections
        that the system will allow before refusing new connections."""
        if backlog < 1:
            backlog = 1
        res = _c.socketlisten(self.fd, backlog)
        if res < 0:
            raise self.error_handler()

    def recv(self, buffersize, flags=0):
        """Receive up to buffersize bytes from the socket.  For the optional
        flags argument, see the Unix manual.  When no data is available, block
        until at least one byte is available or until the remote end is closed.
        When the remote end is closed and all data is read, return the empty
        string."""
        buf = create_string_buffer(buffersize)
        read_bytes = _c.socketrecv(self.fd, buf, buffersize, flags)
        if read_bytes < 0:
            raise self.error_handler()
        return buf[:read_bytes]

    def recvfrom(self, buffersize, flags=0):
        """Like recv(buffersize, flags) but also return the sender's
        address."""
        buf = create_string_buffer(buffersize)
        address, addrlen = self._addrbuf()
        read_bytes = _c.recvfrom(self.fd, buf, buffersize, flags,
                                 byref(address.addr), byref(addrlen))
        if read_bytes < 0:
            raise self.error_handler()
        address.addrlen = addrlen.value
        return (buf[:read_bytes], address)

    def send(self, data, flags=0):
        """Send a data string to the socket.  For the optional flags
        argument, see the Unix manual.  Return the number of bytes
        sent; this may be less than len(data) if the network is busy."""
        res = _c.send(self.fd, data, len(data), flags)
        if res < 0:
            raise self.error_handler()
        return res

    def sendall(self, data, flags=0):
        """Send a data string to the socket.  For the optional flags
        argument, see the Unix manual.  This calls send() repeatedly
        until all data is sent.  If an error occurs, it's impossible
        to tell how much data has been sent."""
        while data:
            res = self.send(data, flags)
            data = data[res:]

    def sendto(self, data, flags, address):
        """Like send(data, flags) but allows specifying the destination
        address.  (Note that 'flags' is mandatory here.)"""
        res = _c.sendto(self.fd, data, len(data), flags,
                        byref(address.addr), address.addrlen)
        if res < 0:
            raise self.error_handler()
        return res

    def shutdown(self, how):
        """Shut down the reading side of the socket (flag == SHUT_RD), the
        writing side of the socket (flag == SHUT_WR), or both ends
        (flag == SHUT_RDWR)."""
        res = _c.socketshutdown(self.fd, how)
        if res < 0:
            raise self.error_handler()

# ____________________________________________________________

def make_socket(fd, family, type, proto):
    result = instantiate(RSocket)
    result.fd = fd
    result.family = family
    result.type = type
    result.proto = proto
    return result

class BaseSocketError(Exception):
    pass

class SocketError(BaseSocketError):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

class CSocketError(BaseSocketError):
    def __init__(self, errno):
        self.errno = errno
    def __str__(self):
        return _c.socket_strerror(self.errno)

def last_error():
    return CSocketError(_c.geterrno())

class GAIError(BaseSocketError):
    def __init__(self, errno):
        self.errno = errno
    def __str__(self):
        return _c.gai_strerror(self.errno)

# ____________________________________________________________

if _c.AF_UNIX is None:
    socketpair_default_family = _c.AF_INET
else:
    socketpair_default_family = _c.AF_UNIX

def socketpair(family=socketpair_default_family, type=_c.SOCK_STREAM, proto=0):
    """socketpair([family[, type[, proto]]]) -> (socket object, socket object)

    Create a pair of socket objects from the sockets returned by the platform
    socketpair() function.
    The arguments are the same as for socket() except the default family is
    AF_UNIX if defined on the platform; otherwise, the default is AF_INET.
    """
    result = _c.socketpair_t()
    res = _c.socketpair(family, type, proto, byref(result))
    if res < 0:
        raise last_error()
    return (make_socket(result[0], family, type, proto),
            make_socket(result[1], family, type, proto))

def fromfd(fd, family, type, proto=0):
    # Dup the fd so it and the socket can be closed independently
    fd = _c.dup(fd)
    if fd < 0:
        raise last_error()
    return make_socket(fd, family, type, proto)

def gethostname():
    buf = create_string_buffer(1024)
    res = _c.gethostname(buf, sizeof(buf)-1)
    if res < 0:
        raise last_error()
    buf[sizeof(buf)-1] = '\x00'
    return buf.value

def gethostbyname(name):
    # XXX this works with IPv6 too, but the docs say it shouldn't...
    return makeipaddr(name)

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


class Address(object):
    """The base class for RPython-level objects representing addresses.
    Fields:  addr    - a _c.sockaddr structure
             addrlen - size used within 'addr'
    """
    def __init__(self, addr, addrlen):
        self.addr = addr
        self.addrlen = addrlen

    def raw_to_addr(self, ptr, size):
        paddr = copy_buffer(ptr, size)
        self.addr = cast(paddr, POINTER(_c.sockaddr)).contents
        self.addrlen = size

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

    def from_null():
        raise SocketError("unknown address family")
    from_null = staticmethod(from_null)

# ____________________________________________________________

class IPAddress(Address):
    """AF_INET and AF_INET6 addresses"""

    def makeipaddr(self, name):
        # Convert a string specifying a host name or one of a few symbolic
        # names to a numeric IP address.  This usually calls gethostbyname()
        # to do the work; the names "" and "<broadcast>" are special.
        if len(name) == 0:
            hints = _c.addrinfo(ai_family   = self.family,
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
                self.raw_to_addr(cast(info.ai_addr, POINTER(c_char)),
                                 info.ai_addrlen)
            finally:
                _c.freeaddrinfo(res)
            return

        # IPv4 also supports the special name "<broadcast>".
        if name == '<broadcast>':
            self.makeipv4addr(_c.INADDR_BROADCAST)
            return

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
                    self.makeipv4addr(_c.htonl(
                        (d0 << 24) | (d1 << 16) | (d2 << 8) | (d3 << 0)))
                    return

        # generic host name to IP conversion
        hints = _c.addrinfo(ai_family = self.family)
        res = _c.addrinfo_ptr()
        error = _c.getaddrinfo(name, None, byref(hints), byref(res))
        # PLAT EAI_NONAME
        if error:
            raise GAIError(error)
        try:
            info = res.contents
            self.raw_to_addr(cast(info.ai_addr, POINTER(c_char)),
                             info.ai_addrlen)
        finally:
            _c.freeaddrinfo(res)

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

    def makeipv4addr(self, s_addr):
        raise SocketError("address family mismatched")

# ____________________________________________________________

class INETAddress(IPAddress):
    family = _c.AF_INET
    struct = _c.sockaddr_in

    def __init__(self, host, port):
        self.makeipaddr(host)
        a = self.as_sockaddr_in()
        a.sin_port = _c.htons(port)

    def makeipv4addr(self, s_addr):
        sin = _c.sockaddr_in(sin_family = _c.AF_INET)   # PLAT sin_len
        sin.sin_addr.s_addr = s_addr
        paddr = cast(pointer(sin), POINTER(_c.sockaddr))
        self.addr = paddr.contents
        self.addrlen = sizeof(_c.sockaddr_in)

    def as_sockaddr_in(self):
        return cast(pointer(self.addr), POINTER(_c.sockaddr_in)).contents

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

    def from_null():
        return make_null_address(INETAddress)
    from_null = staticmethod(from_null)

# ____________________________________________________________

class INET6Address(IPAddress):
    family = _c.AF_INET6
    struct = _c.sockaddr_in6

    def __init__(self, host, port, flowinfo=0, scope_id=0):
        self.makeipaddr(host)
        a = self.as_sockaddr_in6()
        a.sin6_port = _c.htons(port)
        a.sin6_flowinfo = flowinfo
        a.sin6_scope_id = scope_id

    def as_sockaddr_in6(self):
        return cast(pointer(self.addr), POINTER(_c.sockaddr_in6)).contents

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

    def from_null():
        return make_null_address(INET6Address)
    from_null = staticmethod(from_null)

# ____________________________________________________________

class UNIXAddress(Address):
    family = _c.AF_UNIX
    struct = _c.sockaddr_un

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
            addr.sun_path[len(path)] = '\x00'
        for i in range(len(path)):
            addr.sun_path[i] = path[i]
        self.addr = cast(pointer(addr), POINTER(sockaddr)).contents
        self.addrlen = offsetof(sockaddr_un, 'sun_path') + len(path)

    def as_sockaddr_un(self):
        return cast(pointer(self.addr), POINTER(_c.sockaddr_un)).contents

    def get_path(self):
        a = self.as_sockaddr_un()
        if _c.linux and a.sun_path[0] == '\x00':
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

    def from_null():
        return make_null_address(UNIXAddress)
    from_null = staticmethod(from_null)

# ____________________________________________________________

_FAMILIES = {}
for klass in [INETAddress,
              INET6Address,
              UNIXAddress]:
    if klass.family is not None:
        _FAMILIES[klass.family] = klass

def familyclass(family):
    return _FAMILIES.get(addr.sa_family, Address)

def make_address(addr, addrlen):
    result = instantiate(familyclass(addr.sa_family))
    result.addr = addr
    result.addrlen = addrlen
    return result

def make_null_address(klass):
    result = instantiate(klass)
    result.addr = cast(pointer(klass.struct()), POINTER(_c.sockaddr)).contents
    result.addrlen = 0
    return result
make_null_address._annspecialcase_ = 'specialize:arg(0)'

def copy_buffer(ptr, size):
    buf = create_string_buffer(size)
    for i in range(size):
        buf[i] = ptr[i]
    return buf

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
        return CSocketError(_c.errno())

    # convert an Address into an app-level object
    def addr_as_object(self, space, address):
        return address.as_object(space)

    # convert an app-level object into an Address
    # based on the current socket's family
    def addr_from_object(self, space, w_address):
        return af_get(self.family).from_object(space, w_address)

    def null_addr(self):
        return familyclass(self.family).from_null()

    def accept(self):
        """Wait for an incoming connection.
        Return (new socket object, client address)."""
        address = self.null_addr()
        addrlen = _c.socklen_t()
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
        address = self.null_addr()
        addrlen = _c.socklen_t()
        res = _c.socketgetsockname(self.fd, byref(address.addr),
                                            byref(addrlen))
        if res < 0:
            raise self.error_handler()
        address.addrlen = addrlen.value
        return address

    def getpeername(self):
        """Return the address of the remote endpoint."""
        address = self.null_addr()
        addrlen = _c.socklen_t()
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
        address = self.null_addr()
        addrlen = _c.socklen_t()
        read_bytes = _c.socketrecvfrom(self.fd, buf, buffersize, flags,
                                       byref(address.addr), byref(addrlen))
        if read_bytes < 0:
            raise self.error_handler()
        address.addrlen = addrlen.value
        return (buf[:read_bytes], address)

    def send(self, data, flags=0):
        """Send a data string to the socket.  For the optional flags
        argument, see the Unix manual.  Return the number of bytes
        sent; this may be less than len(data) if the network is busy."""
        res = _c.socketsend(self.fd, data, len(data), flags)
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
        res = _c.socketsendto(self.fd, data, len(data), flags,
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

class GAIError(BaseSocketError):
    def __init__(self, errno):
        self.errno = errno
    def __str__(self):
        return _c.gai_strerror(self.errno)

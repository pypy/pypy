"""
An RPython implementation of sockets based on ctypes.
Note that the interface has to be slightly different - this is not
a drop-in replacement for the 'socket' module.
"""

# Known missing features:
#
#   - support for non-Linux platforms
#   - address families other than AF_INET, AF_INET6, AF_UNIX
#   - methods makefile(),
#   - SSL

from pypy.rlib.objectmodel import instantiate
from pypy.rlib import _rsocket_ctypes as _c
from ctypes import c_char, c_ulong, c_char_p, c_void_p
from ctypes import POINTER, pointer, byref, create_string_buffer, sizeof, cast
from pypy.rpython.rctypes.astruct import offsetof
from pypy.rlib.rarithmetic import intmask


constants = _c.constants
locals().update(constants) # Define constants from _c

if _c.MS_WINDOWS:
    def rsocket_startup():
        wsadata = _c.WSAData()
        res = _c.WSAStartup(1, byref(wsadata))
        assert res == 0
else:
    def rsocket_startup():
        pass
 
 
ntohs = _c.ntohs
ntohl = _c.ntohl
htons = _c.htons
htonl = _c.htonl


_FAMILIES = {}
class Address(object):
    """The base class for RPython-level objects representing addresses.
    Fields:  addr    - a _c.sockaddr structure
             addrlen - size used within 'addr'
    """
    class __metaclass__(type):
        def __new__(cls, name, bases, dict):
            family = dict.get('family')
            A = type.__new__(cls, name, bases, dict)
            if family is not None:
                _FAMILIES[family] = A
            return A

    def __init__(self, addr, addrlen):
        self.addr = addr
        self.addrlen = addrlen

    def as_object(self, space):
        """Convert the address to an app-level object."""
        # If we don't know the address family, don't raise an
        # exception -- return it as a tuple.
        family = self.addr.sa_family
        buf = copy_buffer(cast(pointer(self.addr.sa_data), POINTER(c_char)),
                          self.addrlen - offsetof(_c.sockaddr, 'sa_data'))
        return space.newtuple([space.wrap(family),
                               space.wrap(buf.raw)])

    def from_object(space, w_address):
        """Convert an app-level object to an Address."""
        # It's a static method but it's overridden and must be called
        # on the correct subclass.
        raise RSocketError("unknown address family")
    from_object = staticmethod(from_object)

# ____________________________________________________________

def makeipaddr(name, result=None):
    # Convert a string specifying a host name or one of a few symbolic
    # names to an IPAddress instance.  This usually calls getaddrinfo()
    # to do the work; the names "" and "<broadcast>" are special.
    # If 'result' is specified it must be a prebuilt INETAddress or
    # INET6Address that is filled; otherwise a new INETXAddress is returned.
    if result is None:
        family = AF_UNSPEC
    else:
        family = result.family

    if len(name) == 0:
        info = getaddrinfo(None, "0",
                           family=family,
                           socktype=SOCK_DGRAM,   # dummy
                           flags=AI_PASSIVE,
                           address_to_fill=result)
        if len(info) > 1:
            raise RSocketError("wildcard resolved to "
                               "multiple addresses")
        return info[0][4]

    # IPv4 also supports the special name "<broadcast>".
    if name == '<broadcast>':
        return makeipv4addr(intmask(INADDR_BROADCAST), result)

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
                return makeipv4addr(intmask(htonl(
                    (intmask(d0 << 24)) | (d1 << 16) | (d2 << 8) | (d3 << 0))),
                                    result)

    # generic host name to IP conversion
    info = getaddrinfo(name, None, family=family, address_to_fill=result)
    return info[0][4]

class IPAddress(Address):
    """AF_INET and AF_INET6 addresses"""

    def get_host(self):
        # Create a string object representing an IP address.
        # For IPv4 this is always a string of the form 'dd.dd.dd.dd'
        # (with variable size numbers).
        host, serv = getnameinfo(self, NI_NUMERICHOST | NI_NUMERICSERV)
        return host

# ____________________________________________________________

class INETAddress(IPAddress):
    family = AF_INET
    struct = _c.sockaddr_in
    maxlen = sizeof(struct)

    def __init__(self, host, port):
        makeipaddr(host, self)
        a = self.as_sockaddr_in()
        a.sin_port = htons(port)

    def as_sockaddr_in(self):
        if self.addrlen != INETAddress.maxlen:
            raise RSocketError("invalid address")
        return cast(pointer(self.addr), POINTER(_c.sockaddr_in)).contents

    def __repr__(self):
        try:
            return '<INETAddress %s:%d>' % (self.get_host(), self.get_port())
        except SocketError:
            return '<INETAddress ?>'

    def get_port(self):
        a = self.as_sockaddr_in()
        return ntohs(a.sin_port)

    def eq(self, other):   # __eq__() is not called by RPython :-/
        return (isinstance(other, INETAddress) and
                self.get_host() == other.get_host() and
                self.get_port() == other.get_port())

    def as_object(self, space):
        return space.newtuple([space.wrap(self.get_host()),
                               space.wrap(self.get_port())])

    def from_object(space, w_address):
        # Parse an app-level object representing an AF_INET address
        try:
            w_host, w_port = space.unpackiterable(w_address, 2)
        except ValueError:
            raise TypeError("AF_INET address must be a tuple of length 2")
        host = space.str_w(w_host)
        port = space.int_w(w_port)
        return INETAddress(host, port)
    from_object = staticmethod(from_object)

    def fill_from_object(self, space, w_address):
        # XXX a bit of code duplication
        _, w_port = space.unpackiterable(w_address, 2)
        port = space.int_w(w_port)
        a = self.as_sockaddr_in()
        a.sin_port = htons(port)

    def from_in_addr(in_addr):
        sin = _c.sockaddr_in(sin_family = AF_INET)   # PLAT sin_len
        sin.sin_addr = in_addr
        paddr = cast(pointer(sin), _c.sockaddr_ptr)
        result = instantiate(INETAddress)
        result.addr = paddr.contents
        result.addrlen = sizeof(_c.sockaddr_in)
        return result
    from_in_addr = staticmethod(from_in_addr)

    def extract_in_addr(self):
        p = cast(pointer(self.as_sockaddr_in().sin_addr), c_void_p)
        return p, sizeof(_c.in_addr)

# ____________________________________________________________

class INET6Address(IPAddress):
    family = AF_INET6
    struct = _c.sockaddr_in6
    maxlen = sizeof(struct)

    def __init__(self, host, port, flowinfo=0, scope_id=0):
        makeipaddr(host, self)
        a = self.as_sockaddr_in6()
        a.sin6_port = htons(port)
        a.sin6_flowinfo = flowinfo
        a.sin6_scope_id = scope_id

    def as_sockaddr_in6(self):
        if self.addrlen != INET6Address.maxlen:
            raise RSocketError("invalid address")
        return cast(pointer(self.addr), POINTER(_c.sockaddr_in6)).contents

    def __repr__(self):
        try:
            return '<INET6Address %s:%d %d %d>' % (self.get_host(),
                                                   self.get_port(),
                                                   self.get_flowinfo(),
                                                   self.get_scope_id())
        except SocketError:
            return '<INET6Address ?>'

    def get_port(self):
        a = self.as_sockaddr_in6()
        return ntohs(a.sin6_port)

    def get_flowinfo(self):
        a = self.as_sockaddr_in6()
        return a.sin6_flowinfo

    def get_scope_id(self):
        a = self.as_sockaddr_in6()
        return a.sin6_scope_id

    def eq(self, other):   # __eq__() is not called by RPython :-/
        return (isinstance(other, INET6Address) and
                self.get_host() == other.get_host() and
                self.get_port() == other.get_port() and
                self.get_flowinfo() == other.get_flowinfo() and
                self.get_scope_id() == other.get_scope_id())

    def as_object(self, space):
        return space.newtuple([space.wrap(self.get_host()),
                               space.wrap(self.get_port()),
                               space.wrap(self.get_flowinfo()),
                               space.wrap(self.get_scope_id())])

    def from_object(space, w_address):
        pieces_w = space.unpackiterable(w_address)
        if not (2 <= len(pieces_w) <= 4):
            raise TypeError("AF_INET6 address must be a tuple of length 2 "
                               "to 4, not %d" % len(pieces_w))
        host = space.str_w(pieces_w[0])
        port = space.int_w(pieces_w[1])
        if len(pieces_w) > 2: flowinfo = space.int_w(pieces_w[2])
        else:                 flowinfo = 0
        if len(pieces_w) > 3: scope_id = space.int_w(pieces_w[3])
        else:                 scope_id = 0
        return INET6Address(host, port, flowinfo, scope_id)
    from_object = staticmethod(from_object)

    def fill_from_object(self, space, w_address):
        # XXX a bit of code duplication
        pieces_w = space.unpackiterable(w_address)
        if not (2 <= len(pieces_w) <= 4):
            raise RSocketError("AF_INET6 address must be a tuple of length 2 "
                               "to 4, not %d" % len(pieces_w))
        port = space.int_w(pieces_w[1])
        if len(pieces_w) > 2: flowinfo = space.int_w(pieces_w[2])
        else:                 flowinfo = 0
        if len(pieces_w) > 3: scope_id = space.int_w(pieces_w[3])
        else:                 scope_id = 0
        a = self.as_sockaddr_in6()
        a.sin6_port = htons(port)
        a.sin6_flowinfo = flowinfo
        a.sin6_scope_id = scope_id

    def from_in6_addr(in6_addr):
        sin = _c.sockaddr_in6(sin6_family = AF_INET)   # PLAT sin_len
        sin.sin6_addr = in6_addr
        paddr = cast(pointer(sin), _c.sockaddr_ptr)
        result = instantiate(INET6Address)
        result.addr = paddr.contents
        result.addrlen = sizeof(_c.sockaddr_in6)
        return result
    from_in6_addr = staticmethod(from_in6_addr)

    def extract_in_addr(self):
        p = cast(pointer(self.as_sockaddr_in6().sin6_addr), c_void_p)
        return p, sizeof(_c.in6_addr)

# ____________________________________________________________

if 'AF_UNIX' in constants:
    class UNIXAddress(Address):
        family = AF_UNIX
        struct = _c.sockaddr_un
        maxlen = sizeof(struct)

        def __init__(self, path):
            sun = _c.sockaddr_un(sun_family = AF_UNIX)
            if _c.linux and path.startswith('\x00'):
                # Linux abstract namespace extension
                if len(path) > sizeof(sun.sun_path):
                    raise RSocketError("AF_UNIX path too long")
            else:
                # regular NULL-terminated string
                if len(path) >= sizeof(sun.sun_path):
                    raise RSocketError("AF_UNIX path too long")
                sun.sun_path[len(path)] = 0
            for i in range(len(path)):
                sun.sun_path[i] = ord(path[i])
            self.sun = sun
            self.addr = cast(pointer(sun), _c.sockaddr_ptr).contents
            self.addrlen = offsetof(_c.sockaddr_un, 'sun_path') + len(path)

        def as_sockaddr_un(self):
            if self.addrlen <= offsetof(_c.sockaddr_un, 'sun_path'):
                raise RSocketError("invalid address")
            return cast(pointer(self.addr), POINTER(_c.sockaddr_un)).contents

        def __repr__(self):
            try:
                return '<UNIXAddress %r>' % (self.get_path(),)
            except SocketError:
                return '<UNIXAddress ?>'

        def get_path(self):
            a = self.as_sockaddr_un()
            if _c.linux and a.sun_path[0] == 0:
                # Linux abstract namespace
                buf = copy_buffer(cast(pointer(a.sun_path), POINTER(c_char)),
                               self.addrlen - offsetof(_c.sockaddr_un,
                                                       'sun_path'))
                return buf.raw
            else:
                # regular NULL-terminated string
                return cast(pointer(a.sun_path), c_char_p).value

        def eq(self, other):   # __eq__() is not called by RPython :-/
            return (isinstance(other, UNIXAddress) and
                    self.get_path() == other.get_path())

        def as_object(self, space):
            return space.wrap(self.get_path())

        def from_object(space, w_address):
            return UNIXAddress(space.str_w(w_address))
        from_object = staticmethod(from_object)

if 'AF_NETLINK' in constants:
    class NETLINKAddress(Address):
        family = AF_NETLINK
        struct = _c.sockaddr_nl
        maxlen = sizeof(struct)

        def __init__(self, pid, groups):
            addr = _c.sockaddr_nl(nl_family = AF_NETLINK)
            addr.nl_pid = pid
            addr.nl_groups = groups
            self._addr_keepalive_netlink = addr
            self.addr = cast(pointer(addr), _c.sockaddr_ptr).contents
            self.addrlen = sizeof(addr)

        def as_sockaddr_nl(self):
            if self.addrlen != NETLINKAddress.maxlen:
                raise RSocketError("invalid address")
            return cast(pointer(self.addr), POINTER(_c.sockaddr_nl)).contents

        def get_pid(self):
            return self.as_sockaddr_nl().nl_pid

        def get_groups(self):
            return self.as_sockaddr_nl().nl_groups

        def __repr__(self):
            return '<NETLINKAddress %r>' % (self.get_pid(), self.get_groups())
        
        def as_object(self, space):
            return space.newtuple([space.wrap(self.get_pid()),
                                   space.wrap(self.get_groups())])

        def from_object(space, w_address):
            try:
                w_pid, w_groups = space.unpackiterable(w_address, 2)
            except ValueError:
                raise TypeError("AF_NETLINK address must be a tuple of length 2")
            return NETLINKAddress(space.int_w(w_pid), space.int_w(w_groups))
        from_object = staticmethod(from_object)

# ____________________________________________________________

def familyclass(family):
    return _FAMILIES.get(family, Address)
af_get = familyclass

def make_address(addrptr, addrlen, result=None):
    family = addrptr.contents.sa_family
    if result is None:
        result = instantiate(familyclass(family))
    elif result.family != family:
        raise RSocketError("address family mismatched")
    paddr = result._addr_keepalive0 = copy_buffer(cast(addrptr, POINTER(c_char)), addrlen)
    result.addr = cast(paddr, _c.sockaddr_ptr).contents
    result.addrlen = addrlen
    return result

def makeipv4addr(s_addr, result=None):
    if result is None:
        result = instantiate(INETAddress)
    elif result.family != AF_INET:
        raise RSocketError("address family mismatched")
    sin = _c.sockaddr_in(sin_family = AF_INET)   # PLAT sin_len
    sin.sin_addr.s_addr = s_addr
    paddr = cast(pointer(sin), _c.sockaddr_ptr)
    result._addr_keepalive1 = sin
    result.addr = paddr.contents
    result.addrlen = sizeof(_c.sockaddr_in)
    return result

def make_null_address(family):
    klass = familyclass(family)
    buf = create_string_buffer(klass.maxlen)
    result = instantiate(klass)
    result._addr_keepalive2 = buf
    result.addr = cast(buf, _c.sockaddr_ptr).contents
    result.addrlen = 0
    return result, len(buf)

def copy_buffer(ptr, size):
    buf = create_string_buffer(size)
    for i in range(size):
        buf[i] = ptr[i]
    return buf

def ipaddr_from_object(space, w_sockaddr):
    host = space.str_w(space.getitem(w_sockaddr, space.wrap(0)))
    addr = makeipaddr(host)
    addr.fill_from_object(space, w_sockaddr)
    return addr

# ____________________________________________________________

class RSocket(object):
    """RPython-level socket object.
    """
    _mixin_ = True        # for interp_socket.py
    fd = _c.INVALID_SOCKET
    def __init__(self, family=AF_INET, type=SOCK_STREAM, proto=0):
        """Create a new socket."""
        fd = _c.socket(family, type, proto)
        if _c.invalid_socket(fd):
            raise self.error_handler()
        # PLAT RISCOS
        self.fd = fd
        self.family = family
        self.type = type
        self.proto = proto
        self.timeout = defaults.timeout
        
    def __del__(self):
        self.close()

    if hasattr(_c, 'fcntl'):
        def _setblocking(self, block):
            delay_flag = _c.fcntl(self.fd, _c.F_GETFL, 0)
            if block:
                delay_flag &= ~_c.O_NONBLOCK
            else:
                delay_flag |= _c.O_NONBLOCK
            _c.fcntl(self.fd, _c.F_SETFL, delay_flag)
    elif hasattr(_c, 'ioctlsocket'):
        def _setblocking(self, block):
            flag = c_ulong(not block)
            _c.ioctlsocket(self.fd, _c.FIONBIO, byref(flag))

    if hasattr(_c, 'poll'):
        def _select(self, for_writing):
            """Returns 0 when reading/writing is possible,
            1 when timing out and -1 on error."""
            if self.timeout <= 0.0 or self.fd < 0:
                # blocking I/O or no socket.
                return 0
            pollfd = _c.pollfd()
            pollfd.fd = self.fd
            if for_writing:
                pollfd.events = _c.POLLOUT
            else:
                pollfd.events = _c.POLLIN
            timeout = int(self.timeout * 1000.0 + 0.5)
            n = _c.poll(byref(pollfd), 1, timeout)
            if n < 0:
                return -1
            if n == 0:
                return 1
            return 0
    else:
        # Version witout poll(): use select()
        def _select(self, for_writing):
            """Returns 0 when reading/writing is possible,
            1 when timing out and -1 on error."""
            if self.timeout <= 0.0 or self.fd < 0:
                # blocking I/O or no socket.
                return 0
            tv = _c.timeval(tv_sec=int(self.timeout),
                            tv_usec=int((self.timeout-int(self.timeout))
                                        * 1000000))
            fds = _c.fd_set(fd_count=1)
            fds.fd_array[0] = self.fd
            if for_writing:
                n = _c.select(self.fd + 1, None, byref(fds), None, byref(tv))
            else:
                n = _c.select(self.fd + 1, byref(fds), None, None, byref(tv))
            if n < 0:
                return -1
            if n == 0:
                return 1
            return 0
        
        
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
        addr, maxlen = make_null_address(self.family)
        return addr, _c.socklen_t(maxlen)

    def accept(self, SocketClass=None):
        """Wait for an incoming connection.
        Return (new socket object, client address)."""
        if SocketClass is None:
            SocketClass = RSocket
        if self._select(False) == 1:
            raise SocketTimeout
        address, addrlen = self._addrbuf()
        newfd = _c.socketaccept(self.fd, byref(address.addr), byref(addrlen))
        if _c.invalid_socket(newfd):
            raise self.error_handler()
        address.addrlen = addrlen.value
        sock = make_socket(newfd, self.family, self.type, self.proto,
                           SocketClass)
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
            res = _c.socketclose(fd)
            if res != 0:
                raise self.error_handler()

    def connect(self, address):
        """Connect the socket to a remote address."""
        res = _c.socketconnect(self.fd, byref(address.addr), address.addrlen)
        if self.timeout > 0.0:
            errno = _c.geterrno()
            if res < 0 and errno == _c.EINPROGRESS:
                timeout = self._select(True)
                if timeout == 0:
                    res = _c.socketconnect(self.fd, byref(address.addr),
                                           address.addrlen)
                elif timeout == -1:
                    raise self.error_handler()
                else:
                    raise SocketTimeout
                
        if res != 0:
            raise self.error_handler()

    def connect_ex(self, address):
        """This is like connect(address), but returns an error code (the errno
        value) instead of raising an exception when an error occurs."""
        res = _c.socketconnect(self.fd, byref(address.addr), address.addrlen)
        if self.timeout > 0.0:
            errno = _c.geterrno()
            if res < 0 and errno == _c.EINPROGRESS:
                timeout = self._select(True)
                if timeout == 0:
                    res = _c.socketconnect(self.fd, byref(address.addr),
                                           address.addrlen)
                elif timeout == -1:
                    return _c.geterrno()
                else:
                    return _c.EWOULDBLOCK
                
        if res != 0:
            return _c.geterrno()
        return res

    if hasattr(_c, 'dup'):
        def dup(self, SocketClass=None):
            if SocketClass is None:
                SocketClass = RSocket
            fd = _c.dup(self.fd)
            if fd < 0:
                raise self.error_handler()
            return make_socket(fd, self.family, self.type, self.proto,
                               SocketClass=SocketClass)
        
    def fileno(self):
        fd = self.fd
        if _c.invalid_socket(fd):
            raise RSocketError("socket already closed")
        return fd

    def getpeername(self):
        """Return the address of the remote endpoint."""
        address, addrlen = self._addrbuf()
        res = _c.socketgetpeername(self.fd, byref(address.addr),
                                            byref(addrlen))
        if res < 0:
            raise self.error_handler()
        address.addrlen = addrlen.value
        return address

    def getsockname(self):
        """Return the address of the local endpoint."""
        address, addrlen = self._addrbuf()
        res = _c.socketgetsockname(self.fd, byref(address.addr),
                                            byref(addrlen))
        if res < 0:
            raise self.error_handler()
        address.addrlen = addrlen.value
        return address

    def getsockopt(self, level, option, maxlen):
        buf = _c.create_string_buffer(maxlen)
        bufsize = _c.socklen_t()
        bufsize.value = maxlen
        res = _c.socketgetsockopt(self.fd, level, option, cast(buf, POINTER(c_char)), byref(bufsize))
        if res < 0:
            raise self.error_handler()
        return buf.raw[:bufsize.value]

    def getsockopt_int(self, level, option):
        flag = _c.c_int()
        flagsize = _c.socklen_t()
        flagsize.value = _c.sizeof(flag)
        res = _c.socketgetsockopt(self.fd, level, option,
                            byref(flag), byref(flagsize))
        if res < 0:
            raise self.error_handler()
        return flag.value

    def gettimeout(self):
        """Return the timeout of the socket. A timeout < 0 means that
        timeouts are dissabled in the socket."""
        return self.timeout
    
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
        read_bytes = -1
        timeout = self._select(False)
        if timeout == 1:
            raise SocketTimeout
        elif timeout == 0:
            buf = create_string_buffer(buffersize)
            read_bytes = _c.socketrecv(self.fd, buf, buffersize, flags)
        if read_bytes < 0:
            raise self.error_handler()
        return buf[:read_bytes]

    def recvfrom(self, buffersize, flags=0):
        """Like recv(buffersize, flags) but also return the sender's
        address."""
        read_bytes = -1
        timeout = self._select(False)
        if timeout == 1:
            raise SocketTimeout
        elif timeout == 0:
            buf = create_string_buffer(buffersize)
            address, addrlen = self._addrbuf()
            read_bytes = _c.recvfrom(self.fd, buf, buffersize, flags,
                                     byref(address.addr), byref(addrlen))
        if read_bytes < 0:
            raise self.error_handler()
        result_addrlen = addrlen.value
        if result_addrlen:
            address.addrlen = result_addrlen
        else:
            address = None
        return (buf[:read_bytes], address)

    def send(self, data, flags=0):
        """Send a data string to the socket.  For the optional flags
        argument, see the Unix manual.  Return the number of bytes
        sent; this may be less than len(data) if the network is busy."""
        res = -1
        timeout = self._select(False)
        if timeout == 1:
            raise SocketTimeout
        elif timeout == 0:
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
        res = -1
        timeout = self._select(False)
        if timeout == 1:
            raise SocketTimeout
        elif timeout == 0:
            res = _c.sendto(self.fd, data, len(data), flags,
                            byref(address.addr), address.addrlen)
        if res < 0:
            raise self.error_handler()
        return res

    def setblocking(self, block):
        if block:
            timeout = -1.0
        else:
            timeout = 0.0
        self.settimeout(timeout)

    def setsockopt(self, level, option, value):
        res = _c.socketsetsockopt(self.fd, level, option, c_char_p(value), len(value))
        if res < 0:
            raise self.error_handler()

    def setsockopt_int(self, level, option, value):
        flag = _c.c_int(value)
        res = _c.socketsetsockopt(self.fd, level, option,
                            byref(flag), _c.sizeof(flag))
        if res < 0:
            raise self.error_handler()

    def settimeout(self, timeout):
        """Set the timeout of the socket. A timeout < 0 means that
        timeouts are dissabled in the socket."""
        if timeout < 0.0:
            self.timeout = -1.0
        else:
            self.timeout = timeout
        self._setblocking(self.timeout < 0.0)
            
    def shutdown(self, how):
        """Shut down the reading side of the socket (flag == SHUT_RD), the
        writing side of the socket (flag == SHUT_WR), or both ends
        (flag == SHUT_RDWR)."""
        res = _c.socketshutdown(self.fd, how)
        if res < 0:
            raise self.error_handler()

# ____________________________________________________________

def make_socket(fd, family, type, proto, SocketClass=RSocket):
    result = instantiate(SocketClass)
    result.fd = fd
    result.family = family
    result.type = type
    result.proto = proto
    result.timeout = defaults.timeout
    return result
make_socket._annspecialcase_ = 'specialize:arg(4)'

class SocketError(Exception):
    applevelerrcls = 'error'
    def __init__(self):
        pass
    def get_msg(self):
        return ''
    def __str__(self):
        return self.get_msg()

class SocketErrorWithErrno(SocketError):
    def __init__(self, errno):
        self.errno = errno

class RSocketError(SocketError):
    def __init__(self, message):
        self.message = message
    def get_msg(self):
        return self.message

class CSocketError(SocketErrorWithErrno):
    def get_msg(self):
        return _c.socket_strerror(self.errno)

def last_error():
    return CSocketError(_c.geterrno())

class GAIError(SocketErrorWithErrno):
    applevelerrcls = 'gaierror'
    def get_msg(self):
        return _c.gai_strerror(self.errno)

class HSocketError(SocketError):
    applevelerrcls = 'herror'
    def __init__(self, host):
        self.host = host
        # XXX h_errno is not easily available, and hstrerror() is
        # marked as deprecated in the Linux man pages
    def get_msg(self):
        return "host lookup failed: '%s'" % (self.host,)

class SocketTimeout(SocketError):
    applevelerrcls = 'timeout'
    def get_msg(self):
        return 'timed out'

class Defaults:
    timeout = -1.0 # Blocking
defaults = Defaults()


# ____________________________________________________________
if 'AF_UNIX' not in constants or AF_UNIX is None:
    socketpair_default_family = AF_INET
else:
    socketpair_default_family = AF_UNIX

def socketpair(family=socketpair_default_family, type=SOCK_STREAM, proto=0,
               SocketClass=RSocket):
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
    return (make_socket(result[0], family, type, proto, SocketClass),
            make_socket(result[1], family, type, proto, SocketClass))

def fromfd(fd, family, type, proto=0, SocketClass=RSocket):
    # Dup the fd so it and the socket can be closed independently
    fd = _c.dup(fd)
    if fd < 0:
        raise last_error()
    return make_socket(fd, family, type, proto, SocketClass)

def getdefaulttimeout():
    return defaults.timeout

def gethostname():
    buf = create_string_buffer(1024)
    res = _c.gethostname(buf, sizeof(buf)-1)
    if res < 0:
        raise last_error()
    buf[sizeof(buf)-1] = '\x00'
    return buf.value

def gethostbyname(name):
    # this is explicitly not working with IPv6, because the docs say it
    # should not.  Just use makeipaddr(name) for an IPv6-friendly version...
    result = instantiate(INETAddress)
    makeipaddr(name, result)
    return result

def gethost_common(hostname, hostent, addr=None):
    if not hostent:
        raise HSocketError(hostname)
    family = hostent.contents.h_addrtype
    if addr is not None and addr.family != family:
        raise CSocketError(_c.EAFNOSUPPORT)

    aliases = []
    h_aliases = hostent.contents.h_aliases
    if h_aliases:   # h_aliases can be NULL, according to SF #1511317
        i = 0
        alias = h_aliases[0]
        while alias is not None:
            aliases.append(alias)
            i += 1
            alias = h_aliases[i]

    address_list = []
    h_addr_list = hostent.contents.h_addr_list
    i = 0
    paddr = h_addr_list[0]
    while paddr:
        if family == AF_INET:
            p = cast(paddr, POINTER(_c.in_addr))
            addr = INETAddress.from_in_addr(p.contents)
        elif AF_INET6 is not None and family == AF_INET6:
            p = cast(paddr, POINTER(_c.in6_addr))
            addr = INET6Address.from_in6_addr(p.contents)
        else:
            raise RSocketError("unknown address family")
        address_list.append(addr)
        i += 1
        paddr = h_addr_list[i]
    return (hostent.contents.h_name, aliases, address_list)

def gethostbyname_ex(name):
    # XXX use gethostbyname_r() if available, and/or use locks if not
    addr = gethostbyname(name)
    hostent = _c.gethostbyname(name)
    return gethost_common(name, hostent, addr)

def gethostbyaddr(ip):
    # XXX use gethostbyaddr_r() if available, and/or use locks if not
    addr = makeipaddr(ip)
    p, size = addr.extract_in_addr()
    hostent =_c.gethostbyaddr(p, size, addr.family)
    return gethost_common(ip, hostent, addr)

def getaddrinfo(host, port_or_service,
                family=AF_UNSPEC, socktype=0, proto=0, flags=0,
                address_to_fill=None):
    # port_or_service is a string, not an int (but try str(port_number)).
    assert port_or_service is None or isinstance(port_or_service, str)
    hints = _c.addrinfo(ai_family   = family,
                        ai_socktype = socktype,
                        ai_protocol = proto,
                        ai_flags    = flags)
    # XXX need to lock around getaddrinfo() calls?
    res = _c.addrinfo_ptr()
    error = _c.getaddrinfo(host, port_or_service, byref(hints), byref(res))
    if error:
        raise GAIError(error)
    try:
        result = []
        p = res
        while p:
            info = p.contents
            addr = make_address(info.ai_addr, info.ai_addrlen, address_to_fill)
            canonname = info.ai_canonname
            if canonname is None:
                canonname = ""
            result.append((info.ai_family,
                           info.ai_socktype,
                           info.ai_protocol,
                           canonname,
                           addr))
            p = info.ai_next
    finally:
        _c.freeaddrinfo(res)
    return result

def getservbyname(name, proto=None):
    servent = _c.getservbyname(name, proto)
    if not servent:
        raise RSocketError("service/proto not found")
    return _c.ntohs(servent.contents.s_port)

def getservbyport(port, proto=None):
    servent = _c.getservbyport(htons(port), proto)
    if not servent:
        raise RSocketError("port/proto not found")
    return servent.contents.s_name

def getprotobyname(name):
    protoent = _c.getprotobyname(name)
    if not protoent:
        raise RSocketError("protocol not found")
    return protoent.contents.p_proto

def getnameinfo(addr, flags):
    host = create_string_buffer(NI_MAXHOST)
    serv = create_string_buffer(NI_MAXSERV)
    error =_c.getnameinfo(pointer(addr.addr), addr.addrlen,
                          host, len(host),
                          serv, len(serv), flags)
    if error:
        raise GAIError(error)
    return host.value, serv.value

if hasattr(_c, 'inet_aton'):
    def inet_aton(ip):
        "IPv4 dotted string -> packed 32-bits string"
        buf = create_string_buffer(sizeof(_c.in_addr))
        if _c.inet_aton(ip, cast(buf, POINTER(_c.in_addr))):
            return buf.raw
        else:
            raise RSocketError("illegal IP address string passed to inet_aton")
else:
    def inet_aton(ip):
        "IPv4 dotted string -> packed 32-bits string"
        if ip == "255.255.255.255":
            return "\xff\xff\xff\xff"
        packed_addr = _c.inet_addr(ip)
        if _c.c_long(packed_addr).value == INADDR_NONE:
            raise RSocketError("illegal IP address string passed to inet_aton")
        buf = copy_buffer(cast(pointer(c_ulong(packed_addr)),
                               POINTER(c_char)), 4)
        return buf.raw

def inet_ntoa(packed):
    "packet 32-bits string -> IPv4 dotted string"
    if len(packed) != sizeof(_c.in_addr):
        raise RSocketError("packed IP wrong length for inet_ntoa")
    buf = create_string_buffer(sizeof(_c.in_addr))
    buf.raw = packed
    return _c.inet_ntoa(cast(buf, POINTER(_c.in_addr)).contents)

if hasattr(_c, 'inet_pton'):
    def inet_pton(family, ip):
        "human-readable string -> packed string"
        if family == AF_INET:
            size = sizeof(_c.in_addr)
        elif AF_INET6 is not None and family == AF_INET6:
            size = sizeof(_c.in6_addr)
        else:
            raise RSocketError("unknown address family")
        buf = create_string_buffer(size)
        res = _c.inet_pton(family, ip, cast(buf, c_void_p))
        if res < 0:
            raise last_error()
        elif res == 0:
            raise RSocketError("illegal IP address string passed to inet_pton")
        else:
            return buf.raw

if hasattr(_c, 'inet_ntop'):
    def inet_ntop(family, packed):
        "packed string -> human-readable string"
        if family == AF_INET:
            srcsize = sizeof(_c.in_addr)
            dstsize = _c.INET_ADDRSTRLEN
        elif AF_INET6 is not None and family == AF_INET6:
            srcsize = sizeof(_c.in6_addr)
            dstsize = _c.INET6_ADDRSTRLEN
        else:
            raise RSocketError("unknown address family")
        if len(packed) != srcsize:
            raise ValueError("packed IP wrong length for inet_ntop")
        srcbuf = create_string_buffer(srcsize)
        srcbuf.raw = packed
        dstbuf = create_string_buffer(dstsize)
        res = _c.inet_ntop(family, cast(srcbuf, c_void_p), dstbuf, dstsize)
        if res is None:
            raise last_error()
        return res

def setdefaulttimeout(timeout):
    if timeout < 0.0:
        timeout = -1.0
    defaults.timeout = timeout

# _______________________________________________________________
#
# Patch module, for platforms without getaddrinfo / getnameinfo
#

if not getattr(_c, 'getaddrinfo', None):
    from pypy.rlib.getaddrinfo import getaddrinfo
    from pypy.rlib.getaddrinfo import GAIError_getmsg
    GAIError.get_msg = GAIError_getmsg

if not getattr(_c, 'getnameinfo', None):
    from pypy.rlib.getnameinfo import getnameinfo
    from pypy.rlib.getnameinfo import NI_NUMERICHOST, NI_NUMERICSERV

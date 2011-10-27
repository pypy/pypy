from __future__ import with_statement
"""
An RPython implementation of sockets based on rffi.
Note that the interface has to be slightly different - this is not
a drop-in replacement for the 'socket' module.
"""

# Known missing features:
#
#   - address families other than AF_INET, AF_INET6, AF_UNIX, AF_PACKET
#   - AF_PACKET is only supported on Linux
#   - methods makefile(),
#   - SSL
#
# It's unclear if makefile() and SSL support belong here or only as
# app-level code for PyPy.

from pypy.rlib.objectmodel import instantiate, keepalive_until_here
from pypy.rlib import _rsocket_rffi as _c
from pypy.rlib.rarithmetic import intmask
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.lltypesystem.rffi import sizeof, offsetof

def mallocbuf(buffersize):
    return lltype.malloc(rffi.CCHARP.TO, buffersize, flavor='raw')


constants = _c.constants
locals().update(constants) # Define constants from _c

if _c.WIN32:
    from pypy.rlib import rwin32
    def rsocket_startup():
        wsadata = lltype.malloc(_c.WSAData, flavor='raw', zero=True)
        res = _c.WSAStartup(1, wsadata)
        lltype.free(wsadata, flavor='raw')
        assert res == 0
else:
    def rsocket_startup():
        pass
 
 
def ntohs(x):
    return rffi.cast(lltype.Signed, _c.ntohs(x))

def ntohl(x):
    # accepts and returns an Unsigned
    return rffi.cast(lltype.Unsigned, _c.ntohl(x))

def htons(x):
    return rffi.cast(lltype.Signed, _c.htons(x))

def htonl(x):
    # accepts and returns an Unsigned
    return rffi.cast(lltype.Unsigned, _c.htonl(x))


_FAMILIES = {}

class Address(object):
    """The base class for RPython-level objects representing addresses.
    Fields:  addr    - a _c.sockaddr_ptr (memory owned by the Address instance)
             addrlen - size used within 'addr'
    """
    class __metaclass__(type):
        def __new__(cls, name, bases, dict):
            family = dict.get('family')
            A = type.__new__(cls, name, bases, dict)
            if family is not None:
                _FAMILIES[family] = A
            return A

    # default uninitialized value: NULL ptr
    addr_p = lltype.nullptr(_c.sockaddr_ptr.TO)

    def __init__(self, addr, addrlen):
        self.addr_p = addr
        self.addrlen = addrlen

    def __del__(self):
        if self.addr_p:
            lltype.free(self.addr_p, flavor='raw')

    def setdata(self, addr, addrlen):
        # initialize self.addr and self.addrlen.  'addr' can be a different
        # pointer type than exactly sockaddr_ptr, and we cast it for you.
        assert not self.addr_p
        self.addr_p = rffi.cast(_c.sockaddr_ptr, addr)
        self.addrlen = addrlen
    setdata._annspecialcase_ = 'specialize:ll'

    # the following slightly strange interface is needed to manipulate
    # what self.addr_p points to in a safe way.  The problem is that
    # after inlining we might end up with operations that looks like:
    #    addr = self.addr_p
    #    <self is freed here, and its __del__ calls lltype.free()>
    #    read from addr
    # To prevent this we have to insert a keepalive after the last
    # use of 'addr'.  The interface to do that is called lock()/unlock()
    # because it strongly reminds callers not to forget unlock().
    #
    def lock(self, TYPE=_c.sockaddr):
        """Return self.addr_p, cast as a pointer to TYPE.  Must call unlock()!
        """
        return rffi.cast(lltype.Ptr(TYPE), self.addr_p)
    lock._annspecialcase_ = 'specialize:ll'

    def unlock(self):
        """To call after we're done with the pointer returned by lock().
        Note that locking and unlocking costs nothing at run-time.
        """
        keepalive_until_here(self)

    def as_object(self, fd, space):
        """Convert the address to an app-level object."""
        # If we don't know the address family, don't raise an
        # exception -- return it as a tuple.
        addr = self.lock()
        family = rffi.cast(lltype.Signed, addr.c_sa_family)
        datalen = self.addrlen - offsetof(_c.sockaddr, 'c_sa_data')
        rawdata = ''.join([addr.c_sa_data[i] for i in range(datalen)])
        self.unlock()
        return space.newtuple([space.wrap(family),
                               space.wrap(rawdata)])

    def from_object(space, w_address):
        """Convert an app-level object to an Address."""
        # It's a static method but it's overridden and must be called
        # on the correct subclass.
        raise RSocketError("unknown address family")
    from_object = staticmethod(from_object)

    @staticmethod
    def _check_port(space, port):
        from pypy.interpreter.error import OperationError
        if port < 0 or port > 0xffff:
            raise OperationError(space.w_ValueError, space.wrap(
                "port must be 0-65535."))

    def fill_from_object(self, space, w_address):
        """ Purely abstract
        """
        raise NotImplementedError

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
            raise RSocketError("wildcard resolved to multiple addresses")
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

    def lock_in_addr(self):
        """ Purely abstract
        """
        raise NotImplementedError

# ____________________________________________________________

if 'AF_PACKET' in constants:
    class PacketAddress(Address):
        family = AF_PACKET
        struct = _c.sockaddr_ll
        maxlen = minlen = sizeof(struct)

        def get_ifname(self, fd):
            a = self.lock(_c.sockaddr_ll)
            p = lltype.malloc(_c.ifreq, flavor='raw')
            rffi.setintfield(p, 'c_ifr_ifindex',
                             rffi.getintfield(a, 'c_sll_ifindex'))
            if (_c.ioctl(fd, _c.SIOCGIFNAME, p) == 0):
                # eh, the iface name is a constant length array
                i = 0
                d = []
                while p.c_ifr_name[i] != '\x00' and i < len(p.c_ifr_name):
                    d.append(p.c_ifr_name[i])
                    i += 1
                ifname = ''.join(d)
            else:
                ifname = ""
            lltype.free(p, flavor='raw')
            self.unlock()
            return ifname

        def get_protocol(self):
            a = self.lock(_c.sockaddr_ll)
            res = ntohs(rffi.getintfield(a, 'c_sll_protocol'))
            self.unlock()
            return res

        def get_pkttype(self):
            a = self.lock(_c.sockaddr_ll)
            res = rffi.getintfield(a, 'c_sll_pkttype')
            self.unlock()
            return res

        def get_hatype(self):
            a = self.lock(_c.sockaddr_ll)
            res = bool(rffi.getintfield(a, 'c_sll_hatype'))
            self.unlock()
            return res

        def get_addr(self):
            a = self.lock(_c.sockaddr_ll)
            lgt = rffi.getintfield(a, 'c_sll_halen')
            d = []
            for i in range(lgt):
                d.append(a.c_sll_addr[i])
            res = "".join(d)
            self.unlock()
            return res

        def as_object(self, fd, space):
            return space.newtuple([space.wrap(self.get_ifname(fd)),
                                   space.wrap(self.get_protocol()),
                                   space.wrap(self.get_pkttype()),
                                   space.wrap(self.get_hatype()),
                                   space.wrap(self.get_addr())])

class INETAddress(IPAddress):
    family = AF_INET
    struct = _c.sockaddr_in
    maxlen = minlen = sizeof(struct)

    def __init__(self, host, port):
        makeipaddr(host, self)
        a = self.lock(_c.sockaddr_in)
        rffi.setintfield(a, 'c_sin_port', htons(port))
        self.unlock()

    def __repr__(self):
        try:
            return '<INETAddress %s:%d>' % (self.get_host(), self.get_port())
        except SocketError:
            return '<INETAddress ?>'

    def get_port(self):
        a = self.lock(_c.sockaddr_in)
        port = ntohs(a.c_sin_port)
        self.unlock()
        return port

    def eq(self, other):   # __eq__() is not called by RPython :-/
        return (isinstance(other, INETAddress) and
                self.get_host() == other.get_host() and
                self.get_port() == other.get_port())

    def as_object(self, fd, space):
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
        Address._check_port(space, port)
        return INETAddress(host, port)
    from_object = staticmethod(from_object)

    def fill_from_object(self, space, w_address):
        # XXX a bit of code duplication
        from pypy.interpreter.error import OperationError
        _, w_port = space.unpackiterable(w_address, 2)
        port = space.int_w(w_port)
        self._check_port(space, port)
        a = self.lock(_c.sockaddr_in)
        rffi.setintfield(a, 'c_sin_port', htons(port))
        self.unlock()

    def from_in_addr(in_addr):
        result = instantiate(INETAddress)
        # store the malloc'ed data into 'result' as soon as possible
        # to avoid leaks if an exception occurs inbetween
        sin = lltype.malloc(_c.sockaddr_in, flavor='raw', zero=True)
        result.setdata(sin, sizeof(_c.sockaddr_in))
        # PLAT sin_len
        rffi.setintfield(sin, 'c_sin_family', AF_INET)
        rffi.structcopy(sin.c_sin_addr, in_addr)
        return result
    from_in_addr = staticmethod(from_in_addr)

    def lock_in_addr(self):
        a = self.lock(_c.sockaddr_in)
        p = rffi.cast(rffi.VOIDP, a.c_sin_addr)
        return p, sizeof(_c.in_addr)

# ____________________________________________________________

class INET6Address(IPAddress):
    family = AF_INET6
    struct = _c.sockaddr_in6
    maxlen = minlen = sizeof(struct)

    def __init__(self, host, port, flowinfo=0, scope_id=0):
        makeipaddr(host, self)
        a = self.lock(_c.sockaddr_in6)
        rffi.setintfield(a, 'c_sin6_port', htons(port))
        rffi.setintfield(a, 'c_sin6_flowinfo', flowinfo)
        rffi.setintfield(a, 'c_sin6_scope_id', scope_id)
        self.unlock()

    def __repr__(self):
        try:
            return '<INET6Address %s:%d %d %d>' % (self.get_host(),
                                                   self.get_port(),
                                                   self.get_flowinfo(),
                                                   self.get_scope_id())
        except SocketError:
            return '<INET6Address ?>'

    def get_port(self):
        a = self.lock(_c.sockaddr_in6)
        port = ntohs(a.c_sin6_port)
        self.unlock()
        return port

    def get_flowinfo(self):
        a = self.lock(_c.sockaddr_in6)
        flowinfo = a.c_sin6_flowinfo
        self.unlock()
        return rffi.cast(lltype.Unsigned, flowinfo)

    def get_scope_id(self):
        a = self.lock(_c.sockaddr_in6)
        scope_id = a.c_sin6_scope_id
        self.unlock()
        return rffi.cast(lltype.Unsigned, scope_id)

    def eq(self, other):   # __eq__() is not called by RPython :-/
        return (isinstance(other, INET6Address) and
                self.get_host() == other.get_host() and
                self.get_port() == other.get_port() and
                self.get_flowinfo() == other.get_flowinfo() and
                self.get_scope_id() == other.get_scope_id())

    def as_object(self, fd, space):
        return space.newtuple([space.wrap(self.get_host()),
                               space.wrap(self.get_port()),
                               space.wrap(self.get_flowinfo()),
                               space.wrap(self.get_scope_id())])

    def from_object(space, w_address):
        from pypy.interpreter.error import OperationError
        pieces_w = space.unpackiterable(w_address)
        if not (2 <= len(pieces_w) <= 4):
            raise TypeError("AF_INET6 address must be a tuple of length 2 "
                               "to 4, not %d" % len(pieces_w))
        host = space.str_w(pieces_w[0])
        port = space.int_w(pieces_w[1])
        Address._check_port(space, port)
        if len(pieces_w) > 2: flowinfo = space.uint_w(pieces_w[2])
        else:                 flowinfo = 0
        if len(pieces_w) > 3: scope_id = space.uint_w(pieces_w[3])
        else:                 scope_id = 0
        return INET6Address(host, port, flowinfo, scope_id)
    from_object = staticmethod(from_object)

    def fill_from_object(self, space, w_address):
        # XXX a bit of code duplication
        from pypy.interpreter.error import OperationError
        pieces_w = space.unpackiterable(w_address)
        if not (2 <= len(pieces_w) <= 4):
            raise RSocketError("AF_INET6 address must be a tuple of length 2 "
                               "to 4, not %d" % len(pieces_w))
        port = space.int_w(pieces_w[1])
        self._check_port(space, port)
        if len(pieces_w) > 2: flowinfo = space.uint_w(pieces_w[2])
        else:                 flowinfo = 0
        if len(pieces_w) > 3: scope_id = space.uint_w(pieces_w[3])
        else:                 scope_id = 0
        a = self.lock(_c.sockaddr_in6)
        rffi.setintfield(a, 'c_sin6_port', htons(port))
        rffi.setintfield(a, 'c_sin6_flowinfo', flowinfo)
        rffi.setintfield(a, 'c_sin6_scope_id', scope_id)
        self.unlock()

    def from_in6_addr(in6_addr):
        result = instantiate(INET6Address)
        # store the malloc'ed data into 'result' as soon as possible
        # to avoid leaks if an exception occurs inbetween
        sin = lltype.malloc(_c.sockaddr_in6, flavor='raw', zero=True)
        result.setdata(sin, sizeof(_c.sockaddr_in6))
        rffi.setintfield(sin, 'c_sin6_family', AF_INET)
        rffi.structcopy(sin.c_sin6_addr, in6_addr)
        return result
    from_in6_addr = staticmethod(from_in6_addr)

    def lock_in_addr(self):
        a = self.lock(_c.sockaddr_in6)
        p = rffi.cast(rffi.VOIDP, a.c_sin6_addr)
        return p, sizeof(_c.in6_addr)

# ____________________________________________________________

if 'AF_UNIX' in constants:
    class UNIXAddress(Address):
        family = AF_UNIX
        struct = _c.sockaddr_un
        minlen = offsetof(_c.sockaddr_un, 'c_sun_path')
        maxlen = sizeof(struct)

        def __init__(self, path):
            sun = lltype.malloc(_c.sockaddr_un, flavor='raw', zero=True)
            baseofs = offsetof(_c.sockaddr_un, 'c_sun_path')
            self.setdata(sun, baseofs + len(path))
            rffi.setintfield(sun, 'c_sun_family', AF_UNIX)
            if _c.linux and path.startswith('\x00'):
                # Linux abstract namespace extension
                if len(path) > sizeof(_c.sockaddr_un.c_sun_path):
                    raise RSocketError("AF_UNIX path too long")
            else:
                # regular NULL-terminated string
                if len(path) >= sizeof(_c.sockaddr_un.c_sun_path):
                    raise RSocketError("AF_UNIX path too long")
                sun.c_sun_path[len(path)] = '\x00'
            for i in range(len(path)):
                sun.c_sun_path[i] = path[i]

        def __repr__(self):
            try:
                return '<UNIXAddress %r>' % (self.get_path(),)
            except SocketError:
                return '<UNIXAddress ?>'

        def get_path(self):
            a = self.lock(_c.sockaddr_un)
            maxlength = self.addrlen - offsetof(_c.sockaddr_un, 'c_sun_path')
            if _c.linux and maxlength > 0 and a.c_sun_path[0] == '\x00':
                # Linux abstract namespace
                length = maxlength
            else:
                # regular NULL-terminated string
                length = 0
                while length < maxlength and a.c_sun_path[length] != '\x00':
                    length += 1
            result = ''.join([a.c_sun_path[i] for i in range(length)])
            self.unlock()
            return result

        def eq(self, other):   # __eq__() is not called by RPython :-/
            return (isinstance(other, UNIXAddress) and
                    self.get_path() == other.get_path())

        def as_object(self, fd, space):
            return space.wrap(self.get_path())

        def from_object(space, w_address):
            return UNIXAddress(space.str_w(w_address))
        from_object = staticmethod(from_object)

if 'AF_NETLINK' in constants:
    class NETLINKAddress(Address):
        family = AF_NETLINK
        struct = _c.sockaddr_nl
        maxlen = minlen = sizeof(struct)

        def __init__(self, pid, groups):
            addr = lltype.malloc(_c.sockaddr_nl, flavor='raw', zero=True)
            self.setdata(addr, NETLINKAddress.maxlen)
            rffi.setintfield(addr, 'c_nl_family', AF_NETLINK)
            rffi.setintfield(addr, 'c_nl_pid', pid)
            rffi.setintfield(addr, 'c_nl_groups', groups)

        def get_pid(self):
            a = self.lock(_c.sockaddr_nl)
            pid = a.c_nl_pid
            self.unlock()
            return rffi.cast(lltype.Unsigned, pid)

        def get_groups(self):
            a = self.lock(_c.sockaddr_nl)
            groups = a.c_nl_groups
            self.unlock()
            return rffi.cast(lltype.Unsigned, groups)

        def __repr__(self):
            return '<NETLINKAddress %r>' % (self.get_pid(), self.get_groups())
        
        def as_object(self, fd, space):
            return space.newtuple([space.wrap(self.get_pid()),
                                   space.wrap(self.get_groups())])

        def from_object(space, w_address):
            try:
                w_pid, w_groups = space.unpackiterable(w_address, 2)
            except ValueError:
                raise TypeError("AF_NETLINK address must be a tuple of length 2")
            return NETLINKAddress(space.uint_w(w_pid), space.uint_w(w_groups))
        from_object = staticmethod(from_object)

# ____________________________________________________________

def familyclass(family):
    return _FAMILIES.get(family, Address)
af_get = familyclass

def make_address(addrptr, addrlen, result=None):
    family = rffi.cast(lltype.Signed, addrptr.c_sa_family)
    if result is None:
        result = instantiate(familyclass(family))
    elif result.family != family:
        raise RSocketError("address family mismatched")
    # copy into a new buffer the address that 'addrptr' points to
    addrlen = rffi.cast(lltype.Signed, addrlen)
    buf = lltype.malloc(rffi.CCHARP.TO, addrlen, flavor='raw')
    src = rffi.cast(rffi.CCHARP, addrptr)
    for i in range(addrlen):
        buf[i] = src[i]
    result.setdata(buf, addrlen)
    return result

def makeipv4addr(s_addr, result=None):
    if result is None:
        result = instantiate(INETAddress)
    elif result.family != AF_INET:
        raise RSocketError("address family mismatched")
    sin = lltype.malloc(_c.sockaddr_in, flavor='raw', zero=True)
    result.setdata(sin, sizeof(_c.sockaddr_in))
    rffi.setintfield(sin, 'c_sin_family', AF_INET)   # PLAT sin_len
    rffi.setintfield(sin.c_sin_addr, 'c_s_addr', s_addr)
    return result

def make_null_address(family):
    klass = familyclass(family)
    result = instantiate(klass)
    buf = lltype.malloc(rffi.CCHARP.TO, klass.maxlen, flavor='raw', zero=True)
    # Initialize the family to the correct value.  Avoids surprizes on
    # Windows when calling a function that unexpectedly does not set
    # the output address (e.g. recvfrom() on a connected IPv4 socket).
    rffi.setintfield(rffi.cast(_c.sockaddr_ptr, buf), 'c_sa_family', family)
    result.setdata(buf, 0)
    return result, klass.maxlen

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
        fd = self.fd
        if fd != _c.INVALID_SOCKET:
            self.fd = _c.INVALID_SOCKET
            _c.socketclose(fd)

    if hasattr(_c, 'fcntl'):
        def _setblocking(self, block):
            delay_flag = intmask(_c.fcntl(self.fd, _c.F_GETFL, 0))
            if block:
                delay_flag &= ~_c.O_NONBLOCK
            else:
                delay_flag |= _c.O_NONBLOCK
            _c.fcntl(self.fd, _c.F_SETFL, delay_flag)
    elif hasattr(_c, 'ioctlsocket'):
        def _setblocking(self, block):
            flag = lltype.malloc(rffi.ULONGP.TO, 1, flavor='raw')
            flag[0] = rffi.cast(rffi.ULONG, not block)
            _c.ioctlsocket(self.fd, _c.FIONBIO, flag)
            lltype.free(flag, flavor='raw')

    if hasattr(_c, 'poll') and not _c.poll_may_be_broken:
        def _select(self, for_writing):
            """Returns 0 when reading/writing is possible,
            1 when timing out and -1 on error."""
            if self.timeout <= 0.0 or self.fd == _c.INVALID_SOCKET:
                # blocking I/O or no socket.
                return 0
            pollfd = rffi.make(_c.pollfd)
            try:
                rffi.setintfield(pollfd, 'c_fd', self.fd)
                if for_writing:
                    rffi.setintfield(pollfd, 'c_events', _c.POLLOUT)
                else:
                    rffi.setintfield(pollfd, 'c_events', _c.POLLIN)
                timeout = int(self.timeout * 1000.0 + 0.5)
                n = _c.poll(rffi.cast(lltype.Ptr(_c.pollfdarray), pollfd),
                            1, timeout)
            finally:
                lltype.free(pollfd, flavor='raw')
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
            timeout = self.timeout
            if timeout <= 0.0 or self.fd == _c.INVALID_SOCKET:
                # blocking I/O or no socket.
                return 0
            tv = rffi.make(_c.timeval)
            rffi.setintfield(tv, 'c_tv_sec', int(timeout))
            rffi.setintfield(tv, 'c_tv_usec', int((timeout-int(timeout))
                                                  * 1000000))
            fds = lltype.malloc(_c.fd_set.TO, flavor='raw')
            _c.FD_ZERO(fds)
            _c.FD_SET(self.fd, fds)
            null = lltype.nullptr(_c.fd_set.TO)
            if for_writing:
                n = _c.select(self.fd + 1, null, fds, null, tv)
            else:
                n = _c.select(self.fd + 1, fds, null, null, tv)
            lltype.free(fds, flavor='raw')
            lltype.free(tv, flavor='raw')
            if n < 0:
                return -1
            if n == 0:
                return 1
            return 0
        
        
    def error_handler(self):
        return last_error()

    # convert an Address into an app-level object
    def addr_as_object(self, space, address):
        return address.as_object(self.fd, space)

    # convert an app-level object into an Address
    # based on the current socket's family
    def addr_from_object(self, space, w_address):
        return af_get(self.family).from_object(space, w_address)

    # build a null address object, ready to be used as output argument to
    # C functions that return an address.  It must be unlock()ed after you
    # are done using addr_p.
    def _addrbuf(self):
        addr, maxlen = make_null_address(self.family)
        addrlen_p = lltype.malloc(_c.socklen_t_ptr.TO, flavor='raw')
        addrlen_p[0] = rffi.cast(_c.socklen_t, maxlen)
        return addr, addr.addr_p, addrlen_p

    def accept(self, SocketClass=None):
        """Wait for an incoming connection.
        Return (new socket object, client address)."""
        if SocketClass is None:
            SocketClass = RSocket
        if self._select(False) == 1:
            raise SocketTimeout
        address, addr_p, addrlen_p = self._addrbuf()
        try:
            newfd = _c.socketaccept(self.fd, addr_p, addrlen_p)
            addrlen = addrlen_p[0]
        finally:
            lltype.free(addrlen_p, flavor='raw')
            address.unlock()
        if _c.invalid_socket(newfd):
            raise self.error_handler()
        address.addrlen = rffi.cast(lltype.Signed, addrlen)
        sock = make_socket(newfd, self.family, self.type, self.proto,
                           SocketClass)
        return (sock, address)

    def bind(self, address):
        """Bind the socket to a local address."""
        addr = address.lock()
        res = _c.socketbind(self.fd, addr, address.addrlen)
        address.unlock()
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

    if _c.WIN32:
        def _connect(self, address):
            """Connect the socket to a remote address."""
            addr = address.lock()
            res = _c.socketconnect(self.fd, addr, address.addrlen)
            address.unlock()
            errno = _c.geterrno()
            timeout = self.timeout
            if timeout > 0.0 and res < 0 and errno == _c.EWOULDBLOCK:
                tv = rffi.make(_c.timeval)
                rffi.setintfield(tv, 'c_tv_sec', int(timeout))
                rffi.setintfield(tv, 'c_tv_usec',
                                 int((timeout-int(timeout)) * 1000000))
                fds = lltype.malloc(_c.fd_set.TO, flavor='raw')
                _c.FD_ZERO(fds)
                _c.FD_SET(self.fd, fds)
                fds_exc = lltype.malloc(_c.fd_set.TO, flavor='raw')
                _c.FD_ZERO(fds_exc)
                _c.FD_SET(self.fd, fds_exc)
                null = lltype.nullptr(_c.fd_set.TO)

                try:
                    n = _c.select(self.fd + 1, null, fds, fds_exc, tv)

                    if n > 0:
                        if _c.FD_ISSET(self.fd, fds):
                            # socket writable == connected
                            return (0, False)
                        else:
                            # per MS docs, call getsockopt() to get error
                            assert _c.FD_ISSET(self.fd, fds_exc)
                            return (self.getsockopt_int(_c.SOL_SOCKET,
                                                        _c.SO_ERROR), False)
                    elif n == 0:
                        return (_c.EWOULDBLOCK, True)
                    else:
                        return (_c.geterrno(), False)

                finally:
                    lltype.free(fds, flavor='raw')
                    lltype.free(fds_exc, flavor='raw')
                    lltype.free(tv, flavor='raw')

            if res == 0:
                errno = 0
            return (errno, False)
    else:
        def _connect(self, address):
            """Connect the socket to a remote address."""
            addr = address.lock()
            res = _c.socketconnect(self.fd, addr, address.addrlen)
            address.unlock()
            errno = _c.geterrno()
            if self.timeout > 0.0 and res < 0 and errno == _c.EINPROGRESS:
                timeout = self._select(True)
                errno = _c.geterrno()
                if timeout == 0:
                    addr = address.lock()
                    res = _c.socketconnect(self.fd, addr, address.addrlen)
                    address.unlock()
                    if res < 0:
                        errno = _c.geterrno()
                        if errno == _c.EISCONN:
                            res = 0
                elif timeout == -1:
                    return (errno, False)
                else:
                    return (_c.EWOULDBLOCK, True)

            if res == 0:
                errno = 0
            return (errno, False)
        
    def connect(self, address):
        """Connect the socket to a remote address."""
        err, timeout = self._connect(address)
        if timeout:
            raise SocketTimeout
        if err:
            raise CSocketError(err)
        
    def connect_ex(self, address):
        """This is like connect(address), but returns an error code (the errno
        value) instead of raising an exception when an error occurs."""
        err, timeout = self._connect(address)
        return err

    if hasattr(_c, 'dup'):
        def dup(self, SocketClass=None):
            if SocketClass is None:
                SocketClass = RSocket
            fd = _c.dup(self.fd)
            if fd < 0:
                raise self.error_handler()
            return make_socket(fd, self.family, self.type, self.proto,
                               SocketClass=SocketClass)
        
    def getpeername(self):
        """Return the address of the remote endpoint."""
        address, addr_p, addrlen_p = self._addrbuf()
        try:
            res = _c.socketgetpeername(self.fd, addr_p, addrlen_p)
            addrlen = addrlen_p[0]
        finally:
            lltype.free(addrlen_p, flavor='raw')
            address.unlock()
        if res < 0:
            raise self.error_handler()
        address.addrlen = rffi.cast(lltype.Signed, addrlen)
        return address

    def getsockname(self):
        """Return the address of the local endpoint."""
        address, addr_p, addrlen_p = self._addrbuf()
        try:
            res = _c.socketgetsockname(self.fd, addr_p, addrlen_p)
            addrlen = addrlen_p[0]
        finally:
            lltype.free(addrlen_p, flavor='raw')
            address.unlock()
        if res < 0:
            raise self.error_handler()
        address.addrlen = rffi.cast(lltype.Signed, addrlen)
        return address

    def getsockopt(self, level, option, maxlen):
        buf = mallocbuf(maxlen)
        try:
            bufsize_p = lltype.malloc(_c.socklen_t_ptr.TO, flavor='raw')
            try:
                bufsize_p[0] = rffi.cast(_c.socklen_t, maxlen)
                res = _c.socketgetsockopt(self.fd, level, option,
                                          buf, bufsize_p)
                if res < 0:
                    raise self.error_handler()
                size = rffi.cast(lltype.Signed, bufsize_p[0])
                assert size >= 0       # socklen_t is signed on Windows
                result = ''.join([buf[i] for i in range(size)])
            finally:
                lltype.free(bufsize_p, flavor='raw')
        finally:
            lltype.free(buf, flavor='raw')
        return result

    def getsockopt_int(self, level, option):
        flag_p = lltype.malloc(rffi.INTP.TO, 1, flavor='raw')
        try:
            flagsize_p = lltype.malloc(_c.socklen_t_ptr.TO, flavor='raw')
            try:
                flagsize_p[0] = rffi.cast(_c.socklen_t, rffi.sizeof(rffi.INT))
                res = _c.socketgetsockopt(self.fd, level, option,
                                          rffi.cast(rffi.VOIDP, flag_p),
                                          flagsize_p)
                if res < 0:
                    raise self.error_handler()
                result = rffi.cast(lltype.Signed, flag_p[0])
            finally:
                lltype.free(flagsize_p, flavor='raw')
        finally:
            lltype.free(flag_p, flavor='raw')
        return result

    def gettimeout(self):
        """Return the timeout of the socket. A timeout < 0 means that
        timeouts are disabled in the socket."""
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
        timeout = self._select(False)
        if timeout == 1:
            raise SocketTimeout
        elif timeout == 0:
            raw_buf, gc_buf = rffi.alloc_buffer(buffersize)
            try:
                read_bytes = _c.socketrecv(self.fd, raw_buf, buffersize, flags)
                if read_bytes >= 0:
                    return rffi.str_from_buffer(raw_buf, gc_buf, buffersize, read_bytes)
            finally:
                rffi.keep_buffer_alive_until_here(raw_buf, gc_buf)
        raise self.error_handler()

    def recvinto(self, rwbuffer, nbytes, flags=0):
        buf = self.recv(nbytes, flags)
        rwbuffer.setslice(0, buf)
        return len(buf)

    def recvfrom(self, buffersize, flags=0):
        """Like recv(buffersize, flags) but also return the sender's
        address."""
        read_bytes = -1
        timeout = self._select(False)
        if timeout == 1:
            raise SocketTimeout
        elif timeout == 0:
            raw_buf, gc_buf = rffi.alloc_buffer(buffersize)
            try:
                address, addr_p, addrlen_p = self._addrbuf()
                try:
                    read_bytes = _c.recvfrom(self.fd, raw_buf, buffersize, flags,
                                             addr_p, addrlen_p)
                    addrlen = rffi.cast(lltype.Signed, addrlen_p[0])
                finally:
                    lltype.free(addrlen_p, flavor='raw')
                    address.unlock()
                if read_bytes >= 0:
                    if addrlen:
                        address.addrlen = addrlen
                    else:
                        address = None
                    data = rffi.str_from_buffer(raw_buf, gc_buf, buffersize, read_bytes)
                    return (data, address)
            finally:
                rffi.keep_buffer_alive_until_here(raw_buf, gc_buf)
        raise self.error_handler()

    def recvfrom_into(self, rwbuffer, nbytes, flags=0):
        buf, addr = self.recvfrom(nbytes, flags)
        rwbuffer.setslice(0, buf)
        return len(buf), addr        

    def send_raw(self, dataptr, length, flags=0):
        """Send data from a CCHARP buffer."""
        res = -1
        timeout = self._select(True)
        if timeout == 1:
            raise SocketTimeout
        elif timeout == 0:
            res = _c.send(self.fd, dataptr, length, flags)
        if res < 0:
            raise self.error_handler()
        return res

    def send(self, data, flags=0):
        """Send a data string to the socket.  For the optional flags
        argument, see the Unix manual.  Return the number of bytes
        sent; this may be less than len(data) if the network is busy."""
        dataptr = rffi.get_nonmovingbuffer(data)
        try:
            return self.send_raw(dataptr, len(data), flags)
        finally:
            rffi.free_nonmovingbuffer(data, dataptr)

    def sendall(self, data, flags=0, signal_checker=None):
        """Send a data string to the socket.  For the optional flags
        argument, see the Unix manual.  This calls send() repeatedly
        until all data is sent.  If an error occurs, it's impossible
        to tell how much data has been sent."""
        dataptr = rffi.get_nonmovingbuffer(data)
        try:
            remaining = len(data)
            p = dataptr
            while remaining > 0:
                try:
                    res = self.send_raw(p, remaining, flags)
                    p = rffi.ptradd(p, res)
                    remaining -= res
                except CSocketError, e:
                    if e.errno != _c.EINTR:
                        raise
                if signal_checker:
                    signal_checker.check()
        finally:
            rffi.free_nonmovingbuffer(data, dataptr)

    def sendto(self, data, flags, address):
        """Like send(data, flags) but allows specifying the destination
        address.  (Note that 'flags' is mandatory here.)"""
        res = -1
        timeout = self._select(True)
        if timeout == 1:
            raise SocketTimeout
        elif timeout == 0:
            addr = address.lock()
            res = _c.sendto(self.fd, data, len(data), flags,
                            addr, address.addrlen)
            address.unlock()
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
        with rffi.scoped_str2charp(value) as buf:
            res = _c.socketsetsockopt(self.fd, level, option,
                                      rffi.cast(rffi.VOIDP, buf),
                                      len(value))
            if res < 0:
                raise self.error_handler()

    def setsockopt_int(self, level, option, value):
        with lltype.scoped_alloc(rffi.INTP.TO, 1) as flag_p:
            flag_p[0] = rffi.cast(rffi.INT, value)
            res = _c.socketsetsockopt(self.fd, level, option,
                                      rffi.cast(rffi.VOIDP, flag_p),
                                      rffi.sizeof(rffi.INT))
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
        return _c.socket_strerror_str(self.errno)

if _c.WIN32:
    def last_error():
        return CSocketError(rwin32.GetLastError())
else:
    def last_error():
        return CSocketError(_c.geterrno())

class GAIError(SocketErrorWithErrno):
    applevelerrcls = 'gaierror'
    def get_msg(self):
        return _c.gai_strerror_str(self.errno)

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

if hasattr(_c, 'socketpair'):
    def socketpair(family=socketpair_default_family, type=SOCK_STREAM, proto=0,
                   SocketClass=RSocket):
        """socketpair([family[, type[, proto]]]) -> (socket object, socket object)

        Create a pair of socket objects from the sockets returned by the platform
        socketpair() function.
        The arguments are the same as for socket() except the default family is
        AF_UNIX if defined on the platform; otherwise, the default is AF_INET.
        """
        result = lltype.malloc(_c.socketpair_t, 2, flavor='raw')
        res = _c.socketpair(family, type, proto, result)
        if res < 0:
            raise last_error()
        fd0 = rffi.cast(lltype.Signed, result[0])
        fd1 = rffi.cast(lltype.Signed, result[1])
        lltype.free(result, flavor='raw')
        return (make_socket(fd0, family, type, proto, SocketClass),
                make_socket(fd1, family, type, proto, SocketClass))

if hasattr(_c, 'dup'):
    def fromfd(fd, family, type, proto=0, SocketClass=RSocket):
        # Dup the fd so it and the socket can be closed independently
        fd = _c.dup(fd)
        if fd < 0:
            raise last_error()
        return make_socket(fd, family, type, proto, SocketClass)

def getdefaulttimeout():
    return defaults.timeout

def gethostname():
    size = 1024
    buf = lltype.malloc(rffi.CCHARP.TO, size, flavor='raw')
    try:
        res = _c.gethostname(buf, size)
        if res < 0:
            raise last_error()
        return rffi.charp2strn(buf, size)
    finally:
        lltype.free(buf, flavor='raw')

def gethostbyname(name):
    # this is explicitly not working with IPv6, because the docs say it
    # should not.  Just use makeipaddr(name) for an IPv6-friendly version...
    result = instantiate(INETAddress)
    makeipaddr(name, result)
    return result

def gethost_common(hostname, hostent, addr=None):
    if not hostent:
        raise HSocketError(hostname)
    family = rffi.getintfield(hostent, 'c_h_addrtype')
    if addr is not None and addr.family != family:
        raise CSocketError(_c.EAFNOSUPPORT)

    h_aliases = hostent.c_h_aliases
    if h_aliases:   # h_aliases can be NULL, according to SF #1511317
        aliases = rffi.charpp2liststr(h_aliases)
    else:
        aliases = []

    address_list = []
    h_addr_list = hostent.c_h_addr_list
    i = 0
    paddr = h_addr_list[0]
    while paddr:
        if family == AF_INET:
            p = rffi.cast(lltype.Ptr(_c.in_addr), paddr)
            addr = INETAddress.from_in_addr(p)
        elif AF_INET6 is not None and family == AF_INET6:
            p = rffi.cast(lltype.Ptr(_c.in6_addr), paddr)
            addr = INET6Address.from_in6_addr(p)
        else:
            raise RSocketError("unknown address family")
        address_list.append(addr)
        i += 1
        paddr = h_addr_list[i]
    return (rffi.charp2str(hostent.c_h_name), aliases, address_list)

def gethostbyname_ex(name):
    # XXX use gethostbyname_r() if available, and/or use locks if not
    addr = gethostbyname(name)
    hostent = _c.gethostbyname(name)
    return gethost_common(name, hostent, addr)

def gethostbyaddr(ip):
    # XXX use gethostbyaddr_r() if available, and/or use locks if not
    addr = makeipaddr(ip)
    assert isinstance(addr, IPAddress)
    p, size = addr.lock_in_addr()
    try:
        hostent = _c.gethostbyaddr(p, size, addr.family)
    finally:
        addr.unlock()
    return gethost_common(ip, hostent, addr)

def getaddrinfo(host, port_or_service,
                family=AF_UNSPEC, socktype=0, proto=0, flags=0,
                address_to_fill=None):
    # port_or_service is a string, not an int (but try str(port_number)).
    assert port_or_service is None or isinstance(port_or_service, str)
    hints = lltype.malloc(_c.addrinfo, flavor='raw', zero=True)
    rffi.setintfield(hints, 'c_ai_family',   family)
    rffi.setintfield(hints, 'c_ai_socktype', socktype)
    rffi.setintfield(hints, 'c_ai_protocol', proto)
    rffi.setintfield(hints, 'c_ai_flags'   , flags)
    # XXX need to lock around getaddrinfo() calls?
    p_res = lltype.malloc(rffi.CArray(_c.addrinfo_ptr), 1, flavor='raw')
    error = intmask(_c.getaddrinfo(host, port_or_service, hints, p_res))
    res = p_res[0]
    lltype.free(p_res, flavor='raw')
    lltype.free(hints, flavor='raw')
    if error:
        raise GAIError(error)
    try:
        result = []
        info = res
        while info:
            addr = make_address(info.c_ai_addr,
                                rffi.getintfield(info, 'c_ai_addrlen'),
                                address_to_fill)
            if info.c_ai_canonname:
                canonname = rffi.charp2str(info.c_ai_canonname)
            else:
                canonname = ""
            result.append((rffi.cast(lltype.Signed, info.c_ai_family),
                           rffi.cast(lltype.Signed, info.c_ai_socktype),
                           rffi.cast(lltype.Signed, info.c_ai_protocol),
                           canonname,
                           addr))
            info = info.c_ai_next
            address_to_fill = None    # don't fill the same address repeatedly
    finally:
        _c.freeaddrinfo(res)
    return result

def getservbyname(name, proto=None):
    servent = _c.getservbyname(name, proto)
    if not servent:
        raise RSocketError("service/proto not found")
    return ntohs(servent.c_s_port)

def getservbyport(port, proto=None):
    servent = _c.getservbyport(htons(port), proto)
    if not servent:
        raise RSocketError("port/proto not found")
    return rffi.charp2str(servent.c_s_name)

def getprotobyname(name):
    protoent = _c.getprotobyname(name)
    if not protoent:
        raise RSocketError("protocol not found")
    proto = protoent.c_p_proto
    return rffi.cast(lltype.Signed, proto)

def getnameinfo(address, flags):
    host = lltype.malloc(rffi.CCHARP.TO, NI_MAXHOST, flavor='raw')
    try:
        serv = lltype.malloc(rffi.CCHARP.TO, NI_MAXSERV, flavor='raw')
        try:
            addr = address.lock()
            error = intmask(_c.getnameinfo(addr, address.addrlen,
                                           host, NI_MAXHOST,
                                           serv, NI_MAXSERV, flags))
            address.unlock()
            if error:
                raise GAIError(error)
            return rffi.charp2str(host), rffi.charp2str(serv)
        finally:
            lltype.free(serv, flavor='raw')
    finally:
        lltype.free(host, flavor='raw')

if hasattr(_c, 'inet_aton'):
    def inet_aton(ip):
        "IPv4 dotted string -> packed 32-bits string"
        size = sizeof(_c.in_addr)
        buf = mallocbuf(size)
        try:
            if _c.inet_aton(ip, rffi.cast(lltype.Ptr(_c.in_addr), buf)):
                return ''.join([buf[i] for i in range(size)])
            else:
                raise RSocketError("illegal IP address string passed to inet_aton")
        finally:
            lltype.free(buf, flavor='raw')
else:
    def inet_aton(ip):
        "IPv4 dotted string -> packed 32-bits string"
        if ip == "255.255.255.255":
            return "\xff\xff\xff\xff"
        packed_addr = _c.inet_addr(ip)
        if packed_addr == rffi.cast(lltype.Unsigned, INADDR_NONE):
            raise RSocketError("illegal IP address string passed to inet_aton")
        size = sizeof(_c.in_addr)
        buf = mallocbuf(size)
        try:
            rffi.cast(rffi.UINTP, buf)[0] = packed_addr
            return ''.join([buf[i] for i in range(size)])
        finally:
            lltype.free(buf, flavor='raw')

def inet_ntoa(packed):
    "packet 32-bits string -> IPv4 dotted string"
    if len(packed) != sizeof(_c.in_addr):
        raise RSocketError("packed IP wrong length for inet_ntoa")
    buf = rffi.make(_c.in_addr)
    try:
        for i in range(sizeof(_c.in_addr)):
            rffi.cast(rffi.CCHARP, buf)[i] = packed[i]
        return rffi.charp2str(_c.inet_ntoa(buf))
    finally:
        lltype.free(buf, flavor='raw')

if hasattr(_c, 'inet_pton'):
    def inet_pton(family, ip):
        "human-readable string -> packed string"
        if family == AF_INET:
            size = sizeof(_c.in_addr)
        elif AF_INET6 is not None and family == AF_INET6:
            size = sizeof(_c.in6_addr)
        else:
            raise RSocketError("unknown address family")
        buf = mallocbuf(size)
        try:
            res = _c.inet_pton(family, ip, buf)
            if res < 0:
                raise last_error()
            elif res == 0:
                raise RSocketError("illegal IP address string passed "
                                   "to inet_pton")
            else:
                return ''.join([buf[i] for i in range(size)])
        finally:
            lltype.free(buf, flavor='raw')

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
        srcbuf = rffi.get_nonmovingbuffer(packed)
        try:
            dstbuf = mallocbuf(dstsize)
            try:
                res = _c.inet_ntop(family, srcbuf, dstbuf, dstsize)
                if not res:
                    raise last_error()
                return rffi.charp2str(res)
            finally:
                lltype.free(dstbuf, flavor='raw')
        finally:
            rffi.free_nonmovingbuffer(packed, srcbuf)

def setdefaulttimeout(timeout):
    if timeout < 0.0:
        timeout = -1.0
    defaults.timeout = timeout

import sys, os
import pytest
from pypy.tool.pytest.objspace import gettestobjspace
from pypy.interpreter.gateway import interp2app
from rpython.tool.udir import udir
from rpython.rlib import rsocket
from rpython.rtyper.lltypesystem import lltype, rffi

def setup_module(mod):
    mod.space = gettestobjspace(usemodules=['_socket', 'array', 'struct',
                                            'unicodedata'])
    global socket
    import socket
    mod.w_socket = space.appexec([], "(): import _socket as m; return m")
    mod.path = udir.join('fd')
    mod.path.write('fo')

def test_gethostname():
    host = space.appexec([w_socket], "(_socket): return _socket.gethostname()")
    assert space.unwrap(host) == socket.gethostname()

def test_gethostbyname():
    for host in ["localhost", "127.0.0.1"]:
        ip = space.appexec([w_socket, space.wrap(host)],
                           "(_socket, host): return _socket.gethostbyname(host)")
        assert space.unwrap(ip) == socket.gethostbyname(host)

def test_gethostbyname_ex():
    for host in ["localhost", "127.0.0.1"]:
        ip = space.appexec([w_socket, space.wrap(host)],
                           "(_socket, host): return _socket.gethostbyname_ex(host)")
        assert space.unwrap(ip) == socket.gethostbyname_ex(host)

def test_gethostbyaddr():
    try:
        socket.gethostbyaddr("::1")
    except socket.herror:
        ipv6 = False
    else:
        ipv6 = True
    for host in ["localhost", "127.0.0.1", "::1"]:
        if host == "::1" and not ipv6:
            from pypy.interpreter.error import OperationError
            with pytest.raises(OperationError):
                space.appexec([w_socket, space.wrap(host)],
                              "(_socket, host): return _socket.gethostbyaddr(host)")
            continue
        ip = space.appexec([w_socket, space.wrap(host)],
                           "(_socket, host): return _socket.gethostbyaddr(host)")
        assert space.unwrap(ip) == socket.gethostbyaddr(host)

def test_getservbyname():
    name = "smtp"
    # 2 args version
    port = space.appexec([w_socket, space.wrap(name)],
                        "(_socket, name): return _socket.getservbyname(name, 'tcp')")
    assert space.unwrap(port) == 25
    # 1 arg version
    if sys.version_info < (2, 4):
        pytest.skip("getservbyname second argument is not optional before python 2.4")
    port = space.appexec([w_socket, space.wrap(name)],
                        "(_socket, name): return _socket.getservbyname(name)")
    assert space.unwrap(port) == 25

def test_getservbyport():
    if sys.version_info < (2, 4):
        pytest.skip("getservbyport does not exist before python 2.4")
    port = 25
    # 2 args version
    name = space.appexec([w_socket, space.wrap(port)],
                         "(_socket, port): return _socket.getservbyport(port, 'tcp')")
    assert space.unwrap(name) == "smtp"
    name = space.appexec([w_socket, space.wrap(port)],
                         """(_socket, port):
                         try:
                             return _socket.getservbyport(port, 42)
                         except TypeError:
                             return 'OK'
                         """)
    assert space.unwrap(name) == 'OK'
    # 1 arg version
    name = space.appexec([w_socket, space.wrap(port)],
                         "(_socket, port): return _socket.getservbyport(port)")
    assert space.unwrap(name) == "smtp"

    from pypy.interpreter.error import OperationError
    exc = raises(OperationError, space.appexec,
           [w_socket], "(_socket): return _socket.getservbyport(-1)")
    assert exc.value.match(space, space.w_ValueError)

def test_getprotobyname():
    name = "tcp"
    w_n = space.appexec([w_socket, space.wrap(name)],
                        "(_socket, name): return _socket.getprotobyname(name)")
    assert space.unwrap(w_n) == socket.IPPROTO_TCP

def test_ntohs():
    w_n = space.appexec([w_socket, space.wrap(125)],
                        "(_socket, x): return _socket.ntohs(x)")
    assert space.unwrap(w_n) == socket.ntohs(125)

def test_ntohl():
    w_n = space.appexec([w_socket, space.wrap(125)],
                        "(_socket, x): return _socket.ntohl(x)")
    assert space.unwrap(w_n) == socket.ntohl(125)
    w_n = space.appexec([w_socket, space.wrap(0x89abcdef)],
                        "(_socket, x): return _socket.ntohl(x)")
    assert space.unwrap(w_n) in (0x89abcdef, 0xefcdab89)
    space.raises_w(space.w_OverflowError, space.appexec,
                   [w_socket, space.wrap(1<<32)],
                   "(_socket, x): return _socket.ntohl(x)")

def test_htons():
    w_n = space.appexec([w_socket, space.wrap(125)],
                        "(_socket, x): return _socket.htons(x)")
    assert space.unwrap(w_n) == socket.htons(125)

def test_htonl():
    w_n = space.appexec([w_socket, space.wrap(125)],
                        "(_socket, x): return _socket.htonl(x)")
    assert space.unwrap(w_n) == socket.htonl(125)
    w_n = space.appexec([w_socket, space.wrap(0x89abcdef)],
                        "(_socket, x): return _socket.htonl(x)")
    assert space.unwrap(w_n) in (0x89abcdef, 0xefcdab89)
    space.raises_w(space.w_OverflowError, space.appexec,
                   [w_socket, space.wrap(1<<32)],
                   "(_socket, x): return _socket.htonl(x)")

def test_aton_ntoa():
    ip = '123.45.67.89'
    packed = socket.inet_aton(ip)
    w_p = space.appexec([w_socket, space.wrap(ip)],
                        "(_socket, ip): return _socket.inet_aton(ip)")
    assert space.bytes_w(w_p) == packed
    w_ip = space.appexec([w_socket, w_p],
                         "(_socket, p): return _socket.inet_ntoa(p)")
    assert space.unicode_w(w_ip) == ip

def test_pton_ntop_ipv4():
    if not hasattr(socket, 'inet_pton'):
        pytest.skip('No socket.inet_pton on this platform')
    tests = [
        ("123.45.67.89", "\x7b\x2d\x43\x59"),
        ("0.0.0.0", "\x00" * 4),
        ("255.255.255.255", "\xff" * 4),
    ]
    for ip, packed in tests:
        w_p = space.appexec([w_socket, space.wrap(ip)],
                            "(_socket, ip): return _socket.inet_pton(_socket.AF_INET, ip)")
        assert space.unwrap(w_p) == packed
        w_ip = space.appexec([w_socket, w_p],
                             "(_socket, p): return _socket.inet_ntop(_socket.AF_INET, p)")
        assert space.unwrap(w_ip) == ip

def test_ntop_ipv6():
    if not hasattr(socket, 'inet_pton'):
        pytest.skip('No socket.inet_pton on this platform')
    if not socket.has_ipv6:
        pytest.skip("No IPv6 on this platform")
    tests = [
        ("\x00" * 16, "::"),
        ("\x01" * 16, ":".join(["101"] * 8)),
        ("\x00\x00\x10\x10" * 4, None), #"::1010:" + ":".join(["0:1010"] * 3)),
        ("\x00" * 12 + "\x01\x02\x03\x04", "::1.2.3.4"),
        ("\x00" * 10 + "\xff\xff\x01\x02\x03\x04", "::ffff:1.2.3.4"),
    ]
    for packed, ip in tests:
        w_ip = space.appexec([w_socket, space.newbytes(packed)],
            "(_socket, packed): return _socket.inet_ntop(_socket.AF_INET6, packed)")
        if ip is not None:   # else don't check for the precise representation
            assert space.unwrap(w_ip) == ip
        w_packed = space.appexec([w_socket, w_ip],
            "(_socket, ip): return _socket.inet_pton(_socket.AF_INET6, ip)")
        assert space.unwrap(w_packed) == packed

def test_pton_ipv6():
    if not hasattr(socket, 'inet_pton'):
        pytest.skip('No socket.inet_pton on this platform')
    if not socket.has_ipv6:
        pytest.skip("No IPv6 on this platform")
    tests = [
        ("\x00" * 16, "::"),
        ("\x01" * 16, ":".join(["101"] * 8)),
        ("\x00\x01" + "\x00" * 12 + "\x00\x02", "1::2"),
        ("\x00" * 4 + "\x00\x01" * 6, "::1:1:1:1:1:1"),
        ("\x00\x01" * 6 + "\x00" * 4, "1:1:1:1:1:1::"),
        ("\xab\xcd\xef\00" + "\x00" * 12, "ABCD:EF00::"),
        ("\xab\xcd\xef\00" + "\x00" * 12, "abcd:ef00::"),
        ("\x00\x00\x10\x10" * 4, "::1010:" + ":".join(["0:1010"] * 3)),
        ("\x00" * 12 + "\x01\x02\x03\x04", "::1.2.3.4"),
        ("\x00" * 10 + "\xff\xff\x01\x02\x03\x04", "::ffff:1.2.3.4"),
    ]
    for packed, ip in tests:
        w_packed = space.appexec([w_socket, space.wrap(ip)],
            "(_socket, ip): return _socket.inet_pton(_socket.AF_INET6, ip)")
        assert space.unwrap(w_packed) == packed

def test_has_ipv6():
    pytest.skip("has_ipv6 is always True on PyPy for now")
    res = space.appexec([w_socket], "(_socket): return _socket.has_ipv6")
    assert space.unwrap(res) == socket.has_ipv6

def test_getaddrinfo():
    host = b"localhost"
    port = 25
    info = socket.getaddrinfo(host, port)
    w_l = space.appexec([w_socket, space.newbytes(host), space.wrap(port)],
                        "(_socket, host, port): return _socket.getaddrinfo(host, port)")
    assert space.unwrap(w_l) == info
    w_l = space.appexec([w_socket, space.wrap(host), space.wrap(port)],
                        "(_socket, host, port): return _socket.getaddrinfo(host, port)")
    assert space.unwrap(w_l) == info
    w_l = space.appexec([w_socket, space.newbytes(host), space.wrap('smtp')],
                        "(_socket, host, port): return _socket.getaddrinfo(host, port)")
    assert space.unwrap(w_l) == socket.getaddrinfo(host, 'smtp')

def test_unknown_addr_as_object():
    from pypy.module._socket.interp_socket import addr_as_object
    c_addr = lltype.malloc(rsocket._c.sockaddr, flavor='raw', track_allocation=False)
    c_addr.c_sa_data[0] = 'c'
    rffi.setintfield(c_addr, 'c_sa_family', 15)
    # XXX what size to pass here? for the purpose of this test it has
    #     to be short enough so we have some data, 1 sounds good enough
    #     + sizeof USHORT
    w_obj = addr_as_object(rsocket.Address(c_addr, 1 + 2), -1, space)
    assert space.isinstance_w(w_obj, space.w_tuple)
    assert space.int_w(space.getitem(w_obj, space.wrap(0))) == 15
    assert space.str_w(space.getitem(w_obj, space.wrap(1))) == 'c'

def test_addr_raw_packet():
    from pypy.module._socket.interp_socket import addr_as_object
    if not hasattr(rsocket._c, 'sockaddr_ll'):
        pytest.skip("posix specific test")
    # HACK: To get the correct interface number of lo, which in most cases is 1,
    # but can be anything (i.e. 39), we need to call the libc function
    # if_nametoindex to get the correct index
    import ctypes
    libc = ctypes.CDLL(ctypes.util.find_library('c'))
    ifnum = libc.if_nametoindex('lo')

    c_addr_ll = lltype.malloc(rsocket._c.sockaddr_ll, flavor='raw')
    addrlen = rffi.sizeof(rsocket._c.sockaddr_ll)
    c_addr = rffi.cast(lltype.Ptr(rsocket._c.sockaddr), c_addr_ll)
    rffi.setintfield(c_addr_ll, 'c_sll_ifindex', ifnum)
    rffi.setintfield(c_addr_ll, 'c_sll_protocol', 8)
    rffi.setintfield(c_addr_ll, 'c_sll_pkttype', 13)
    rffi.setintfield(c_addr_ll, 'c_sll_hatype', 0)
    rffi.setintfield(c_addr_ll, 'c_sll_halen', 3)
    c_addr_ll.c_sll_addr[0] = 'a'
    c_addr_ll.c_sll_addr[1] = 'b'
    c_addr_ll.c_sll_addr[2] = 'c'
    rffi.setintfield(c_addr, 'c_sa_family', socket.AF_PACKET)
    # fd needs to be somehow valid
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    fd = s.fileno()
    w_obj = addr_as_object(rsocket.make_address(c_addr, addrlen), fd, space)
    lltype.free(c_addr_ll, flavor='raw')
    assert space.is_true(space.eq(w_obj, space.newtuple([
        space.wrap('lo'),
        space.wrap(socket.ntohs(8)),
        space.wrap(13),
        space.wrap(False),
        space.wrap("abc"),
        ])))

def test_getnameinfo():
    from pypy.module._socket.interp_socket import get_error
    host = "127.0.0.1"
    port = 25
    info = socket.getnameinfo((host, port), 0)
    w_l = space.appexec([w_socket, space.wrap(host), space.wrap(port)],
                        "(_socket, host, port): return _socket.getnameinfo((host, port), 0)")
    assert space.unwrap(w_l) == info
    sockaddr = space.newtuple([space.wrap('mail.python.org'), space.wrap(0)])
    space.raises_w(get_error(space, 'error'), space.appexec,
                   [w_socket, sockaddr, space.wrap(0)],
                   "(_socket, sockaddr, flags): return _socket.getnameinfo(sockaddr, flags)")
    if socket.has_ipv6:
        sockaddr = space.newtuple([space.wrap('::1'), space.wrap(0),
                                   space.wrap(0xffffffff)])
        space.raises_w(space.w_OverflowError, space.appexec,
                       [w_socket, sockaddr, space.wrap(0)],
                       "(_socket, sockaddr, flags): return _socket.getnameinfo(sockaddr, flags)")

def test_timeout():
    space.appexec([w_socket, space.wrap(25.4)],
                  "(_socket, timeout): _socket.setdefaulttimeout(timeout)")
    w_t = space.appexec([w_socket],
                  "(_socket): return _socket.getdefaulttimeout()")
    assert space.unwrap(w_t) == 25.4

    space.appexec([w_socket, space.w_None],
                  "(_socket, timeout): _socket.setdefaulttimeout(timeout)")
    w_t = space.appexec([w_socket],
                  "(_socket): return _socket.getdefaulttimeout()")
    assert space.unwrap(w_t) is None


# XXX also need tests for other connection and timeout errors


class AppTestSocket:
    spaceconfig = dict(usemodules=['_socket', '_weakref', 'struct'])

    def setup_class(cls):
        cls.space = space
        cls.w_udir = space.wrap(str(udir))

    def teardown_class(cls):
        if not cls.runappdirect:
            cls.space.sys.getmodule('_socket').shutdown(cls.space)

    def test_module(self):
        import _socket
        assert _socket.socket.__name__ == 'socket'
        assert _socket.socket.__module__ == '_socket'

    def test_ntoa_exception(self):
        import _socket
        raises(_socket.error, _socket.inet_ntoa, b"ab")

    def test_aton_exceptions(self):
        import _socket
        tests = ["127.0.0.256", "127.0.0.255555555555555555", "127.2b.0.0",
            "127.2.0.0.1", "127.2.0."]
        for ip in tests:
            raises(_socket.error, _socket.inet_aton, ip)

    def test_ntop_exceptions(self):
        import _socket
        if not hasattr(_socket, 'inet_ntop'):
            skip('No socket.inet_pton on this platform')
        for family, packed, exception in \
                    [(_socket.AF_INET + _socket.AF_INET6, b"", _socket.error),
                     (_socket.AF_INET, b"a", ValueError),
                     (_socket.AF_INET6, b"a", ValueError),
                     (_socket.AF_INET, "aa\u2222a", TypeError)]:
            raises(exception, _socket.inet_ntop, family, packed)

    def test_pton_exceptions(self):
        import _socket
        if not hasattr(_socket, 'inet_pton'):
            skip('No socket.inet_pton on this platform')
        tests = [
            (_socket.AF_INET + _socket.AF_INET6, ""),
            (_socket.AF_INET, "127.0.0.256"),
            (_socket.AF_INET, "127.0.0.255555555555555555"),
            (_socket.AF_INET, "127.2b.0.0"),
            (_socket.AF_INET, "127.2.0.0.1"),
            (_socket.AF_INET, "127.2..0"),
            (_socket.AF_INET6, "127.0.0.1"),
            (_socket.AF_INET6, "1::2::3"),
            (_socket.AF_INET6, "1:1:1:1:1:1:1:1:1"),
            (_socket.AF_INET6, "1:1:1:1:1:1:1:1::"),
            (_socket.AF_INET6, "1:1:1::1:1:1:1:1"),
            (_socket.AF_INET6, "1::22222:1"),
            (_socket.AF_INET6, "1::eg"),
        ]
        for family, ip in tests:
            raises(_socket.error, _socket.inet_pton, family, ip)

    def test_newsocket_error(self):
        import _socket
        raises(_socket.error, _socket.socket, 10001, _socket.SOCK_STREAM, 0)

    def test_socket_fileno(self):
        import _socket
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM, 0)
        assert s.fileno() > -1
        assert isinstance(s.fileno(), int)

    def test_socket_repr(self):
        import _socket
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        try:
            expected = ('<socket object, fd=%s, family=%s, type=%s, protocol=%s>'
                        % (s.fileno(), s.family, s.type, s.proto))
            assert repr(s) == expected
        finally:
            s.close()
        expected = ('<socket object, fd=-1, family=%s, type=%s, protocol=%s>'
                    % (s.family, s.type, s.proto))
        assert repr(s) == expected

    def test_socket_close(self):
        import _socket, os
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM, 0)
        fileno = s.fileno()
        assert s.fileno() >= 0
        s.close()
        assert s.fileno() < 0
        s.close()
        if os.name != 'nt':
            raises(OSError, os.close, fileno)

    def test_socket_close_error(self):
        import _socket, os
        if os.name == 'nt':
            skip("Windows sockets are not files")
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM, 0)
        os.close(s.fileno())
        s.close()

    def test_socket_connect(self):
        import _socket, os
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM, 0)
        # it would be nice to have a test which works even if there is no
        # network connection. However, this one is "good enough" for now. Skip
        # it if there is no connection.
        try:
            s.connect(("www.python.org", 80))
        except _socket.gaierror as ex:
            skip("GAIError - probably no connection: %s" % str(ex.args))
        name = s.getpeername() # Will raise socket.error if not connected
        assert name[1] == 80
        s.close()

    def test_socket_connect_ex(self):
        import _socket
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM, 0)
        # The following might fail if the DNS redirects failed requests to a
        # catch-all address (i.e. opendns).
        # Make sure we get an app-level error, not an interp one.
        raises(_socket.gaierror, s.connect_ex, ("wrong.invalid", 80))
        s.close()

    def test_socket_connect_typeerrors(self):
        tests = [
            "",
            ("80"),
            ("80", "80"),
            (80, 80),
        ]
        import _socket
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM, 0)
        for args in tests:
            raises((TypeError, ValueError), s.connect, args)
        s.close()

    def test_bigport(self):
        import _socket
        s = _socket.socket()
        exc = raises(OverflowError, s.connect, ("localhost", -1))
        assert "port must be 0-65535." in str(exc.value)
        exc = raises(OverflowError, s.connect, ("localhost", 1000000))
        assert "port must be 0-65535." in str(exc.value)
        s = _socket.socket(_socket.AF_INET6)
        exc = raises(OverflowError, s.connect, ("::1", 1234, 1048576))
        assert "flowinfo must be 0-1048575." in str(exc.value)

    def test_NtoH(self):
        import sys
        import _socket as socket
        # This just checks that htons etc. are their own inverse,
        # when looking at the lower 16 or 32 bits.
        sizes = {socket.htonl: 32, socket.ntohl: 32,
                 socket.htons: 16, socket.ntohs: 16}
        for func, size in sizes.items():
            mask = (1 << size) - 1
            for i in (0, 1, 0xffff, ~0xffff, 2, 0x01234567, 0x76543210):
                assert i & mask == func(func(i&mask)) & mask

            swapped = func(mask)
            assert swapped & mask == mask
            try:
                func(-1)
            except (OverflowError, ValueError):
                pass
            else:
                assert False
            try:
                func(sys.maxsize*2+2)
            except OverflowError:
                pass
            else:
                assert False

    def test_NtoH_overflow(self):
        skip("we are not checking for overflowing values yet")
        import _socket as socket
        # Checks that we cannot give too large values to htons etc.
        # Skipped for now; CPython 2.6 is also not consistent.
        sizes = {socket.htonl: 32, socket.ntohl: 32,
                 socket.htons: 16, socket.ntohs: 16}
        for func, size in sizes.items():
            try:
                func(1 << size)
            except OverflowError:
                pass
            else:
                assert False

    def test_newsocket(self):
        import socket
        s = socket.socket()

    def test_subclass(self):
        from _socket import socket
        class MySock(socket):
            blah = 123
        s = MySock()
        assert s.blah == 123

    def test_getsetsockopt(self):
        import _socket as socket
        import struct
        # A socket should start with reuse == 0
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        reuse = s.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR)
        assert reuse == 0
        #
        raises(TypeError, s.setsockopt, socket.SOL_SOCKET,
                          socket.SO_REUSEADDR, 2 ** 31)
        raises(TypeError, s.setsockopt, socket.SOL_SOCKET,
                          socket.SO_REUSEADDR, 2 ** 32 + 1)
        assert s.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR) == 0
        #
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        reuse = s.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR)
        assert reuse != 0
        # String case
        intsize = struct.calcsize('i')
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        reusestr = s.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,
                                intsize)
        (reuse,) = struct.unpack('i', reusestr)
        assert reuse == 0
        reusestr = struct.pack('i', 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, reusestr)
        reusestr = s.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,
                                intsize)
        (reuse,) = struct.unpack('i', reusestr)
        assert reuse != 0

    def test_socket_ioctl(self):
        import _socket, sys
        if sys.platform != 'win32':
            skip("win32 only")
        assert hasattr(_socket.socket, 'ioctl')
        assert hasattr(_socket, 'SIO_RCVALL')
        assert hasattr(_socket, 'RCVALL_ON')
        assert hasattr(_socket, 'RCVALL_OFF')
        assert hasattr(_socket, 'SIO_KEEPALIVE_VALS')
        s = _socket.socket()
        raises(ValueError, s.ioctl, -1, None)
        s.ioctl(_socket.SIO_KEEPALIVE_VALS, (1, 100, 100))

    def test_dup(self):
        import _socket as socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('localhost', 0))
        fd = socket.dup(s.fileno())
        assert s.fileno() != fd

    def test_buffer(self):
        # Test that send/sendall/sendto accept a buffer as arg
        import _socket, os
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM, 0)
        # XXX temporarily we use python.org to test, will have more robust tests
        # in the absence of a network connection later when more parts of the
        # socket API are implemented.  Currently skip the test if there is no
        # connection.
        try:
            s.connect(("www.python.org", 80))
        except _socket.gaierror as ex:
            skip("GAIError - probably no connection: %s" % str(ex.args))
        exc = raises(TypeError, s.send, None)
        assert str(exc.value) == "'NoneType' does not support the buffer interface"
        assert s.send(memoryview(b'')) == 0
        assert s.sendall(memoryview(b'')) is None
        exc = raises(TypeError, s.send, '')
        assert str(exc.value) == "'str' does not support the buffer interface"
        raises(TypeError, s.sendall, '')
        s.close()
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM, 0)
        s.sendto(memoryview(b''), ('localhost', 9)) # Send to discard port.
        s.close()

    def test_unix_socket_connect(self):
        import _socket, os
        if not hasattr(_socket, 'AF_UNIX'):
            skip('AF_UNIX not supported.')
        oldcwd = os.getcwd()
        os.chdir(self.udir)
        try:
            sockpath = 'app_test_unix_socket_connect'

            serversock = _socket.socket(_socket.AF_UNIX)
            serversock.bind(sockpath)
            serversock.listen(1)

            clientsock = _socket.socket(_socket.AF_UNIX)
            clientsock.connect(sockpath)
            fileno, addr = serversock._accept()
            s = _socket.socket(fileno=fileno)
            assert not addr

            s.send(b'X')
            data = clientsock.recv(100)
            assert data == b'X'
            clientsock.send(b'Y')
            data = s.recv(100)
            assert data == b'Y'

            clientsock.close()
            s.close()
        finally:
            os.chdir(oldcwd)

    def test_automatic_shutdown(self):
        # doesn't really test anything, but at least should not explode
        # in close_all_sockets()
        import _socket
        self.foo = _socket.socket()

    def test_subclass_init(self):
        # Socket is not created in __new__, but in __init__.
        import socket
        class Socket_IPV6(socket.socket):
            def __init__(self):
                socket.socket.__init__(self, family=socket.AF_INET6)
        assert Socket_IPV6().family == socket.AF_INET6

    def test_subclass_noinit(self):
        from _socket import socket
        class MySock(socket):
            def __init__(self, *args):
                pass  # don't call super
        s = MySock()
        assert s.type == 0
        assert s.proto == 0
        assert s.family == 0
        assert s.fileno() < 0
        raises(OSError, s.bind, ('localhost', 0))

    def test_dealloc_warn(self):
        import _socket
        import gc
        import warnings

        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        r = repr(s)
        gc.collect()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            s = None
            gc.collect()
        assert len(w) == 1, [str(warning) for warning in w]
        assert r in str(w[0])


class AppTestNetlink:
    def setup_class(cls):
        if not hasattr(os, 'getpid'):
            pytest.skip("AF_NETLINK needs os.getpid()")
        w_ok = space.appexec([], "(): import _socket; " +
                                 "return hasattr(_socket, 'AF_NETLINK')")
        if not space.is_true(w_ok):
            pytest.skip("no AF_NETLINK on this platform")
        cls.space = space

    def test_connect_to_kernel_netlink_routing_socket(self):
        import _socket, os
        s = _socket.socket(_socket.AF_NETLINK, _socket.SOCK_DGRAM, _socket.NETLINK_ROUTE)
        assert s.getsockname() == (0, 0)
        s.bind((0, 0))
        a, b = s.getsockname()
        assert a == os.getpid()
        assert b == 0


class AppTestPacket:
    def setup_class(cls):
        if not hasattr(os, 'getuid') or os.getuid() != 0:
            pytest.skip("AF_PACKET needs to be root for testing")
        w_ok = space.appexec([], "(): import _socket; " +
                                 "return hasattr(_socket, 'AF_PACKET')")
        if not space.is_true(w_ok):
            pytest.skip("no AF_PACKET on this platform")
        cls.space = space

    def test_convert_between_tuple_and_sockaddr_ll(self):
        import _socket
        s = _socket.socket(_socket.AF_PACKET, _socket.SOCK_RAW)
        assert s.getsockname() == ('', 0, 0, 0, '')
        s.bind(('lo', 123))
        a, b, c, d, e = s.getsockname()
        assert (a, b, c) == ('lo', 123, 0)
        assert isinstance(d, int)
        assert isinstance(e, str)
        assert 0 <= len(e) <= 8


class AppTestSocketTCP:
    HOST = 'localhost'
    spaceconfig = {'usemodules': ['_socket', 'array']}

    def setup_method(self, method):
        w_HOST = self.space.wrap(self.HOST)
        self.w_serv = self.space.appexec([w_HOST],
            '''(HOST):
            import _socket
            serv = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
            serv.bind((HOST, 0))
            serv.listen(1)
            return serv
            ''')

    def teardown_method(self, method):
        if hasattr(self, 'w_serv'):
            self.space.appexec([self.w_serv], '(serv): serv.close()')
            self.w_serv = None

    def test_timeout(self):
        from _socket import timeout
        def raise_timeout():
            self.serv.settimeout(1.0)
            self.serv._accept()
        raises(timeout, raise_timeout)

    def test_timeout_zero(self):
        from _socket import error
        def raise_error():
            self.serv.settimeout(0.0)
            foo = self.serv._accept()
        raises(error, raise_error)

    def test_recv_send_timeout(self):
        from _socket import socket, timeout, SOL_SOCKET, SO_RCVBUF, SO_SNDBUF
        cli = socket()
        cli.connect(self.serv.getsockname())
        fileno, addr = self.serv._accept()
        t = socket(fileno=fileno)
        cli.settimeout(1.0)
        # test recv() timeout
        t.send(b'*')
        buf = cli.recv(100)
        assert buf == b'*'
        raises(timeout, cli.recv, 100)
        # test that send() works
        count = cli.send(b'!')
        assert count == 1
        buf = t.recv(1)
        assert buf == b'!'
        # test that sendall() works
        count = cli.sendall(b'?')
        assert count is None
        buf = t.recv(1)
        assert buf == b'?'
        # speed up filling the buffers
        t.setsockopt(SOL_SOCKET, SO_RCVBUF, 4096)
        cli.setsockopt(SOL_SOCKET, SO_SNDBUF, 4096)
        # test send() timeout
        count = 0
        try:
            while 1:
                count += cli.send(b'foobar' * 70)
                assert count < 100000
        except timeout:
            pass
        t.recv(count)
        # test sendall() timeout
        try:
            while 1:
                cli.sendall(b'foobar' * 70)
        except timeout:
            pass
        # done
        cli.close()
        t.close()

    def test_recv_into(self):
        import socket
        import array
        MSG = b'dupa was here\n'
        cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cli.connect(self.serv.getsockname())
        fileno, addr = self.serv._accept()
        conn = socket.socket(fileno=fileno)
        buf = memoryview(MSG)
        conn.send(buf)
        buf = array.array('b', b' ' * 1024)
        nbytes = cli.recv_into(buf)
        assert nbytes == len(MSG)
        msg = buf.tobytes()[:len(MSG)]
        assert msg == MSG

        conn.send(MSG)
        buf = bytearray(1024)
        nbytes = cli.recv_into(memoryview(buf))
        assert nbytes == len(MSG)
        msg = buf[:len(MSG)]
        assert msg == MSG

    def test_recvfrom_into(self):
        import socket
        import array
        MSG = b'dupa was here\n'
        cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cli.connect(self.serv.getsockname())
        fileno, addr = self.serv._accept()
        conn = socket.socket(fileno=fileno)
        buf = memoryview(MSG)
        conn.send(buf)
        buf = array.array('b', b' ' * 1024)
        nbytes, addr = cli.recvfrom_into(buf)
        assert nbytes == len(MSG)
        msg = buf.tobytes()[:len(MSG)]
        assert msg == MSG

        conn.send(MSG)
        buf = bytearray(1024)
        nbytes, addr = cli.recvfrom_into(memoryview(buf))
        assert nbytes == len(MSG)
        msg = buf[:len(MSG)]
        assert msg == MSG

        conn.send(MSG)
        buf = bytearray(8)
        exc = raises(ValueError, cli.recvfrom_into, buf, 1024)
        assert str(exc.value) == "nbytes is greater than the length of the buffer"

    def test_family(self):
        import socket
        cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        assert cli.family == socket.AF_INET


class AppTestErrno:
    spaceconfig = {'usemodules': ['_socket']}

    def test_errno(self):
        from socket import socket, AF_INET, SOCK_STREAM, error
        import errno
        s = socket(AF_INET, SOCK_STREAM)
        exc = raises(error, s.accept)
        assert isinstance(exc.value, error)
        assert isinstance(exc.value, IOError)
        # error is EINVAL, or WSAEINVAL on Windows
        assert exc.value.errno == getattr(errno, 'WSAEINVAL', errno.EINVAL)
        assert isinstance(exc.value.strerror, str)

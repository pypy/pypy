# spaceconfig = {"usemodules": ["_socket", "_weakref", "array", "struct", "select", "unicodedata"]}
import os
import sys
import pytest


def test_module():
    import _socket
    assert _socket.socket.__name__ == 'socket'
    assert _socket.socket.__module__ == '_socket'

def test_overflow_errors():
    import _socket
    pytest.raises(OverflowError, _socket.getservbyport, -1)
    pytest.raises(OverflowError, _socket.getservbyport, 65536)

def test_ntoa_exception():
    import _socket
    pytest.raises(_socket.error, _socket.inet_ntoa, b"ab")

def test_aton_exceptions():
    import _socket
    tests = ["127.0.0.256", "127.0.0.255555555555555555", "127.2b.0.0",
        "127.2.0.0.1", "127.2.0."]
    for ip in tests:
        pytest.raises(_socket.error, _socket.inet_aton, ip)

def test_ntop_exceptions():
    import _socket
    if not hasattr(_socket, 'inet_ntop'):
        pytest.skip('No socket.inet_pton on this platform')
    for family, packed, exception in \
                [(_socket.AF_INET + _socket.AF_INET6, b"", _socket.error),
                 (_socket.AF_INET, b"a", ValueError),
                 (_socket.AF_INET6, b"a", ValueError),
                 (_socket.AF_INET, "aa\u2222a", TypeError)]:
        pytest.raises(exception, _socket.inet_ntop, family, packed)

def test_pton_exceptions():
    import _socket
    if not hasattr(_socket, 'inet_pton'):
        pytest.skip('No socket.inet_pton on this platform')
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
        pytest.raises(_socket.error, _socket.inet_pton, family, ip)

def test_newsocket_error():
    import _socket
    pytest.raises(_socket.error, _socket.socket, 10001, _socket.SOCK_STREAM, 0)

def test_socket_fileno():
    import _socket
    s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM, 0)
    assert s.fileno() > -1
    assert isinstance(s.fileno(), int)

def test_socket_repr():
    import _socket
    s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    try:
        expected = ('<socket object, fd=%s, family=%s, type=%s, proto=%s>'
                    % (s.fileno(), s.family, s.type, s.proto))
        assert repr(s) == expected
    finally:
        s.close()
    expected = ('<socket object, fd=-1, family=%s, type=%s, proto=%s>'
                % (s.family, s.type, s.proto))
    assert repr(s) == expected

def test_socket_close():
    import _socket, os
    s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM, 0)
    fileno = s.fileno()
    assert s.fileno() >= 0
    s.close()
    assert s.fileno() < 0
    s.close()
    if os.name != 'nt':
        pytest.raises(OSError, os.close, fileno)

@pytest.mark.skipif(sys.platform == 'win32')
def test_socket_close_exception():
    import _socket, errno
    s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM, 0)
    _socket.socket(fileno=s.fileno()).close()
    e = pytest.raises(OSError, s.close)
    assert e.value.errno in (errno.EBADF, errno.ENOTSOCK)

@pytest.mark.skipif(sys.platform == 'win32')
def test_setblocking_invalidfd():
    import _socket
    s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM, 0)
    _socket.socket(fileno=s.fileno()).close()
    pytest.raises(OSError, s.setblocking, False)

def test_socket_connect():
    import _socket
    s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM, 0)
    try:
        s.connect(("www.python.org", 80))
    except _socket.gaierror as ex:
        pytest.skip("GAIError - probably no connection: %s" % str(ex.args))
    except ConnectionRefusedError as ex:
        pytest.skip("Connection Refused - probably no connection: %s" % str(ex.args))
    name = s.getpeername() # Will raise socket.error if not connected
    assert name[1] == 80
    s.close()

def test_socket_connect_ex():
    import _socket
    s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM, 0)
    # The following might fail if the DNS redirects failed requests to a
    # catch-all address (i.e. opendns).
    # Make sure we get an app-level error, not an interp one.
    pytest.raises(_socket.gaierror, s.connect_ex, ("wrong.invalid", 80))
    s.close()

def test_socket_connect_typeerrors():
    tests = [
        "",
        "80",
        ("80",),
        ("80", "80"),
        (80, 80),
    ]
    import _socket
    s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM, 0)
    for args in tests:
        pytest.raises((TypeError, ValueError), s.connect, args)
    s.close()

def test_bigport():
    import _socket
    s = _socket.socket()
    exc = pytest.raises(OverflowError, s.connect, ("localhost", -1))
    assert "port must be 0-65535." in str(exc.value)
    exc = pytest.raises(OverflowError, s.connect, ("localhost", 1000000))
    assert "port must be 0-65535." in str(exc.value)
    s = _socket.socket(_socket.AF_INET6)
    exc = pytest.raises(OverflowError, s.connect, ("::1", 1234, 1048576))
    assert "flowinfo must be 0-1048575." in str(exc.value)

def test_NtoH():
    import _socket as socket
    # This checks that htons etc. are their own inverse,
    # when looking at the lower 16 or 32 bits.  It also
    # checks that we get OverflowErrors when calling with -1,
    # or (for XtoXl()) with too large values.  For XtoXs()
    # large values are silently truncated instead, like CPython.
    sizes = {socket.htonl: 32, socket.ntohl: 32,
             socket.htons: 16, socket.ntohs: 16}
    for func, size in sizes.items():
        mask = (1 << size) - 1
        for i in (0, 1, 0xffff, 0xffff0000, 2, 0x01234567, 0x76543210):
            assert i & mask == func(func(i&mask)) & mask

        swapped = func(mask)
        assert swapped & mask == mask
        pytest.raises(OverflowError, func, -1)
        if size > 16:    # else, values too large are ignored
            pytest.raises(OverflowError, func, 2 ** size)

def test_newsocket():
    import _socket
    s = _socket.socket()

def test_subclass():
    from _socket import socket
    class MySock(socket):
        blah = 123
    s = MySock()
    assert s.blah == 123

def test_getsetsockopt():
    import _socket as socket
    import struct
    # A socket should start with reuse == 0
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    reuse = s.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR)
    assert reuse == 0
    #
    pytest.raises(TypeError, s.setsockopt, socket.SOL_SOCKET,
                      socket.SO_REUSEADDR, 2 ** 31)
    pytest.raises(TypeError, s.setsockopt, socket.SOL_SOCKET,
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
    # try to call setsockopt() with a buffer argument
    reusestr = struct.pack('i', 0)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, memoryview(reusestr))
    reusestr = s.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,
                            intsize)
    (reuse,) = struct.unpack('i', reusestr)
    assert reuse == 0

def test_getsetsockopt_zero():
    # related to issue #2561: when specifying the buffer size param:
    # if 0 or None, should return the setted value,
    # otherwise an empty buffer of the specified size
    import _socket
    s = _socket.socket()
    assert s.getsockopt(_socket.IPPROTO_TCP, _socket.TCP_NODELAY, 0) == 0
    ret = s.getsockopt(_socket.IPPROTO_TCP, _socket.TCP_NODELAY, 2)
    if len(ret) == 1:
        # win32 returns a byte-as-bool
        assert ret == b'\x00'
    else:
        assert ret == b'\x00\x00'
    s.setsockopt(_socket.IPPROTO_TCP, _socket.TCP_NODELAY, True)
    assert s.getsockopt(_socket.IPPROTO_TCP, _socket.TCP_NODELAY, 0) != 0
    s.setsockopt(_socket.IPPROTO_TCP, _socket.TCP_NODELAY, 1)
    assert s.getsockopt(_socket.IPPROTO_TCP, _socket.TCP_NODELAY, 0) != 0

def test_getsockopt_bad_length():
    import _socket
    s = _socket.socket()
    buf = s.getsockopt(_socket.IPPROTO_TCP, _socket.TCP_NODELAY, 1024)
    if len(buf) == 1:
        # win32 returns a byte-as-bool
        assert buf == b'\x00'
    else:
        assert buf == b'\x00' * 4
    pytest.raises(_socket.error, s.getsockopt,
           _socket.IPPROTO_TCP, _socket.TCP_NODELAY, 1025)
    pytest.raises(_socket.error, s.getsockopt,
           _socket.IPPROTO_TCP, _socket.TCP_NODELAY, -1)

def test_socket_ioctl():
    import _socket, sys
    if sys.platform != 'win32':
        pytest.skip("win32 only")
    assert hasattr(_socket.socket, 'ioctl')
    assert hasattr(_socket, 'SIO_RCVALL')
    assert hasattr(_socket, 'RCVALL_ON')
    assert hasattr(_socket, 'RCVALL_OFF')
    assert hasattr(_socket, 'SIO_KEEPALIVE_VALS')
    s = _socket.socket()
    pytest.raises(ValueError, s.ioctl, -1, None)
    s.ioctl(_socket.SIO_KEEPALIVE_VALS, (1, 100, 100))

@pytest.mark.skipif(os.name != 'nt', reason="win32 only")
def test_socket_sharelocal():
    import _socket, sys, os
    assert hasattr(_socket.socket, 'share')
    s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    with pytest.raises(OSError):
        s.listen()
    s.bind(('localhost', 0))
    s.listen(1)
    data = s.share(os.getpid())
    # emulate socket.fromshare
    s2 = _socket.socket(0, 0, 0, data)
    try:
        assert s.gettimeout() == s2.gettimeout()
        assert s.family == s2.family
        assert s.type == s2.type
        if s.proto != 0:
            assert s.proto == s2.proto
    finally:
        s.close()
        s2.close()

def test_dup():
    import _socket as socket, os
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    fd = socket.dup(s.fileno())
    assert s.fileno() != fd
    if os.name != 'nt':
        assert os.get_inheritable(s.fileno()) is False
        assert os.get_inheritable(fd) is False
    s_dup = socket.socket(fileno=fd)
    s_dup.close()
    s.close()

def test_dup_error():
    import _socket
    pytest.raises(_socket.error, _socket.dup, 123456)

@pytest.mark.skipif(os.name=='nt', reason="no recvmsg on win32")
def test_recvmsg_issue2649():
    import _socket as socket
    listener = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(('127.0.0.1', 1234))

    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    s.sendto(b'x', ('127.0.0.1', 1234))
    with pytest.raises(BlockingIOError):
        queue = s.recvmsg(1024, 1024, socket.MSG_ERRQUEUE)

def test_buffer():
    # Test that send/sendall/sendto accept a buffer as arg
    import _socket
    s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM, 0)
    # XXX temporarily we use python.org to test, will have more robust tests
    # in the absence of a network connection later when more parts of the
    # socket API are implemented.  Currently skip the test if there is no
    # connection.
    try:
        s.connect(("www.python.org", 80))
    except _socket.gaierror as ex:
        pytest.skip("GAIError - probably no connection: %s" % str(ex.args))
    except ConnectionRefusedError as ex:
        pytest.skip("Connection Refused - probably no connection: %s" % str(ex.args))
    exc = pytest.raises(TypeError, s.send, None)
    assert str(exc.value).startswith("a bytes-like object is required,")
    assert s.send(memoryview(b'')) == 0
    assert s.sendall(memoryview(b'')) is None
    exc = pytest.raises(TypeError, s.send, '')
    assert str(exc.value).startswith("a bytes-like object is required,")
    pytest.raises(TypeError, s.sendall, '')
    s.close()
    s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM, 0)
    s.sendto(memoryview(b''), ('localhost', 9))  # Send to discard port.
    s.close()

def test_listen_default():
    import _socket, sys
    if sys.platform == 'win32':
        with pytest.raises(OSError):
            _socket.socket().listen()
    else:
        _socket.socket().listen()
    assert isinstance(_socket.SOMAXCONN, int)

def test_unix_socket_connect():
    import _socket, os, tempfile
    if not hasattr(_socket, 'AF_UNIX'):
        pytest.skip('AF_UNIX not supported.')
    udir = tempfile.mkdtemp()
    oldcwd = os.getcwd()
    os.chdir(udir)
    try:
      for sockpath in ['app_test_unix_socket_connect',
                       b'b_app_test_unix_socket_connect',
                       bytearray(b'ba_app_test_unix_socket_connect')]:

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

def test_subclass_init():
    # Socket is not created in __new__, but in __init__.
    import _socket as socket
    class Socket_IPV6(socket.socket):
        def __init__(self):
            socket.socket.__init__(self, family=socket.AF_INET6)
    assert Socket_IPV6().family == socket.AF_INET6

def test_subclass_noinit():
    from _socket import socket
    class MySock(socket):
        def __init__(self, *args):
            pass  # don't call super
    s = MySock()
    assert s.type == 0
    assert s.proto == 0
    assert s.family == 0
    assert s.fileno() < 0
    pytest.raises(OSError, s.bind, ('localhost', 0))

def test_dealloc_warn():
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

def test_invalid_fd():
    import _socket
    pytest.raises(ValueError, _socket.socket, fileno=-1)
    pytest.raises(TypeError, _socket.socket, fileno=42.5)

def test_socket_non_inheritable():
    import _socket, os
    s1 = _socket.socket()
    if os.name == 'nt':
        with pytest.raises(OSError):
            os.get_inheritable(s1.fileno())
    else:
        assert os.get_inheritable(s1.fileno()) is False
    s1.close()

def test_socketpair_non_inheritable():
    import _socket, os
    if not hasattr(_socket, 'socketpair'):
        pytest.skip("no socketpair")
    s1, s2 = _socket.socketpair()
    assert os.get_inheritable(s1.fileno()) is False
    assert os.get_inheritable(s2.fileno()) is False
    s1.close()
    s2.close()

def test_hostname_unicode():
    import _socket
    domain = u"испытание.pythontest.net"
    try:
        _socket.gethostbyname(domain)
        _socket.gethostbyname_ex(domain)
        _socket.getaddrinfo(domain, 0, _socket.AF_UNSPEC, _socket.SOCK_STREAM)
    except _socket.gaierror as ex:
        pytest.skip("GAIError - probably no connection: %s" % str(ex.args))
    s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    pytest.raises(TypeError, s.connect, (domain + '\x00', 80))

def test_socket_close_via_close():
    import _socket
    sock = _socket.socket()
    try:
        sock.bind(('localhost', 0))
        _socket.close(sock.fileno())
        with pytest.raises(OSError):
            sock.listen(1)
        with pytest.raises(OSError):
            _socket.close(sock.fileno())
    finally:
        with pytest.raises(OSError):
            sock.close()

def test_socket_get_values_from_fd():
    import _socket
    if hasattr(_socket, "SOCK_DGRAM"):
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        try:
            s.bind(('localhost', 0))
            fd = s.fileno()
            s2 = _socket.socket(fileno=fd)
            try:
                # detach old fd to avoid double close
                s.detach()
                assert s2.fileno() == fd
                assert s2.family == _socket.AF_INET
                assert s2.type == _socket.SOCK_DGRAM

            finally:
                s2.close()
        finally:
            s.close()

def test_socket_init_non_blocking():
    import _socket
    if not hasattr(_socket, "SOCK_NONBLOCK"):
        pytest.skip("no SOCK_NONBLOCK")
    s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM |
                                        _socket.SOCK_NONBLOCK)
    assert s.getblocking() == False
    assert s.gettimeout() == 0.0

def test_socket_consistent_sock_type():
    import _socket
    SOCK_NONBLOCK = getattr(_socket, 'SOCK_NONBLOCK', 0)
    SOCK_CLOEXEC = getattr(_socket, 'SOCK_CLOEXEC', 0)
    sock_type = _socket.SOCK_STREAM | SOCK_NONBLOCK | SOCK_CLOEXEC

    s = _socket.socket(_socket.AF_INET, sock_type)
    try:
        assert s.type == _socket.SOCK_STREAM
        s.settimeout(1)
        assert s.type == _socket.SOCK_STREAM
        s.settimeout(0)
        assert s.type == _socket.SOCK_STREAM
        s.setblocking(True)
        assert s.type == _socket.SOCK_STREAM
        s.setblocking(False)
        assert s.type == _socket.SOCK_STREAM
    finally:
        s.close()


@pytest.mark.skipif(not hasattr(os, 'getpid'),
    reason="AF_NETLINK needs os.getpid()")
def test_connect_to_kernel_netlink_routing_socket():
    import _socket, os
    if not hasattr(_socket, 'AF_NETLINK'):
        pytest.skip("no AF_NETLINK on this platform")
    s = _socket.socket(_socket.AF_NETLINK, _socket.SOCK_DGRAM,
                       _socket.NETLINK_ROUTE)
    assert s.getsockname() == (0, 0)
    s.bind((0, 0))
    a, b = s.getsockname()
    assert a == os.getpid()
    assert b == 0


@pytest.mark.skipif(not hasattr(os, 'getuid') or os.getuid() != 0,
    reason="AF_PACKET needs to be root for testing")
def test_convert_between_tuple_and_sockaddr_ll():
    import _socket
    if not hasattr(_socket, 'AF_PACKET'):
        pytest.skip("no AF_PACKET on this platform")
    s = _socket.socket(_socket.AF_PACKET, _socket.SOCK_RAW)
    assert s.getsockname() == ('', 0, 0, 0, b''), 's.getsockname %s' % str(s.getsockname())
    s.bind(('lo', 123))
    a, b, c, d, e = s.getsockname()
    assert (a, b, c) == ('lo', 123, 0)
    assert isinstance(d, int)
    assert isinstance(e, bytes)
    assert 0 <= len(e) <= 8
    s.close()


def test_tcp_timeout():
    import _socket
    serv = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    serv.bind(('localhost', 0))
    serv.listen(1)
    from _socket import timeout
    def raise_timeout():
        serv.settimeout(1.0)
        serv._accept()
    try:
        pytest.raises(timeout, raise_timeout)
    finally:
        serv.close()

def test_tcp_timeout_zero():
    import _socket
    serv = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    serv.bind(('localhost', 0))
    serv.listen(1)
    from _socket import error
    def raise_error():
        serv.settimeout(0.0)
        foo = serv._accept()
    try:
        pytest.raises(error, raise_error)
    finally:
        serv.close()

@pytest.mark.skipif(os.name == 'nt', reason="win32 has additional buffering")
def test_tcp_recv_send_timeout():
    import _socket
    serv = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    serv.bind(('localhost', 0))
    serv.listen(1)
    from _socket import socket, timeout, SOL_SOCKET, SO_RCVBUF, SO_SNDBUF
    import sys
    cli = socket()
    cli.settimeout(1.0)
    cli.connect(serv.getsockname())
    fileno, addr = serv._accept()
    t = socket(fileno=fileno)
    # test recv() timeout
    t.send(b'*')
    buf = cli.recv(100)
    assert buf == b'*'
    pytest.raises(timeout, cli.recv, 100)
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
    if sys.platform != 'win32':
        # windows never fills the buffer
        try:
            while 1:
                count += cli.send(b'foobar' * 70)
                if sys.platform == 'darwin':
                    # MacOS will auto-tune up to 512k
                    # (net.inet.tcp.doauto{rcv,snd}buf sysctls)
                    assert count < 1000000
                else:
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
    serv.close()

def test_tcp_getblocking():
    import _socket
    serv = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    serv.bind(('localhost', 0))
    serv.listen(1)
    serv.setblocking(True)
    assert serv.getblocking()
    serv.setblocking(False)
    assert not serv.getblocking()
    serv.close()

def test_tcp_recv_into():
    import _socket as socket
    import array
    import _io
    serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serv.bind(('localhost', 0))
    serv.listen(1)
    MSG = b'dupa was here\n'
    cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cli.connect(serv.getsockname())
    fileno, addr = serv._accept()
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

    # A case where rwbuffer.get_raw_address() fails
    conn.send(MSG)
    buf = _io.BytesIO(b' ' * 1024)
    m = buf.getbuffer()
    nbytes = cli.recv_into(m)
    assert nbytes == len(MSG)
    msg = buf.getvalue()[:len(MSG)]
    assert msg == MSG
    conn.close()
    serv.close()

def test_tcp_recvfrom_into():
    import _socket as socket
    import array
    import _io
    serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serv.bind(('localhost', 0))
    serv.listen(1)
    MSG = b'dupa was here\n'
    cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cli.connect(serv.getsockname())
    fileno, addr = serv._accept()
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

    # A case where rwbuffer.get_raw_address() fails
    conn.send(MSG)
    buf = _io.BytesIO(b' ' * 1024)
    nbytes, addr = cli.recvfrom_into(buf.getbuffer())
    assert nbytes == len(MSG)
    msg = buf.getvalue()[:len(MSG)]
    assert msg == MSG

    conn.send(MSG)
    buf = bytearray(8)
    exc = pytest.raises(ValueError, cli.recvfrom_into, buf, 1024)
    assert str(exc.value) == "nbytes is greater than the length of the buffer"
    conn.close()
    serv.close()

@pytest.mark.skipif(os.name == 'nt', reason="no recvmg_into on win32")
def test_tcp_recvmsg_into():
    import _socket
    serv = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    serv.bind(('localhost', 0))
    serv.listen(1)
    cli = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    cli.connect(serv.getsockname())
    fileno, addr = serv._accept()
    conn = _socket.socket(fileno=fileno)
    conn.send(b'Hello World!')
    buf1 = bytearray(5)
    buf2 = bytearray(6)
    rettup = cli.recvmsg_into([memoryview(buf1), memoryview(buf2)])
    nbytes, _, _, addr = rettup
    assert nbytes == 11
    assert buf1 == b'Hello'
    assert buf2 == b' World'
    conn.close()
    cli.close()
    serv.close()

def test_tcp_family():
    import _socket as socket
    cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    assert cli.family == socket.AF_INET

def test_tcp_missing_error_catching():
    from _socket import socket, error
    s = socket()
    s.close()
    pytest.raises(error, s.settimeout, 1)            # EBADF
    pytest.raises(error, s.setblocking, True)        # EBADF
    pytest.raises(error, s.getsockopt, 42, 84, 8)    # EBADF

def test_tcp_accept_non_inheritable():
    import _socket, os
    serv = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    serv.bind(('localhost', 0))
    serv.listen(1)
    cli = _socket.socket()
    cli.connect(serv.getsockname())
    fileno, addr = serv._accept()
    if os.name == 'nt':
        with pytest.raises(OSError):
            os.get_inheritable(fileno)
    else:
        assert os.get_inheritable(fileno) is False
    conn = _socket.socket(fileno=fileno)
    conn.close()
    cli.close()
    serv.close()

def test_tcp_recv_into_params():
    import os
    import _socket
    serv = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    serv.bind(('localhost', 0))
    serv.listen(1)
    cli = _socket.socket()
    cli.connect(serv.getsockname())
    fileno, addr = serv._accept()
    conn = _socket.socket(fileno=fileno)
    conn.send(b"abcdef")
    #
    m = memoryview(bytearray(5))
    pytest.raises(ValueError, cli.recv_into, m, -1)
    pytest.raises(ValueError, cli.recv_into, m, 6)
    cli.recv_into(m, 5)
    assert m.tobytes() == b"abcde"
    conn.close()
    cli.close()
    serv.close()

def test_tcp_bytearray_name():
    import _socket as socket
    if not hasattr(socket, 'AF_UNIX'):
        pytest.skip('AF_UNIX not supported.')
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.bind(bytearray(b"\x00python\x00test\x00"))
    assert s.getsockname() == b"\x00python\x00test\x00"

def test_tcp_bind_audit():
    import _socket
    import sys
    events = []
    def f(event, args):
        events.append((event, args))
    s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    sys.addaudithook(f)
    s.bind(('localhost', 0))
    assert len(events) == 1
    assert events[0][0] == 'socket.bind'
    assert events[0][1][0] is s
    assert events[0][1][1] == ('localhost', 0)

def test_tcp_timeout_is_alias():
    import _socket
    assert _socket.timeout is TimeoutError


def test_errno():
    from _socket import socket, AF_INET, SOCK_STREAM, error
    import errno
    s = socket(AF_INET, SOCK_STREAM)
    exc = pytest.raises(error, s._accept)
    assert isinstance(exc.value, error)
    assert isinstance(exc.value, IOError)
    # error is EINVAL, or WSAEINVAL on Windows
    assert exc.value.errno == getattr(errno, 'WSAEINVAL', errno.EINVAL)
    assert isinstance(exc.value.strerror, str)

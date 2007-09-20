import py, errno, sys
from pypy.rlib import rsocket_rffi as rsocket
from pypy.rlib.rsocket_rffi import *

def setup_module(mod):
    rsocket_startup()

def test_ipv4_addr():
    a = INETAddress("localhost", 4000)
    assert a.get_host() == "127.0.0.1"
    assert a.get_port() == 4000
    a = INETAddress("", 4001)
    assert a.get_host() == "0.0.0.0"
    assert a.get_port() == 4001
    a = INETAddress("<broadcast>", 47002)
    assert a.get_host() == "255.255.255.255"
    assert a.get_port() == 47002
    py.test.raises(GAIError, INETAddress, "no such host exists", 47003)
    res = repr(a)
    assert res == "<INETAddress 255.255.255.255:47002>"

def test_unix_addr():
    if getattr(rsocket, 'AF_UNIX', None) is None:
        py.test.skip('AF_UNIX not supported.')
    a = UNIXAddress("/tmp/socketname")
    assert a.get_path() == "/tmp/socketname"

def test_netlink_addr():
    if getattr(rsocket, 'AF_NETLINK', None) is None:
        py.test.skip('AF_NETLINK not supported.')
    pid = 1
    group_mask = 64 + 32
    a = NETLINKAddress(pid, group_mask)
    assert a.get_pid() == pid
    assert a.get_groups() == group_mask
    
def test_gethostname():
    s = gethostname()
    assert isinstance(s, str)

def test_gethostbyname():
    a = gethostbyname('localhost')
    assert isinstance(a, INETAddress)
    assert a.get_host() == "127.0.0.1"

def test_gethostbyname_ex():
    name, aliases, address_list = gethostbyname_ex('localhost')
    allnames = [name] + aliases
    for n in allnames:
        assert isinstance(n, str)
    assert 'localhost' in allnames
    for a in address_list:
        if isinstance(a, INETAddress) and a.get_host() == "127.0.0.1":
            break  # ok
    else:
        py.test.fail("could not find the 127.0.0.1 IPv4 address in %r"
                     % (address_list,))

def test_socketpair():
    if sys.platform == "win32":
        py.test.skip('No socketpair on Windows')
    s1, s2 = socketpair()
    s1.send('?')
    buf = s2.recv(100)
    assert buf == '?'
    count = s2.send('x'*99)
    assert 1 <= count <= 99
    buf = s1.recv(100)
    assert buf == 'x'*count
    s1.close()
    s2.close()

def test_simple_tcp():
    import thread
    sock = RSocket()
    try_ports = [1023] + range(20000, 30000, 437)
    for port in try_ports:
        print 'binding to port %d:' % (port,),
        try:
            sock.bind(INETAddress('127.0.0.1', port))
            print 'works'
            break
        except SocketError, e:   # should get a "Permission denied"
            print e
    else:
        raise e

    addr = INETAddress('127.0.0.1', port)
    assert addr.eq(sock.getsockname())
    sock.listen(1)
    s2 = RSocket(AF_INET, SOCK_STREAM)
    thread.start_new_thread(s2.connect, (addr,))
    print 'waiting for connexion'
    s1, addr2 = sock.accept()
    print 'connexion accepted'
    assert addr.eq(s2.getpeername())
    assert addr2.eq(s2.getsockname())
    assert addr2.eq(s1.getpeername())

    s1.send('?')
    print 'sent one character'
    buf = s2.recv(100)
    assert buf == '?'
    print 'received ok'
    thread.start_new_thread(s2.sendall, ('x'*50000,))
    buf = ''
    while len(buf) < 50000:
        data = s1.recv(50100)
        print 'recv returned %d bytes' % (len(data,))
        assert data
        buf += data
    assert buf == 'x'*50000
    print 'data received ok'
    s1.close()
    s2.close()

def test_simple_udp():
    s1 = RSocket(AF_INET, SOCK_DGRAM)
    try_ports = [1023] + range(20000, 30000, 437)
    for port in try_ports:
        print 'binding to port %d:' % (port,),
        try:
            s1.bind(INETAddress('127.0.0.1', port))
            print 'works'
            break
        except SocketError, e:   # should get a "Permission denied"
            print e
    else:
        raise e

    addr = INETAddress('127.0.0.1', port)
    assert addr.eq(s1.getsockname())
    s2 = RSocket(AF_INET, SOCK_DGRAM)
    s2.connect(addr)
    addr2 = s2.getsockname()

    s1.sendto('?', 0, addr2)
    buf = s2.recv(100)
    assert buf == '?'
    count = s2.send('x'*99)
    assert 1 <= count <= 99
    buf, addr3 = s1.recvfrom(100)
    assert buf == 'x'*count
    assert addr3.eq(addr2)
    s1.close()
    s2.close()

def test_nonblocking():
    sock = RSocket()
    sock.setblocking(False)
    try_ports = [1023] + range(20000, 30000, 437)
    for port in try_ports:
        print 'binding to port %d:' % (port,),
        try:
            sock.bind(INETAddress('127.0.0.1', port))
            print 'works'
            break
        except SocketError, e:   # should get a "Permission denied"
            print e
    else:
        raise e

    addr = INETAddress('127.0.0.1', port)
    assert addr.eq(sock.getsockname())
    sock.listen(1)
    err = py.test.raises(CSocketError, sock.accept)
    assert err.value.errno in (errno.EAGAIN, errno.EWOULDBLOCK)

    s2 = RSocket(AF_INET, SOCK_STREAM)
    s2.setblocking(False)
    err = py.test.raises(CSocketError, s2.connect, addr)
    assert err.value.errno in (errno.EINPROGRESS, errno.EWOULDBLOCK)

    s1, addr2 = sock.accept()
    s1.setblocking(False)
    assert addr.eq(s2.getpeername())
    assert addr2.eq(s2.getsockname())
    assert addr2.eq(s1.getpeername())

    err = s2.connect_ex(addr)   # should now work
    assert err in (0, errno.EISCONN)

    s1.send('?')
    import time
    time.sleep(0.01) # Windows needs some time to transfer data
    buf = s2.recv(100)
    assert buf == '?'
    err = py.test.raises(CSocketError, s1.recv, 5000)
    assert err.value.errno in (errno.EAGAIN, errno.EWOULDBLOCK)
    count = s2.send('x'*50000)
    assert 1 <= count <= 50000
    while count: # Recv may return less than requested
        buf = s1.recv(count + 100)
        assert len(buf) <= count
        assert buf.count('x') == len(buf)
        count -= len(buf)
    # Check that everything has been read
    err = py.test.raises(CSocketError, s1.recv, 5000)
    s1.close()
    s2.close()

def test_getaddrinfo_http():
    lst = getaddrinfo('localhost', 'http')
    assert isinstance(lst, list)
    found = False
    for family, socktype, protocol, canonname, addr in lst:
        if (family          == AF_INET and
            socktype        == SOCK_STREAM and
            addr.get_host() == '127.0.0.1' and
            addr.get_port() == 80):
            found = True
    assert found, lst
    py.test.raises(GAIError, getaddrinfo, 'www.very-invalidaddress.com', None)

def test_getaddrinfo_snake():
    lst = getaddrinfo('snake.cs.uni-duesseldorf.de', None)
    assert isinstance(lst, list)
    found = False
    for family, socktype, protocol, canonname, addr in lst:
        if addr.get_host() == '134.99.112.214':
            found = True
    assert found, lst

def test_getaddrinfo_no_reverse_lookup():
    # It seems that getaddrinfo never runs a reverse lookup on Linux.
    # Python2.3 on Windows returns the hostname.
    lst = getaddrinfo('134.99.112.214', None, flags=AI_CANONNAME)
    assert isinstance(lst, list)
    found = False
    for family, socktype, protocol, canonname, addr in lst:
        assert canonname != 'snake.cs.uni-duesseldorf.de'
        if addr.get_host() == '134.99.112.214':
            found = True
    assert found, lst

def test_connect_ex():
    s = RSocket()
    err = s.connect_ex(INETAddress('0.0.0.0', 0))   # should not work
    assert err in (errno.ECONNREFUSED, errno.EADDRNOTAVAIL)


def test_getsetsockopt():
    import struct
    assert struct.calcsize("i") == rffi.sizeof(rffi.INT)
    # A socket sould start with reuse == 0
    s = RSocket(AF_INET, SOCK_STREAM)
    reuse = s.getsockopt_int(SOL_SOCKET, SO_REUSEADDR)
    assert reuse == 0
    s.setsockopt_int(SOL_SOCKET, SO_REUSEADDR, 1)
    reuse = s.getsockopt_int(SOL_SOCKET, SO_REUSEADDR)
    assert reuse != 0
    # Test string case
    s = RSocket(AF_INET, SOCK_STREAM)
    reusestr = s.getsockopt(SOL_SOCKET, SO_REUSEADDR, rffi.sizeof(rffi.INT))
    value, = struct.unpack("i", reusestr)
    assert value == 0
    optstr = struct.pack("i", 1)
    s.setsockopt(SOL_SOCKET, SO_REUSEADDR, optstr)
    reusestr = s.getsockopt(SOL_SOCKET, SO_REUSEADDR, rffi.sizeof(rffi.INT))
    value, = struct.unpack("i", reusestr)
    assert value != 0

def test_dup():
    if sys.platform == "win32":
        skip("dup does not work on Windows")
    s = RSocket(AF_INET, SOCK_STREAM)
    s.setsockopt_int(SOL_SOCKET, SO_REUSEADDR, 1)
    s.bind(INETAddress('localhost', 50007))
    s2 = s.dup()
    assert s.fileno() != s2.fileno()
    assert s.getsockname().eq(s2.getsockname())

def test_inet_aton():
    assert inet_aton('1.2.3.4') == '\x01\x02\x03\x04'
    assert inet_aton('127.0.0.1') == '\x7f\x00\x00\x01'
    tests = ["127.0.0.256", "127.0.0.255555555555555555", "127.2b.0.0",
        "127.2.0.0.1", "127.2.0."]
    for ip in tests:
        py.test.raises(SocketError, inet_aton, ip)

    # Windows 2000: missing numbers are replaced by 0
    for ip, aton in [("11..22.33", '\x0b\x00\x16\x21'),
                     (".11.22.33", '\x00\x0b\x16\x21')]:
        try:
            assert inet_aton(ip) == aton
        except SocketError:
            pass

def test_inet_ntoa():
    assert inet_ntoa('\x01\x02\x03\x04') == '1.2.3.4'

def test_inet_pton():
    assert inet_pton(AF_INET, '1.2.3.5') == '\x01\x02\x03\x05'
    py.test.raises(SocketError, inet_pton, AF_INET, '127.0.0.256')

def test_inet_ntop():
    assert inet_ntop(AF_INET, '\x01\x02\x03\x05') == '1.2.3.5'

class TestTCP:
    PORT = 50007
    HOST = 'localhost'

    def setup_method(self, method):
        self.serv = RSocket(AF_INET, SOCK_STREAM)
        self.serv.setsockopt_int(SOL_SOCKET, SO_REUSEADDR, 1)
        self.serv.bind(INETAddress(self.HOST, self.PORT))
        self.serv.listen(1)

    def teardown_method(self, method):
        self.serv.close()
        self.serv = None

    def test_timeout(self):
        def raise_timeout():
            self.serv.settimeout(1.0)
            self.serv.accept()
        py.test.raises(SocketTimeout, raise_timeout)

    def test_timeout_zero(self):
        def raise_error():
            self.serv.settimeout(0.0)
            foo = self.serv.accept()
        py.test.raises(SocketError, raise_error)


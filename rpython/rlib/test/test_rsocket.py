import py, errno, sys
from rpython.rlib import rsocket
from rpython.rlib.rsocket import *
import socket as cpy_socket
from rpython.translator.c.test.test_genc import compile


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
    for host in ["localhost", "127.0.0.1"]:
        a = gethostbyname(host)
        assert isinstance(a, INETAddress)
        assert a.get_host() == "127.0.0.1"

def test_gethostbyname_ex():
    for host in ["localhost", "127.0.0.1"]:
        name, aliases, address_list = gethostbyname_ex(host)
        allnames = [name] + aliases
        for n in allnames:
            assert isinstance(n, str)
        if sys.platform != 'win32':
            assert host in allnames
        for a in address_list:
            if isinstance(a, INETAddress) and a.get_host() == "127.0.0.1":
                break  # ok
            # no IPV6, should always return IPV4
        else:
            py.test.fail("could not find the localhost address in %r"
                         % (address_list,))

def test_gethostbyaddr():
    try:
        cpy_socket.gethostbyaddr("::1")
    except cpy_socket.herror:
        ipv6 = HSocketError
    except cpy_socket.gaierror:
        ipv6 = GAIError
    else:
        ipv6 = None
    for host in ["localhost", "127.0.0.1", "::1"]:
        if host == "::1" and ipv6:
            with py.test.raises(ipv6):
                gethostbyaddr(host)
            continue
        name, aliases, address_list = gethostbyaddr(host)
        allnames = [name] + aliases
        for n in allnames:
            assert isinstance(n, str)
        if sys.platform != 'win32':
            assert 'localhost' in allnames or 'ip6-localhost' in allnames
        for a in address_list:
            if isinstance(a, INETAddress) and a.get_host() == "127.0.0.1":
                break  # ok
            if host != '127.0.0.1':  # name lookup might return IPV6
                if isinstance(a, INET6Address) and a.get_host() == "::1":
                    break  # ok
        else:
            py.test.fail("could not find the localhost address in %r"
                         % (address_list,))

def test_getservbyname():
    assert getservbyname('http') == 80
    assert getservbyname('http', 'tcp') == 80

def test_getservbyport():
    assert getservbyport(80) == cpy_socket.getservbyport(80)
    assert getservbyport(80, 'tcp') == cpy_socket.getservbyport(80)

def test_getprotobyname():
    assert getprotobyname('tcp') == IPPROTO_TCP
    assert getprotobyname('udp') == IPPROTO_UDP

def test_socketpair():
    if sys.platform == "win32":
        py.test.skip('No socketpair on Windows')
    s1, s2 = socketpair()
    s1.sendall('?')
    buf = s2.recv(100)
    assert buf == '?'
    count = s2.send('x'*99)
    assert 1 <= count <= 99
    buf = s1.recv(100)
    assert buf == 'x'*count
    s1.close()
    s2.close()

def test_socketpair_recvinto_1():
    class Buffer:
        def setslice(self, start, string):
            self.x = string

        def get_raw_address(self):
            raise ValueError

    if sys.platform == "win32":
        py.test.skip('No socketpair on Windows')
    s1, s2 = socketpair()
    buf = Buffer()
    s1.sendall('?')
    n = s2.recvinto(buf, 1)
    assert n == 1
    assert buf.x == '?'
    count = s2.send('x'*99)
    assert 1 <= count <= 99
    n = s1.recvinto(buf, 100)
    assert n == count
    assert buf.x == 'x'*count
    s1.close()
    s2.close()

def test_socketpair_recvinto_2():
    class Buffer:
        def __init__(self):
            self._p = lltype.malloc(rffi.CCHARP.TO, 100, flavor='raw',
                                    track_allocation=False)

        def _as_str(self, count):
            return rffi.charpsize2str(self._p, count)

        def get_raw_address(self):
            return self._p

    if sys.platform == "win32":
        py.test.skip('No socketpair on Windows')
    s1, s2 = socketpair()
    buf = Buffer()
    s1.sendall('?')
    n = s2.recvinto(buf, 1)
    assert n == 1
    assert buf._as_str(1) == '?'
    count = s2.send('x'*99)
    assert 1 <= count <= 99
    n = s1.recvinto(buf, 100)
    assert n == count
    assert buf._as_str(n) == 'x'*count
    s1.close()
    s2.close()

def test_socketpair_recvfrom_into_1():
    class Buffer:
        def setslice(self, start, string):
            self.x = string

        def get_raw_address(self):
            raise ValueError

    if sys.platform == "win32":
        py.test.skip('No socketpair on Windows')
    s1, s2 = socketpair()
    buf = Buffer()
    s1.sendall('?')
    n, addr = s2.recvfrom_into(buf, 1)
    assert n == 1
    assert addr is None
    assert buf.x == '?'
    count = s2.send('x'*99)
    assert 1 <= count <= 99
    n, addr = s1.recvfrom_into(buf, 100)
    assert n == count
    assert addr is None
    assert buf.x == 'x'*count
    s1.close()
    s2.close()

def test_socketpair_recvfrom_into_2():
    class Buffer:
        def __init__(self):
            self._p = lltype.malloc(rffi.CCHARP.TO, 100, flavor='raw',
                                    track_allocation=False)

        def _as_str(self, count):
            return rffi.charpsize2str(self._p, count)

        def get_raw_address(self):
            return self._p

    if sys.platform == "win32":
        py.test.skip('No socketpair on Windows')
    s1, s2 = socketpair()
    buf = Buffer()
    s1.sendall('?')
    n, addr = s2.recvfrom_into(buf, 1)
    assert n == 1
    assert addr is None
    assert buf._as_str(1) == '?'
    count = s2.send('x'*99)
    assert 1 <= count <= 99
    n, addr = s1.recvfrom_into(buf, 100)
    assert n == count
    assert addr is None
    assert buf._as_str(n) == 'x'*count
    s1.close()
    s2.close()


def test_simple_tcp():
    from rpython.rlib import rthread
    sock = RSocket()
    try_ports = [1023] + range(20000, 30000, 437)
    for port in try_ports:
        print 'binding to port %d:' % (port,),
        try:
            sock.bind(INETAddress('127.0.0.1', port))
            print 'works'
            break
        except SocketError as e:   # should get a "Permission denied"
            print e
    else:
        raise e

    addr = INETAddress('127.0.0.1', port)
    assert addr.eq(sock.getsockname())
    sock.listen(1)
    s2 = RSocket(AF_INET, SOCK_STREAM)
    s2.settimeout(10.0) # test one side with timeouts so select is used, shouldn't affect test
    connected = [False] #thread-mutable list
    def connecting():
        try:
            s2.connect(addr)
            connected[0] = True
        finally:
            lock.release()
    lock = rthread.allocate_lock()
    lock.acquire(True)
    rthread.start_new_thread(connecting, ())
    print 'waiting for connection'
    fd1, addr2 = sock.accept()
    s1 = RSocket(fd=fd1)
    print 'connection accepted'
    lock.acquire(True)
    assert connected[0]
    print 'connecting side knows that the connection was accepted too'
    assert addr.eq(s2.getpeername())
    #assert addr2.eq(s2.getsockname())
    assert addr2.eq(s1.getpeername())

    s1.send('?')
    print 'sent one character'
    buf = s2.recv(100)
    assert buf == '?'
    print 'received ok'
    def sendstuff():
        s2.sendall('x'*50000)
    rthread.start_new_thread(sendstuff, ())
    buf = ''
    while len(buf) < 50000:
        data = s1.recv(50100)
        print 'recv returned %d bytes' % (len(data,))
        assert data
        buf += data
    assert buf == 'x'*50000
    print 'data received ok'
    s1.shutdown(SHUT_RDWR)
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
        except SocketError as e:   # should get a "Permission denied"
            print e
    else:
        raise e

    addr = INETAddress('127.0.0.1', port)
    assert addr.eq(s1.getsockname())
    s2 = RSocket(AF_INET, SOCK_DGRAM)
    s2.settimeout(10.0) # test one side with timeouts so select is used, shouldn't affect test
    s2.bind(INETAddress('127.0.0.1', INADDR_ANY))
    addr2 = s2.getsockname()

    s1.sendto('?', 0, addr2)
    buf = s2.recv(100)
    assert buf == '?'
    s2.connect(addr)
    count = s2.send('x'*99)
    assert 1 <= count <= 99
    buf, addr3 = s1.recvfrom(100)
    assert buf == 'x'*count
    print addr2, addr3
    assert addr2.get_port() == addr3.get_port()
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
        except SocketError as e:   # should get a "Permission denied"
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

    fd1, addr2 = sock.accept()
    s1 = RSocket(fd=fd1)
    s1.setblocking(False)
    assert addr.eq(s2.getpeername())
    assert addr2.get_port() == s2.getsockname().get_port()
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
    # The following might fail if the DNS redirects failed requests to a
    # catch-all address (i.e. opendns).
    e = py.test.raises(GAIError, getaddrinfo, 'www.very-invalidaddress.com', None)
    assert isinstance(e.value.get_msg(), str)

def getaddrinfo_pydotorg(i, result):
    lst = getaddrinfo('python.org', None)
    assert isinstance(lst, list)
    found = False
    for family, socktype, protocol, canonname, addr in lst:
        if addr.get_host() in ('104.130.43.121', '23.253.135.79'):
            found = True
        elif family == AF_INET:
            print 'pydotorg changed to', addr.get_host()
    result[i] += found

def test_getaddrinfo_pydotorg():
    result = [0,]
    getaddrinfo_pydotorg(0, result)
    assert result[0] == 1


def test_getaddrinfo_no_reverse_lookup():
    # It seems that getaddrinfo never runs a reverse lookup on Linux.
    # Python2.3 on Windows returns the hostname.
    lst = getaddrinfo('82.94.164.162', None, flags=AI_NUMERICHOST)
    assert isinstance(lst, list)
    found = False
    print lst
    for family, socktype, protocol, canonname, addr in lst:
        assert 'python.org' not in canonname
        if addr.get_host() == '82.94.164.162':
            found = True
    assert found, lst

def test_getaddrinfo_osx_crash():
    # see CPython issue17269
    for port in [None, '0', '00']:
        getaddrinfo('localhost', port, 0, 0, 0, AI_NUMERICSERV)

def test_connect_ex():
    s = RSocket()
    err = s.connect_ex(INETAddress('0.0.0.0', 0))   # should not work
    assert err in (errno.ECONNREFUSED, errno.EADDRNOTAVAIL)
    s.close()

def test_connect_with_timeout_fail():
    s = RSocket()
    s.settimeout(0.1)
    with py.test.raises(SocketTimeout):
        s.connect(INETAddress('172.30.172.30', 12345))
    s.close()

def test_connect_with_timeout_succeed():
    s = RSocket()
    s.settimeout(10.0)
    s.connect(INETAddress('python.org', 80))
    s.close()

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
    s = RSocket(AF_INET, SOCK_STREAM)
    try:
        s.bind(INETAddress('localhost', 50007))
        if sys.platform == "win32":
            assert not hasattr(s, 'dup')
            return
        s2 = s.dup()
        try:
            assert s.fd != s2.fd
            assert s.getsockname().eq(s2.getsockname())
        finally:
            s2.close()
    finally:
        s.close()

def test_c_dup():
    # rsocket.dup() duplicates fd, it also works on Windows
    # (but only on socket handles!)
    s = RSocket(AF_INET, SOCK_STREAM)
    try:
        s.bind(INETAddress('localhost', 50007))
        s2 = RSocket(fd=dup(s.fd))
        try:
            assert s.fd != s2.fd
            assert s.getsockname().eq(s2.getsockname())
        finally:
            s2.close()
    finally:
        s.close()

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
    if not hasattr(rsocket, 'inet_pton'):
        py.test.skip("no inet_pton()")
    assert inet_pton(AF_INET, '1.2.3.5') == '\x01\x02\x03\x05'
    py.test.raises(SocketError, inet_pton, AF_INET, '127.0.0.256')

def test_inet_ntop():
    if not hasattr(rsocket, 'inet_ntop'):
        py.test.skip("no inet_ntop()")
    assert inet_ntop(AF_INET, '\x01\x02\x03\x05') == '1.2.3.5'

def test_unix_socket_connect():
    if getattr(rsocket, 'AF_UNIX', None) is None:
        py.test.skip('AF_UNIX not supported.')
    from rpython.tool.udir import udir
    sockpath = str(udir.join('test_unix_socket_connect'))
    a = UNIXAddress(sockpath)

    serversock = RSocket(AF_UNIX)
    serversock.bind(a)
    serversock.listen(1)

    clientsock = RSocket(AF_UNIX)
    clientsock.connect(a)
    fd, addr = serversock.accept()
    s = RSocket(AF_UNIX, fd=fd)

    s.send('X')
    data = clientsock.recv(100)
    assert data == 'X'
    clientsock.send('Y')
    data = s.recv(100)
    assert data == 'Y'

    clientsock.close()
    s.close()

class TestTCP:
    PORT = 50007
    HOST = 'localhost'

    def setup_method(self, method):
        self.serv = RSocket(AF_INET, SOCK_STREAM)
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

def _test_cond_include(cond):
    # Test that _rsocket_rffi is importable even on platforms where
    # AF_PACKET or AF_NETLINK is not defined.
    import re
    from rpython.rlib import _rsocket_rffi
    srcfile = _rsocket_rffi.__file__
    if srcfile.lower().endswith('c') or srcfile.lower().endswith('o'):
        srcfile = srcfile[:-1]      # .pyc => .py
    assert srcfile.lower().endswith('.py')
    sourcelines = open(srcfile, 'rb').read().splitlines()
    found = False
    for i, line in enumerate(sourcelines):
        line2 = re.sub(r"(\s*COND_HEADER\s*=)",
                      r"\1'#undef %s\\n'+" % cond,
                      line)
        if line2 != line:
            found = True
            sourcelines[i] = line2
    assert found
    d = {}
    sourcelines.append('')
    exec '\n'.join(sourcelines) in d

def test_no_AF_PACKET():
    _test_cond_include('AF_PACKET')

def test_no_AF_NETLINK():
    _test_cond_include('AF_NETLINK')

def test_thread_safe_gethostbyaddr():
    py.test.skip("hits non-thread-safe issues with ll2ctypes")
    import threading
    nthreads = 10
    ip = '8.8.8.8'
    domain = gethostbyaddr(ip)[0]
    result = [0] * nthreads
    threads = [None] * nthreads
    lock = threading.Lock()
    def lookup_addr(ip, i):
        name, aliases, address_list = gethostbyaddr(ip, lock)
        if name == domain:
            result[i] += 1
    for i in range(nthreads):
        threads[i] = threading.Thread(target = lookup_addr, args=[ip, i])
        threads[i].start()
    for i in range(nthreads):
        threads[i].join()
    assert sum(result) == nthreads

def test_thread_safe_gethostbyname_ex():
    py.test.skip("hits non-thread-safe issues with ll2ctypes")
    import threading
    nthreads = 10
    domain = 'google.com'
    result = [0] * nthreads
    threads = [None] * nthreads
    lock = threading.Lock()
    def lookup_name(i):
        name, aliases, address_list = gethostbyname_ex(domain, lock)
        if name == domain:
            result[i] += 1
    for i in range(nthreads):
        threads[i] = threading.Thread(target = lookup_name, args=[i])
        threads[i].start()
    for i in range(nthreads):
        threads[i].join()
    assert sum(result) == nthreads

def test_getaddrinfo_pydotorg_threadsafe():
    py.test.skip("hits non-thread-safe issues with ll2ctypes")
    import threading
    nthreads = 10
    result = [0] * nthreads
    threads = [None] * nthreads
    for i in range(nthreads):
        threads[i] = threading.Thread(target = getaddrinfo_pydotorg, args=[i, result])
        threads[i].start()
    for i in range(nthreads):
        threads[i].join()
    assert sum(result) == nthreads

def test_translate_netdb_lock():
    def f():
        rsocket_startup()
        gethostbyaddr("localhost")
        return 0
    fc = compile(f, [])
    assert fc() == 0

def test_translate_netdb_lock_thread():
    def f():
        rsocket_startup()
        gethostbyaddr("localhost")
        return 0
    fc = compile(f, [], thread=True)
    assert fc() == 0

def test_socket_saves_errno(tmpdir):
    # ensure errno is set to a known value...
    unconnected_sock = RSocket()
    e = py.test.raises(CSocketError, unconnected_sock.recv, 1024)
    # ...which is ENOTCONN
    assert e.value.errno == errno.ENOTCONN

    e = py.test.raises(CSocketError,
                       RSocket,
                       family=AF_INET, type=SOCK_STREAM, proto=SOL_UDP)
    assert e.value.errno in (errno.EPROTOTYPE, errno.EPROTONOSUPPORT)

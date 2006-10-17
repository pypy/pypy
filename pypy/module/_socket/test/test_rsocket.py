import py
from pypy.module._socket.rsocket import *
from pypy.module._socket.rsocket import _c

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
    a = UNIXAddress("/tmp/socketname")
    assert a.get_path() == "/tmp/socketname"

def test_gethostname():
    s = gethostname()
    assert isinstance(s, str)

def test_gethostbyname():
    a = gethostbyname('localhost')
    assert isinstance(a, INETAddress)
    assert a.get_host() == "127.0.0.1"

def test_socketpair():
    s1, s2 = socketpair()
    s1.send('?')
    buf = s2.recv(100)
    assert buf == '?'
    count = s2.send('x'*50000)
    buf = s1.recv(50000)
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
        except CSocketError, e:   # should get a "Permission denied"
            print e
    else:
        raise e

    addr = INETAddress('127.0.0.1', port)
    assert addr.eq(sock.getsockname())
    sock.listen(1)
    s2 = RSocket(_c.AF_INET, _c.SOCK_STREAM)
    thread.start_new_thread(s2.connect, (addr,))
    s1, addr2 = sock.accept()
    assert addr.eq(s2.getpeername())
    assert addr2.eq(s2.getsockname())
    assert addr2.eq(s1.getpeername())

    s1.send('?')
    buf = s2.recv(100)
    assert buf == '?'
    count = s2.send('x'*50000)
    buf = s1.recv(50000)
    assert buf == 'x'*count
    s1.close()
    s2.close()

def test_simple_udp():
    s1 = RSocket(_c.AF_INET, _c.SOCK_DGRAM)
    try_ports = [1023] + range(20000, 30000, 437)
    for port in try_ports:
        print 'binding to port %d:' % (port,),
        try:
            s1.bind(INETAddress('127.0.0.1', port))
            print 'works'
            break
        except CSocketError, e:   # should get a "Permission denied"
            print e
    else:
        raise e

    addr = INETAddress('127.0.0.1', port)
    assert addr.eq(s1.getsockname())
    s2 = RSocket(_c.AF_INET, _c.SOCK_DGRAM)
    s2.connect(addr)
    addr2 = s2.getsockname()

    s1.sendto('?', 0, addr2)
    buf = s2.recv(100)
    assert buf == '?'
    count = s2.send('x'*50000)
    buf, addr3 = s1.recvfrom(50000)
    assert buf == 'x'*count
    assert addr3.eq(addr2)
    s1.close()
    s2.close()

# -*- coding: utf-8 -*-
import os
import socket
import pytest
from rpython.tool.udir import udir
from rpython.rlib import rsocket
from rpython.rtyper.lltypesystem import lltype, rffi

@pytest.fixture
def spaceconfig():
    return {'usemodules': ['_socket', 'array', 'struct', 'unicodedata']}

@pytest.fixture
def w_socket(space):
    return space.appexec([], "(): import _socket as m; return m")

def test_gethostname(space, w_socket):
    host = space.appexec([w_socket], "(_socket): return _socket.gethostname()")
    assert space.unwrap(host) == socket.gethostname()

def test_gethostbyname(space, w_socket):
    for host in ["localhost", "127.0.0.1"]:
        ip = space.appexec([w_socket, space.wrap(host)],
                           "(_socket, host): return _socket.gethostbyname(host)")
        assert space.unwrap(ip) == socket.gethostbyname(host)

def test_gethostbyname_ex(space, w_socket):
    for host in ["localhost", "127.0.0.1"]:
        ip = space.appexec([w_socket, space.wrap(host)],
                           "(_socket, host): return _socket.gethostbyname_ex(host)")
        assert space.unwrap(ip) == socket.gethostbyname_ex(host)

def test_gethostbyaddr(space, w_socket):
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

def test_getservbyname(space, w_socket):
    name = "smtp"
    # 2 args version
    port = space.appexec([w_socket, space.wrap(name)],
                        "(_socket, name): return _socket.getservbyname(name, 'tcp')")
    assert space.unwrap(port) == 25
    # 1 arg version
    port = space.appexec([w_socket, space.wrap(name)],
                        "(_socket, name): return _socket.getservbyname(name)")
    assert space.unwrap(port) == 25

def test_getservbyport(space, w_socket):
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

def test_getprotobyname(space, w_socket):
    name = "tcp"
    w_n = space.appexec([w_socket, space.wrap(name)],
                        "(_socket, name): return _socket.getprotobyname(name)")
    assert space.unwrap(w_n) == socket.IPPROTO_TCP

@pytest.mark.skipif("not hasattr(socket, 'fromfd')")
@pytest.mark.skipif("sys.platform=='win32'")
def test_ntohs(space, w_socket):
    w_n = space.appexec([w_socket, space.wrap(125)],
                        "(_socket, x): return _socket.ntohs(x)")
    assert space.unwrap(w_n) == socket.ntohs(125)

def test_ntohl(space, w_socket):
    w_n = space.appexec([w_socket, space.wrap(125)],
                        "(_socket, x): return _socket.ntohl(x)")
    assert space.unwrap(w_n) == socket.ntohl(125)
    w_n = space.appexec([w_socket, space.wrap(0x89abcdef)],
                        "(_socket, x): return _socket.ntohl(x)")
    assert space.unwrap(w_n) in (0x89abcdef, 0xefcdab89)
    space.raises_w(space.w_OverflowError, space.appexec,
                   [w_socket, space.wrap(1 << 32)],
                   "(_socket, x): return _socket.ntohl(x)")

def test_htons(space, w_socket):
    w_n = space.appexec([w_socket, space.wrap(125)],
                        "(_socket, x): return _socket.htons(x)")
    assert space.unwrap(w_n) == socket.htons(125)

def test_htonl(space, w_socket):
    w_n = space.appexec([w_socket, space.wrap(125)],
                        "(_socket, x): return _socket.htonl(x)")
    assert space.unwrap(w_n) == socket.htonl(125)
    w_n = space.appexec([w_socket, space.wrap(0x89abcdef)],
                        "(_socket, x): return _socket.htonl(x)")
    assert space.unwrap(w_n) in (0x89abcdef, 0xefcdab89)
    space.raises_w(space.w_OverflowError, space.appexec,
                   [w_socket, space.wrap(1 << 32)],
                   "(_socket, x): return _socket.htonl(x)")

def test_aton_ntoa(space, w_socket):
    ip = '123.45.67.89'
    packed = socket.inet_aton(ip)
    w_p = space.appexec([w_socket, space.wrap(ip)],
                        "(_socket, ip): return _socket.inet_aton(ip)")
    assert space.bytes_w(w_p) == packed
    w_ip = space.appexec([w_socket, w_p],
                         "(_socket, p): return _socket.inet_ntoa(p)")
    assert space.utf8_w(w_ip) == ip

@pytest.mark.skipif("not hasattr(socket, 'inet_pton')")
def test_pton_ntop_ipv4(space, w_socket):
    tests = [
        ("123.45.67.89", "\x7b\x2d\x43\x59"),
        ("0.0.0.0", "\x00" * 4),
        ("255.255.255.255", "\xff" * 4),
    ]
    for ip, packed in tests:
        w_p = space.appexec([w_socket, space.wrap(ip)], """(_socket, ip):
            return _socket.inet_pton(_socket.AF_INET, ip)""")
        assert space.unwrap(w_p) == packed
        w_ip = space.appexec([w_socket, w_p], """(_socket, p):
            return _socket.inet_ntop(_socket.AF_INET, p)""")
        assert space.unwrap(w_ip) == ip

def test_ntop_ipv6(space, w_socket):
    if not hasattr(socket, 'inet_pton'):
        pytest.skip('No socket.inet_pton on this platform')
    if not socket.has_ipv6:
        pytest.skip("No IPv6 on this platform")
    tests = [
        (b"\x00" * 16, "::"),
        (b"\x01" * 16, ":".join(["101"] * 8)),
        (b"\x00\x00\x10\x10" * 4, None),  # "::1010:" + ":".join(["0:1010"] * 3)),
        (b"\x00" * 12 + "\x01\x02\x03\x04", "::1.2.3.4"),
        (b"\x00" * 10 + "\xff\xff\x01\x02\x03\x04", "::ffff:1.2.3.4"),
    ]
    for packed, ip in tests:
        w_ip = space.appexec([w_socket, space.newbytes(packed)],
            "(_socket, packed): return _socket.inet_ntop(_socket.AF_INET6, packed)")
        if ip is not None:   # else don't check for the precise representation
            assert space.unwrap(w_ip) == ip
        w_packed = space.appexec([w_socket, w_ip],
            "(_socket, ip): return _socket.inet_pton(_socket.AF_INET6, ip)")
        assert space.unwrap(w_packed) == packed

def test_pton_ipv6(space, w_socket):
    import sys
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
        ("\x00" * 12 + "\x01\x02\x03\x04", "::1.2.3.4"),
        ("\x00" * 10 + "\xff\xff\x01\x02\x03\x04", "::ffff:1.2.3.4"),
    ]
    if sys.platform != 'win32':
        tests.append(
            ("\x00\x00\x10\x10" * 4, "::1010:" + ":".join(["0:1010"] * 3))
        )
    for packed, ip in tests:
        w_packed = space.appexec([w_socket, space.wrap(ip)],
            "(_socket, ip): return _socket.inet_pton(_socket.AF_INET6, ip)")
        assert space.unwrap(w_packed) == packed

def test_getaddrinfo(space, w_socket):
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
    w_l = space.appexec([w_socket, space.newbytes(host), space.wrap(u'\uD800')], '''

       (_socket, host, port):
            try:
                info = _socket.getaddrinfo(host, port)
            except Exception as e:
                return e.reason == 'surrogates not allowed'
            return -1
        ''')
    assert space.unwrap(w_l) == True

def test_getaddrinfo_ipv6(space, w_socket):
    host = 'fe80::1%1'
    port = 80
    w_l = space.appexec([w_socket, space.newtext(host), space.newint(port)],
                        "(_socket, host, port): return _socket.getaddrinfo(host, port)")
    w_tup = space.getitem(w_l, space.newint(0))
    w_tup2 = space.getitem(w_tup, space.newint(4))
    w_canon = space.getitem(w_tup2, space.newint(0))
    canon_name = space.text_w(w_canon)
    # Make sure the scope ID (the `%1` part) is removed (issue 3628, 3938)
    assert '%' not in canon_name

@pytest.mark.skipif("not hasattr(socket, 'sethostname')")
def test_sethostname(space, w_socket):
    space.raises_w(space.w_OSError, space.appexec,
                   [w_socket],
                   "(_socket): _socket.sethostname(_socket.gethostname())")


@pytest.mark.skipif("not hasattr(socket, 'sethostname')")
def test_sethostname_bytes(space, w_socket):
    space.raises_w(space.w_OSError, space.appexec,
                   [w_socket],
                   "(_socket): _socket.sethostname(_socket.gethostname().encode())")


def test_unknown_addr_as_object(space, ):
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
    assert space.text_w(space.getitem(w_obj, space.wrap(1))) == 'c'

def test_addr_raw_packet(space, ):
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
    c_addr_ll.c_sll_addr[0] = rffi.r_uchar(ord('a'))
    c_addr_ll.c_sll_addr[1] = rffi.r_uchar(ord('b'))
    c_addr_ll.c_sll_addr[2] = rffi.r_uchar(ord('c'))
    rffi.setintfield(c_addr, 'c_sa_family', socket.AF_PACKET)
    # fd needs to be somehow valid
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    fd = s.fileno()
    w_obj = addr_as_object(rsocket.make_address(c_addr, addrlen), fd, space)
    lltype.free(c_addr_ll, flavor='raw')
    assert space.is_true(space.eq(w_obj, space.newtuple([
        space.newtext('lo'),
        space.newint(socket.ntohs(8)),
        space.newint(13),
        space.newbool(False),
        space.newbytes("abc"),
    ])))

def test_getnameinfo(space, w_socket):
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

def test_timeout(space, w_socket):
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

def test_type(space, w_socket):
    w_bool = space.appexec([w_socket],
                    """(_socket,):
                    if not hasattr(_socket, 'SOCK_CLOEXEC'):
                        return -1
                    s = _socket.socket(_socket.AF_INET,
                                    _socket.SOCK_STREAM | _socket.SOCK_CLOEXEC)
                    return s.type == _socket.SOCK_STREAM
                    """)
    assert(space.bool_w(w_bool))


from pypy.objspace.std import StdObjSpace
from pypy.tool.udir import udir
import py
import socket, sys

def setup_module(mod):
    mod.space = StdObjSpace(usemodules=['_socket'])
    mod.w_socket = space.appexec([], "(): import _socket as m; return m")
    mod.path = udir.join('fd')
    mod.path.write('fo')

def test_gethostname():
    host = space.appexec([w_socket], "(_socket): return _socket.gethostname()")
    assert space.unwrap(host) == socket.gethostname()

def test_gethostbyname():
    host = "localhost"
    ip = space.appexec([w_socket, space.wrap(host)],
                       "(_socket, host): return _socket.gethostbyname(host)")
    assert space.unwrap(ip) == socket.gethostbyname(host)

def test_gethostbyname_ex():
    host = "localhost"
    ip = space.appexec([w_socket, space.wrap(host)],
                       "(_socket, host): return _socket.gethostbyname_ex(host)")
    assert isinstance(space.unwrap(ip), tuple)
    assert space.unwrap(ip) == socket.gethostbyname_ex(host)

def test_gethostbyaddr():
    host = "localhost"
    ip = space.appexec([w_socket, space.wrap(host)],
                       "(_socket, host): return _socket.gethostbyaddr(host)")
    assert space.unwrap(ip) == socket.gethostbyaddr(host)
    host = "127.0.0.1"
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
        py.test.skip("getservbyname second argument is not optional before python 2.4")
    port = space.appexec([w_socket, space.wrap(name)],
                        "(_socket, name): return _socket.getservbyname(name)")
    assert space.unwrap(port) == 25

def test_getservbyport():
    if sys.version_info < (2, 4):
        py.test.skip("getservbyport does not exist before python 2.4")
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

def test_getprotobyname():
    name = "tcp"
    w_n = space.appexec([w_socket, space.wrap(name)],
                        "(_socket, name): return _socket.getprotobyname(name)")
    assert space.unwrap(w_n) == socket.IPPROTO_TCP

def test_fromfd():
    # XXX review
    if not hasattr(socket, 'fromfd'):
        py.test.skip("No socket.fromfd on this platform")
    orig_fd = path.open()
    fd = space.appexec([w_socket, space.wrap(orig_fd.fileno()),
            space.wrap(socket.AF_INET), space.wrap(socket.SOCK_STREAM),
            space.wrap(0)],
           """(_socket, fd, family, type, proto): 
                 return _socket.fromfd(fd, family, type, proto)""")

    assert space.unwrap(fd).fileno()
    fd = space.appexec([w_socket, space.wrap(orig_fd.fileno()),
            space.wrap(socket.AF_INET), space.wrap(socket.SOCK_STREAM)],
                """(_socket, fd, family, type):
                    return _socket.fromfd(fd, family, type)""")

    assert space.unwrap(fd).fileno()

def test_ntohs():
    w_n = space.appexec([w_socket, space.wrap(125)],
                        "(_socket, x): return _socket.ntohs(x)")
    assert space.unwrap(w_n) == socket.ntohs(125)

def test_ntohl():
    w_n = space.appexec([w_socket, space.wrap(125)],
                        "(_socket, x): return _socket.ntohl(x)")
    assert space.unwrap(w_n) == socket.ntohl(125)

def test_htons():
    w_n = space.appexec([w_socket, space.wrap(125)],
                        "(_socket, x): return _socket.htons(x)")
    assert space.unwrap(w_n) == socket.htons(125)

def test_htonl():
    w_n = space.appexec([w_socket, space.wrap(125)],
                        "(_socket, x): return _socket.htonl(x)")
    assert space.unwrap(w_n) == socket.htonl(125)

def test_packed_ip():
    ip = '123.45.67.89'
    packed = socket.inet_aton(ip)
    w_p = space.appexec([w_socket, space.wrap(ip)],
                        "(_socket, ip): return _socket.inet_aton(ip)")
    assert space.unwrap(w_p) == packed
    w_ip = space.appexec([w_socket, space.wrap(packed)],
                         "(_socket, p): return _socket.inet_ntoa(p)")
    assert space.unwrap(w_ip) == ip

def test_pton():
    ip = '123.45.67.89'
    packed = socket.inet_aton(ip)
    if not hasattr(socket, 'inet_pton'):
        py.test.skip('No socket.(inet_pton|inet_ntop) on this platform')
    w_p = space.appexec([w_socket, space.wrap(ip)],
                        "(_socket, ip): return _socket.inet_pton(_socket.AF_INET, ip)")
    assert space.unwrap(w_p) == packed
    w_ip = space.appexec([w_socket, space.wrap(packed)],
                         "(_socket, p): return _socket.inet_ntop(_socket.AF_INET, p)")
    assert space.unwrap(w_ip) == ip

def test_has_ipv6():
    res = space.appexec([w_socket], "(_socket): return _socket.has_ipv6")
    assert space.unwrap(res) == socket.has_ipv6

def test_getaddrinfo():
    host = "localhost"
    port = 25
    info = socket.getaddrinfo(host, port)
    w_l = space.appexec([w_socket, space.wrap(host), space.wrap(port)],
                        "(_socket, host, port): return _socket.getaddrinfo(host, port)")
    assert space.unwrap(w_l) == info
    py.test.skip("Too long...")
    w_l = space.appexec([w_socket, space.wrap(unicode(host)), space.wrap(port)],
                        "(_socket, host, port): return _socket.getaddrinfo(host, port)")
    assert space.unwrap(w_l) == info
    
def test_getnameinfo():
    host = "localhost"
    port = 25
    info = socket.getnameinfo((host, port), 0)
    w_l = space.appexec([w_socket, space.wrap(host), space.wrap(port)],
                        "(_socket, host, port): return _socket.getnameinfo((host, port), 0)")
    assert space.unwrap(w_l) == info

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
    
    
    
    


import _socket
import pypy.module._socket.rpython.exttable
from pypy.module._socket.rpython.ll__socket import *
from pypy.translator.annrpython import RPythonAnnotator
from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.module.support import from_rstr
from pypy.rpython.module.support import to_opaque_object, from_opaque_object

def test_ntohs():
    def fn():
        return _socket.ntohs(1)
    a = RPythonAnnotator()
    res = interpret(fn, [])
    assert res == _socket.ntohs(1)

def test_gethostname():
    def fn():
        return _socket.gethostname()
    a = RPythonAnnotator()
    res = interpret(fn, [])
    assert from_rstr(res) == _socket.gethostname()

def test_getaddrinfo():
    host = "localhost"
    port = 25
    result = []
    addr = ll__socket_getaddrinfo(to_rstr(host), port, 0, 0, 0, 0)
    info = ll__socket_nextaddrinfo(addr)
    info = info[:4] + (info[4:],)
    assert info == _socket.getaddrinfo(host, port)[0]

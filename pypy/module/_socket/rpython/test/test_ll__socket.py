
import _socket
import pypy.module._socket.rpython.exttable
from pypy.module._socket.rpython.ll__socket import *
from pypy.translator.annrpython import RPythonAnnotator
from pypy.rpython.test.test_llinterp import interpret

def test_ntohs():
    def fn():
        return _socket.ntohs(1)
    a = RPythonAnnotator()
    res = interpret(fn, [])
    assert res == _socket.ntohs(1)

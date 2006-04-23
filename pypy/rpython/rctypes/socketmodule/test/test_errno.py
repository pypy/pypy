import errno
import py.test
from pypy.rpython.rctypes.socketmodule._socket import *

def test_connect_error():
    s = socket()
    # This should be refused
    e = py.test.raises(error, s.connect, ('127.0.0.1', 1000))
    assert e.value.args[0] == errno.ECONNREFUSED

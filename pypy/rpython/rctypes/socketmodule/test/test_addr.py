import py
from pypy.rpython.rctypes.socketmodule._socket import *

def test_getaddrinfo():
    lst = getaddrinfo('snake.cs.uni-duesseldorf.de', None)
    assert isinstance(lst, list)
    found = False
    for family, socktype, protocol, canonname, (host, port) in lst:
        if host == '134.99.112.214':
            found = True
    assert found, lst

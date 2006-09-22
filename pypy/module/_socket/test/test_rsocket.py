import py
from pypy.module._socket.rsocket import *

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

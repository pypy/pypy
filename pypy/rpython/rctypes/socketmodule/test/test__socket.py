import py
import _socket, errno
from pypy.rpython.rctypes.socketmodule import _socket as _rsocket

def interface_matcher(interface1, interface2):
    members = [member for member in dir(interface1) if not member.startswith('_')]
    verifying_set = dir(interface2)
    for member in members:
        assert member in verifying_set

def test_interfaces():
    #interface_matcher(_socket, _rsocket)
    #interface_matcher(_rsocket, _socket)
    interface_matcher(_socket.socket, _rsocket.socket)
    interface_matcher(_rsocket.socket, _socket.socket)

def test_accept():
    s = _rsocket.socket(_rsocket.AF_INET, _rsocket.SOCK_STREAM,
                        _socket.IPPROTO_TCP)
    e = py.test.raises(_rsocket.error, s.accept).value
    assert e.args[0] == errno.EINVAL
    

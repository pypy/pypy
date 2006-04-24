import py
import _socket, errno, thread
from pypy.rpython.rctypes.socketmodule import _socket as _rsocket
from pypy.module._socket.test import echoserver

def interface_matcher(interface1, interface2):
    members = [member for member in dir(interface1) if member != "CAPI" and not member.startswith('_')]
    verifying_set = dir(interface2)
    for member in members:
        assert member in verifying_set

def test_interfaces():
    py.test.skip("In progress.")
    interface_matcher(_socket, _rsocket)
    interface_matcher(_rsocket, _socket)
    interface_matcher(_socket.socket, _rsocket.socket)
    interface_matcher(_rsocket.socket, _socket.socket)

class TestSocket:

    HOST = "127.0.0.1"
    PORT = echoserver.PORT
    family = _socket.AF_INET
    
    def setup_class(cls):    
        thread.start_new_thread(echoserver.start_server, (),
                                            {"address_family": cls.family})
        import time
        time.sleep(1)
    def teardown_class(cls):
        import telnetlib
        tn = telnetlib.Telnet(cls.HOST, cls.PORT)
        tn.write("shutdown\n")
        tn.close()

    def test_accept_no_bind(self):
        s = _rsocket.socket(_rsocket.AF_INET, _rsocket.SOCK_STREAM,
                            _socket.IPPROTO_TCP)
        e = py.test.raises(_rsocket.error, s.accept).value
        assert e.args[0] == errno.EINVAL
    
    def test_getpeername(self):
        s = _rsocket.socket(self.family, _socket.SOCK_STREAM, 0)
        s.connect((self.HOST, self.PORT))
        sockname = s.getpeername()
        s.close()
        host, port = sockname
        assert host == self.HOST
        assert port == self.PORT
        


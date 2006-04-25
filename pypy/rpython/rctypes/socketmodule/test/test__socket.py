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

class TestSocketWithServer:

    HOST = "127.0.0.1"
    PORT = echoserver.PORT
    family = _socket.AF_INET
    
    def setup_class(self):
        self.server = echoserver.create_server()
        thread.start_new_thread(self.server.serve, (),
                                            {"address_family": self.family})
        
    def teardown_class(self):
        import telnetlib
        tn = telnetlib.Telnet(self.HOST, self.PORT)
        tn.write("shutdown\n")
        tn.close()

    def test_accept_no_bind(self):
        s = _rsocket.socket(_rsocket.AF_INET, _rsocket.SOCK_STREAM,
                            _socket.IPPROTO_TCP)
        e = py.test.raises(_rsocket.error, s.accept).value
        assert e.args[0] == errno.EINVAL
    
    def test_getpeername(self):
        s = _rsocket.socket(self.family, _rsocket.SOCK_STREAM, 0)
        s.connect((self.HOST, self.PORT))
        sockname = s.getpeername()
        s.close()
        host, port = sockname
        assert host == self.HOST
        assert port == self.PORT

    
class TestSocket:
    HOST = "127.0.0.1"
    PORT = 1025
    ADDR = (HOST, PORT)

    def connecting_client(self, addr):
        socket = __import__("socket", {}, {}, [])
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(addr)
        self.client_addr = s.getsockname()
        s.send("@")
        self.received = s.recv(1024)
        while data:
            self.received += s.recv(1024)
        s.close()

    def test_getsockname(self):
        s = _rsocket.socket(_rsocket.AF_INET, _rsocket.SOCK_STREAM, 0)
        s.bind(self.ADDR)
        sockname = s.getsockname()
        s.close()
        assert sockname == self.ADDR

    def test_accept(self):
        s = _rsocket.socket(_rsocket.AF_INET, _rsocket.SOCK_STREAM, 0)
        s.bind((self.HOST, 0))
        s.listen(1)
        ADDR = s.getsockname()
        thread.start_new_thread(self.connecting_client, (ADDR,))
        client, clientaddr = s.accept()
        res = client.recv(1)
        assert res == "@"
        assert clientaddr == self.client_addr
        client.close()
        

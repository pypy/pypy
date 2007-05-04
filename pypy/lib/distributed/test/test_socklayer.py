
from pypy.conftest import gettestobjspace

# XXX think how to close the socket

class AppTestSocklayer:
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withtproxy": True,
                                       "usemodules":("_stackless","_socket", "select")})
    
    def test_socklayer(self):
        class X:
            z = 3

        x = X()

        from py.__.green.pipe.gsocket import GreenSocket
        from distributed.socklayer import socket_loop, connect
        from py.__.green.greensock2 import oneof, allof

        def one():
            socket_loop(('127.0.0.1', 21211), {'x':x}, socket=GreenSocket)

        def two():
            rp = connect(('127.0.0.1', 21211), GreenSocket)
            assert rp.get_remote('x').z == 3

        oneof(one, two)

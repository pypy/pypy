import py
from pypy.conftest import gettestobjspace

def setup_module(mod):
    py.test.importorskip("pygreen")   # found e.g. in py/trunk/contrib 

# XXX think how to close the socket

class AppTestSocklayer:
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withtproxy": True,
                                       "usemodules":("_socket", "select")})
    
    def test_socklayer(self):
        class X(object):
            z = 3

        x = X()

        try:
            import py
        except ImportError:
            skip("pylib not importable")
        from pygreen.pipe.gsocke import GreenSocket
        from distributed.socklayer import socket_loop, connect
        from pygreen.greensock2 import oneof, allof

        def one():
            socket_loop(('127.0.0.1', 21211), {'x':x}, socket=GreenSocket)

        def two():
            rp = connect(('127.0.0.1', 21211), GreenSocket)
            assert rp.x.z == 3

        oneof(one, two)

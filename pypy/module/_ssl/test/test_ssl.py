from py.test import raises, skip
from pypy.conftest import gettestobjspace
import os

class AppTestSSL:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_ssl',))
        cls.space = space

    def test_init_module(self):
        import _ssl
    
    def test_sslerror(self):
        import _ssl
        assert issubclass(_ssl.sslerror, Exception)

    def test_constants(self):
        import _ssl
        
        assert isinstance(_ssl.SSL_ERROR_ZERO_RETURN, int)
        assert isinstance(_ssl.SSL_ERROR_WANT_READ, int)
        assert isinstance(_ssl.SSL_ERROR_WANT_WRITE, int)
        assert isinstance(_ssl.SSL_ERROR_WANT_X509_LOOKUP, int)
        assert isinstance(_ssl.SSL_ERROR_SYSCALL, int)
        assert isinstance(_ssl.SSL_ERROR_SSL, int)
        assert isinstance(_ssl.SSL_ERROR_WANT_CONNECT, int)
        assert isinstance(_ssl.SSL_ERROR_EOF, int)
        assert isinstance(_ssl.SSL_ERROR_INVALID_ERROR_CODE, int)
    
    def test_RAND_add(self):
        from _ssl import RAND_add
        raises(TypeError, RAND_add, 4, 4)
        raises(TypeError, RAND_add, "xyz", "zyx")
        RAND_add("xyz", 1.2345)
    
    def test_RAND_status(self):
        import _ssl
        _ssl.RAND_status()
    
    def test_RAND_egd(self):
        from _ssl import RAND_egd
        raises(TypeError, RAND_egd, 4)
        
        # you need to install http://egd.sourceforge.net/ to test this
        # execute "egd.pl entropy" in the current dir
        RAND_egd("entropy")
    
    def test_connect(self):
        import socket
        
        # https://connect.sigen-ca.si/index-en.html
        ADDR = "connect.sigen-ca.si", 443
        s = socket.socket()
        s.connect(ADDR)
        ss = socket.ssl(s)
        s.close()
    
    def test_server_method(self):
        import socket
        ADDR = "connect.sigen-ca.si", 443
        s = socket.socket()
        s.connect(ADDR)
        ss = socket.ssl(s)
        assert isinstance(ss.server(), str)
        s.close()
    
    def test_issuer_method(self):
        import socket
        ADDR = "connect.sigen-ca.si", 443
        s = socket.socket()
        s.connect(ADDR)
        ss = socket.ssl(s)
        assert isinstance(ss.issuer(), str)
        s.close()

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
        try:
            s.connect(ADDR)
        except:
            skip("no network available or issues with connection")
        ss = socket.ssl(s)
        s.close()
    
    def test_server(self):
        import socket
        ADDR = "connect.sigen-ca.si", 443
        s = socket.socket()
        try:
            s.connect(ADDR)
        except:
            skip("no network available or issues with connection")
        ss = socket.ssl(s)
        assert isinstance(ss.server(), str)
        s.close()
    
    def test_issuer(self):
        import socket
        ADDR = "connect.sigen-ca.si", 443
        s = socket.socket()
        try:
            s.connect(ADDR)
        except:
            skip("no network available or issues with connection")
        ss = socket.ssl(s)
        assert isinstance(ss.issuer(), str)
        s.close()
        
    def test_write(self):
        import socket
        ADDR = "connect.sigen-ca.si", 443
        s = socket.socket()
        try:
            s.connect(ADDR)
        except:
            skip("no network available or issues with connection")
        ss = socket.ssl(s)
        raises(TypeError, ss.write, 123)
        num_bytes = ss.write("hello\n")
        assert isinstance(num_bytes, int)
        assert num_bytes >= 0
        s.close()
        
    def test_read(self):
        import socket
        ADDR = "connect.sigen-ca.si", 443
        s = socket.socket()
        try:
            s.connect(ADDR)
        except:
            skip("no network available or issues with connection")
        ss = socket.ssl(s)
        raises(TypeError, ss.read, "foo")
        ss.write("hello\n")
        data = ss.read()
        assert isinstance(data, str)
        s.close()

    def test_read_upto(self):
        import socket
        ADDR = "connect.sigen-ca.si", 443
        s = socket.socket()
        try:
            s.connect(ADDR)
        except:
            skip("no network available or issues with connection")
        ss = socket.ssl(s)
        raises(TypeError, ss.read, "foo")
        ss.write("hello\n")
        data = ss.read(10)
        assert isinstance(data, str)
        assert len(data) == 10
        s.close()
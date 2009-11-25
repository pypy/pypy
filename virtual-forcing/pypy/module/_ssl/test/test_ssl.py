from pypy.conftest import gettestobjspace
import os
import py

class AppTestSSL:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_ssl', '_socket'))
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
        import _ssl
        if not hasattr(_ssl, "RAND_add"):
            skip("RAND_add is not available on this machine")
        raises(TypeError, _ssl.RAND_add, 4, 4)
        raises(TypeError, _ssl.RAND_add, "xyz", "zyx")
        _ssl.RAND_add("xyz", 1.2345)
    
    def test_RAND_status(self):
        import _ssl
        if not hasattr(_ssl, "RAND_status"):
            skip("RAND_status is not available on this machine")
        _ssl.RAND_status()
    
    def test_RAND_egd(self):
        import _ssl, os, stat
        if not hasattr(_ssl, "RAND_egd"):
            skip("RAND_egd is not available on this machine")
        raises(TypeError, _ssl.RAND_egd, 4)

        # you need to install http://egd.sourceforge.net/ to test this
        # execute "egd.pl entropy" in the current dir
        if (not os.access("entropy", 0) or
            not stat.S_ISSOCK(os.stat("entropy").st_mode)):
            skip("This test needs a running entropy gathering daemon")
        _ssl.RAND_egd("entropy")

class AppTestConnectedSSL:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_ssl', '_socket'))
        cls.space = space

    def setup_method(self, method):
        # https://connect.sigen-ca.si/index-en.html
        ADDR = "connect.sigen-ca.si", 443

        self.w_s = self.space.appexec([self.space.wrap(ADDR)], """(ADDR):
            import socket
            s = socket.socket()
            try:
                s.connect(ADDR)
            except:
                skip("no network available or issues with connection")
            return s
            """)

    def test_connect(self):
        import socket
        ss = socket.ssl(self.s)
        self.s.close()

    def test_server(self):
        import socket
        ss = socket.ssl(self.s)
        assert isinstance(ss.server(), str)
        self.s.close()

    def test_issuer(self):
        import socket
        ss = socket.ssl(self.s)
        assert isinstance(ss.issuer(), str)
        self.s.close()

    def test_write(self):
        import socket
        ss = socket.ssl(self.s)
        raises(TypeError, ss.write, 123)
        num_bytes = ss.write("hello\n")
        assert isinstance(num_bytes, int)
        assert num_bytes >= 0
        self.s.close()

    def test_read(self):
        import socket
        ss = socket.ssl(self.s)
        raises(TypeError, ss.read, "foo")
        ss.write("hello\n")
        data = ss.read()
        assert isinstance(data, str)
        self.s.close()

    def test_read_upto(self):
        import socket
        ss = socket.ssl(self.s)
        raises(TypeError, ss.read, "foo")
        ss.write("hello\n")
        data = ss.read(10)
        assert isinstance(data, str)
        assert len(data) == 10
        self.s.close()

class AppTestConnectedSSL_Timeout(AppTestConnectedSSL):
    # Same tests, with a socket timeout
    # to exercise the poll() calls

    def setup_class(cls):
        space = gettestobjspace(usemodules=('_ssl', '_socket'))
        cls.space = space
        cls.space.appexec([], """():
            import socket; socket.setdefaulttimeout(1)
            """)

    def teardown_class(cls):
        cls.space.appexec([], """():
            import socket; socket.setdefaulttimeout(1)
            """)

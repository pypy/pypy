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

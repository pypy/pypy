from rpython.tool.udir import udir

class AppTestSSL:
    spaceconfig = dict(usemodules=('_ssl', '_socket', 'binascii'))

    def setup_class(cls):
        import os
        cls.w_nullbytecert = cls.space.wrap(os.path.join(
            os.path.dirname(__file__), 'nullbytecert.pem'))

    def test_init_module(self):
        import _ssl

    def test_sslerror(self):
        import _ssl, _socket
        assert issubclass(_ssl.SSLError, Exception)
        assert issubclass(_ssl.SSLError, IOError)
        assert issubclass(_ssl.SSLError, _socket.error)

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

        assert isinstance(_ssl.OPENSSL_VERSION_INFO, tuple)
        assert len(_ssl.OPENSSL_VERSION_INFO) == 5
        assert isinstance(_ssl.OPENSSL_VERSION, str)
        assert 'openssl' in _ssl.OPENSSL_VERSION.lower()

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

    def test_sslwrap(self):
        import ssl, _socket, sys, gc
        if sys.platform == 'darwin' or 'freebsd' in sys.platform:
            skip("hangs indefinitely on OSX & FreeBSD (also on CPython)")
        s = _socket.socket()
        ss = ssl.wrap_socket(s)

    def test_test_decode_nullbytecert(self):
        import _ssl
        p = _ssl._test_decode_cert(self.nullbytecert)
        subject = ((('countryName', 'US'),),
                   (('stateOrProvinceName', 'Oregon'),),
                   (('localityName', 'Beaverton'),),
                   (('organizationName', 'Python Software Foundation'),),
                   (('organizationalUnitName', 'Python Core Development'),),
                   (('commonName', 'null.python.org\x00example.org'),),
                   (('emailAddress', 'python-dev@python.org'),))
        assert p['subject'] == subject
        assert p['issuer'] == subject
        assert p['subjectAltName'] == \
            (('DNS', 'altnull.python.org\x00example.com'),
             ('email', 'null@python.org\x00user@example.org'),
             ('URI', 'http://null.python.org\x00http://example.org'),
             ('IP Address', '192.0.2.1'),
             ('IP Address', '2001:DB8:0:0:0:0:0:1\n'))


class AppTestConnectedSSL:
    spaceconfig = {
        "usemodules": ['_ssl', '_socket', 'struct', 'array', 'binascii',
                       'unicodedata'],
    }

    def setup_method(self, method):
        # https://www.verisign.net/
        ADDR = "www.verisign.net", 443

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
        import ssl, gc
        ss = ssl.wrap_socket(self.s)
        self.s.close()
        del ss; gc.collect()

    def test_write(self):
        import ssl, gc
        ss = ssl.wrap_socket(self.s)
        raises(TypeError, ss.write, 123)
        num_bytes = ss.write(b"hello\n")
        assert isinstance(num_bytes, int)
        assert num_bytes >= 0
        self.s.close()
        del ss; gc.collect()

    def test_read(self):
        import ssl, gc
        ss = ssl.wrap_socket(self.s)
        raises(TypeError, ss.read, b"foo")
        ss.write(b"hello\n")
        data = ss.read()
        assert isinstance(data, bytes)
        self.s.close()
        del ss; gc.collect()

    def test_read_upto(self):
        import ssl, gc
        ss = ssl.wrap_socket(self.s)
        raises(TypeError, ss.read, b"foo")
        ss.write(b"hello\n")
        data = ss.read(10)
        assert isinstance(data, bytes)
        assert len(data) == 10
        assert ss.pending() > 50 # many more bytes to read
        self.s.close()
        del ss; gc.collect()

    def test_read_into(self):
        import ssl, gc
        ss = ssl.wrap_socket(self.s)
        ss.write(b"hello\n")
        b = bytearray(8)
        read = ss.read(10, b)
        assert read == 8
        discard = ss.read()
        read = ss.read(10, b)
        assert read == 0
        self.s.close()
        del ss; gc.collect()

    def test_shutdown(self):
        import socket, ssl, sys, gc
        ss = ssl.wrap_socket(self.s)
        ss.write(b"hello\n")
        try:
            ss.shutdown(socket.SHUT_RDWR)
        except socket.error as e:
            if e.errno == 0:
                pass  # xxx obscure case; throwing errno 0 is pretty odd...
            raise
        raises(AttributeError, ss.write, b"hello\n")
        del ss; gc.collect()

    def test_server_hostname(self):
        import socket, _ssl, gc
        ctx = _ssl._SSLContext(_ssl.PROTOCOL_SSLv23)
        ss = ctx._wrap_socket(self.s, False,
                              server_hostname="svn.python.org")
        self.s.close()
        del ss; gc.collect()
        

class AppTestConnectedSSL_Timeout(AppTestConnectedSSL):
    # Same tests, with a socket timeout
    # to exercise the poll() calls

    def setup_class(cls):
        cls.space.appexec([], """():
            import socket; socket.setdefaulttimeout(1)
            """)

    def teardown_class(cls):
        cls.space.appexec([], """():
            import socket; socket.setdefaulttimeout(1)
            """)

class AppTestContext:
    spaceconfig = dict(usemodules=('_ssl',))

    def setup_class(cls):
        tmpfile = udir / "tmpfile.pem"
        tmpfile.write(SSL_CERTIFICATE + SSL_PRIVATE_KEY)
        cls.w_keycert = cls.space.wrap(str(tmpfile))
        tmpfile = udir / "key.pem"
        tmpfile.write(SSL_PRIVATE_KEY)
        cls.w_key = cls.space.wrap(str(tmpfile))
        tmpfile = udir / "cert.pem"
        tmpfile.write(SSL_CERTIFICATE)
        cls.w_cert = cls.space.wrap(str(tmpfile))
        tmpfile = udir / "badcert.pem"
        tmpfile.write(SSL_BADCERT)
        cls.w_badcert = cls.space.wrap(str(tmpfile))
        tmpfile = udir / "emptycert.pem"
        tmpfile.write(SSL_EMPTYCERT)
        cls.w_emptycert = cls.space.wrap(str(tmpfile))

    def test_load_cert_chain(self):
        import _ssl
        ctx = _ssl._SSLContext(_ssl.PROTOCOL_TLSv1)
        ctx.load_cert_chain(self.keycert)
        ctx.load_cert_chain(self.cert, self.key)
        raises(IOError, ctx.load_cert_chain, "inexistent.pem")
        raises(_ssl.SSLError, ctx.load_cert_chain, self.badcert)
        raises(_ssl.SSLError, ctx.load_cert_chain, self.emptycert)

    def test_load_verify_locations(self):
        import _ssl
        ctx = _ssl._SSLContext(_ssl.PROTOCOL_TLSv1)
        ctx.load_verify_locations(self.keycert)
        ctx.load_verify_locations(cafile=self.keycert, capath=None)

    def test_constructor(self):
        import _ssl
        raises(ValueError, _ssl._SSLContext, -1)
        raises(ValueError, _ssl._SSLContext, 42)

    def test_options(self):
        import _ssl
        ctx = _ssl._SSLContext(_ssl.PROTOCOL_TLSv1)
        assert _ssl.OP_ALL | _ssl.OP_NO_SSLv2 == ctx.options



SSL_CERTIFICATE = """
-----BEGIN CERTIFICATE-----
MIICVDCCAb2gAwIBAgIJANfHOBkZr8JOMA0GCSqGSIb3DQEBBQUAMF8xCzAJBgNV
BAYTAlhZMRcwFQYDVQQHEw5DYXN0bGUgQW50aHJheDEjMCEGA1UEChMaUHl0aG9u
IFNvZnR3YXJlIEZvdW5kYXRpb24xEjAQBgNVBAMTCWxvY2FsaG9zdDAeFw0xMDEw
MDgyMzAxNTZaFw0yMDEwMDUyMzAxNTZaMF8xCzAJBgNVBAYTAlhZMRcwFQYDVQQH
Ew5DYXN0bGUgQW50aHJheDEjMCEGA1UEChMaUHl0aG9uIFNvZnR3YXJlIEZvdW5k
YXRpb24xEjAQBgNVBAMTCWxvY2FsaG9zdDCBnzANBgkqhkiG9w0BAQEFAAOBjQAw
gYkCgYEA21vT5isq7F68amYuuNpSFlKDPrMUCa4YWYqZRt2OZ+/3NKaZ2xAiSwr7
6MrQF70t5nLbSPpqE5+5VrS58SY+g/sXLiFd6AplH1wJZwh78DofbFYXUggktFMt
pTyiX8jtP66bkcPkDADA089RI1TQR6Ca+n7HFa7c1fabVV6i3zkCAwEAAaMYMBYw
FAYDVR0RBA0wC4IJbG9jYWxob3N0MA0GCSqGSIb3DQEBBQUAA4GBAHPctQBEQ4wd
BJ6+JcpIraopLn8BGhbjNWj40mmRqWB/NAWF6M5ne7KpGAu7tLeG4hb1zLaldK8G
lxy2GPSRF6LFS48dpEj2HbMv2nvv6xxalDMJ9+DicWgAKTQ6bcX2j3GUkCR0g/T1
CRlNBAAlvhKzO7Clpf9l0YKBEfraJByX
-----END CERTIFICATE-----
"""

SSL_PRIVATE_KEY = """
-----BEGIN PRIVATE KEY-----
MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBANtb0+YrKuxevGpm
LrjaUhZSgz6zFAmuGFmKmUbdjmfv9zSmmdsQIksK++jK0Be9LeZy20j6ahOfuVa0
ufEmPoP7Fy4hXegKZR9cCWcIe/A6H2xWF1IIJLRTLaU8ol/I7T+um5HD5AwAwNPP
USNU0Eegmvp+xxWu3NX2m1Veot85AgMBAAECgYA3ZdZ673X0oexFlq7AAmrutkHt
CL7LvwrpOiaBjhyTxTeSNWzvtQBkIU8DOI0bIazA4UreAFffwtvEuPmonDb3F+Iq
SMAu42XcGyVZEl+gHlTPU9XRX7nTOXVt+MlRRRxL6t9GkGfUAXI3XxJDXW3c0vBK
UL9xqD8cORXOfE06rQJBAP8mEX1ERkR64Ptsoe4281vjTlNfIbs7NMPkUnrn9N/Y
BLhjNIfQ3HFZG8BTMLfX7kCS9D593DW5tV4Z9BP/c6cCQQDcFzCcVArNh2JSywOQ
ZfTfRbJg/Z5Lt9Fkngv1meeGNPgIMLN8Sg679pAOOWmzdMO3V706rNPzSVMME7E5
oPIfAkEA8pDddarP5tCvTTgUpmTFbakm0KoTZm2+FzHcnA4jRh+XNTjTOv98Y6Ik
eO5d1ZnKXseWvkZncQgxfdnMqqpj5wJAcNq/RVne1DbYlwWchT2Si65MYmmJ8t+F
0mcsULqjOnEMwf5e+ptq5LzwbyrHZYq5FNk7ocufPv/ZQrcSSC+cFwJBAKvOJByS
x56qyGeZLOQlWS2JS3KJo59XuLFGqcbgN9Om9xFa41Yb4N9NvplFivsvZdw3m1Q/
SPIXQuT8RMPDVNQ=
-----END PRIVATE KEY-----
"""
SSL_BADCERT = """
-----BEGIN RSA PRIVATE KEY-----
MIICXwIBAAKBgQC8ddrhm+LutBvjYcQlnH21PPIseJ1JVG2HMmN2CmZk2YukO+9L
opdJhTvbGfEj0DQs1IE8M+kTUyOmuKfVrFMKwtVeCJphrAnhoz7TYOuLBSqt7lVH
fhi/VwovESJlaBOp+WMnfhcduPEYHYx/6cnVapIkZnLt30zu2um+DzA9jQIDAQAB
AoGBAK0FZpaKj6WnJZN0RqhhK+ggtBWwBnc0U/ozgKz2j1s3fsShYeiGtW6CK5nU
D1dZ5wzhbGThI7LiOXDvRucc9n7vUgi0alqPQ/PFodPxAN/eEYkmXQ7W2k7zwsDA
IUK0KUhktQbLu8qF/m8qM86ba9y9/9YkXuQbZ3COl5ahTZrhAkEA301P08RKv3KM
oXnGU2UHTuJ1MAD2hOrPxjD4/wxA/39EWG9bZczbJyggB4RHu0I3NOSFjAm3HQm0
ANOu5QK9owJBANgOeLfNNcF4pp+UikRFqxk5hULqRAWzVxVrWe85FlPm0VVmHbb/
loif7mqjU8o1jTd/LM7RD9f2usZyE2psaw8CQQCNLhkpX3KO5kKJmS9N7JMZSc4j
oog58yeYO8BBqKKzpug0LXuQultYv2K4veaIO04iL9VLe5z9S/Q1jaCHBBuXAkEA
z8gjGoi1AOp6PBBLZNsncCvcV/0aC+1se4HxTNo2+duKSDnbq+ljqOM+E7odU+Nq
ewvIWOG//e8fssd0mq3HywJBAJ8l/c8GVmrpFTx8r/nZ2Pyyjt3dH1widooDXYSV
q6Gbf41Llo5sYAtmxdndTLASuHKecacTgZVhy0FryZpLKrU=
-----END RSA PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
Just bad cert data
-----END CERTIFICATE-----
-----BEGIN RSA PRIVATE KEY-----
MIICXwIBAAKBgQC8ddrhm+LutBvjYcQlnH21PPIseJ1JVG2HMmN2CmZk2YukO+9L
opdJhTvbGfEj0DQs1IE8M+kTUyOmuKfVrFMKwtVeCJphrAnhoz7TYOuLBSqt7lVH
fhi/VwovESJlaBOp+WMnfhcduPEYHYx/6cnVapIkZnLt30zu2um+DzA9jQIDAQAB
AoGBAK0FZpaKj6WnJZN0RqhhK+ggtBWwBnc0U/ozgKz2j1s3fsShYeiGtW6CK5nU
D1dZ5wzhbGThI7LiOXDvRucc9n7vUgi0alqPQ/PFodPxAN/eEYkmXQ7W2k7zwsDA
IUK0KUhktQbLu8qF/m8qM86ba9y9/9YkXuQbZ3COl5ahTZrhAkEA301P08RKv3KM
oXnGU2UHTuJ1MAD2hOrPxjD4/wxA/39EWG9bZczbJyggB4RHu0I3NOSFjAm3HQm0
ANOu5QK9owJBANgOeLfNNcF4pp+UikRFqxk5hULqRAWzVxVrWe85FlPm0VVmHbb/
loif7mqjU8o1jTd/LM7RD9f2usZyE2psaw8CQQCNLhkpX3KO5kKJmS9N7JMZSc4j
oog58yeYO8BBqKKzpug0LXuQultYv2K4veaIO04iL9VLe5z9S/Q1jaCHBBuXAkEA
z8gjGoi1AOp6PBBLZNsncCvcV/0aC+1se4HxTNo2+duKSDnbq+ljqOM+E7odU+Nq
ewvIWOG//e8fssd0mq3HywJBAJ8l/c8GVmrpFTx8r/nZ2Pyyjt3dH1widooDXYSV
q6Gbf41Llo5sYAtmxdndTLASuHKecacTgZVhy0FryZpLKrU=
-----END RSA PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
Just bad cert data
-----END CERTIFICATE-----
"""
SSL_EMPTYCERT = ""

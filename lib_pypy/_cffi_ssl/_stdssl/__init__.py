import sys
import time
import _thread
import socket
import weakref
from _pypy_openssl import ffi
from _pypy_openssl import lib
from _cffi_ssl._stdssl.certificate import (_test_decode_cert,
    _decode_certificate, _certificate_to_der)
from _cffi_ssl._stdssl.utility import (_str_with_len, _bytes_with_len,
    _str_to_ffi_buffer, _str_from_buf, _cstr_decode_fs)
from _cffi_ssl._stdssl.error import (ssl_error, pyssl_error,
        SSLError, SSLZeroReturnError, SSLWantReadError,
        SSLWantWriteError, SSLSyscallError,
        SSLEOFError)
from _cffi_ssl._stdssl.error import (SSL_ERROR_NONE,
        SSL_ERROR_SSL, SSL_ERROR_WANT_READ, SSL_ERROR_WANT_WRITE,
        SSL_ERROR_WANT_X509_LOOKUP, SSL_ERROR_SYSCALL,
        SSL_ERROR_ZERO_RETURN, SSL_ERROR_WANT_CONNECT,
        SSL_ERROR_EOF, SSL_ERROR_NO_SOCKET, SSL_ERROR_INVALID_ERROR_CODE,
        pyerr_write_unraisable)
from _cffi_ssl._stdssl import error
from select import poll, POLLIN, POLLOUT, select
from enum import IntEnum as _IntEnum

OPENSSL_VERSION = ffi.string(lib.OPENSSL_VERSION_TEXT).decode('utf-8')
OPENSSL_VERSION_NUMBER = lib.OPENSSL_VERSION_NUMBER
ver = OPENSSL_VERSION_NUMBER
ver, status = divmod(ver, 16)
ver, patch  = divmod(ver, 256)
ver, fix    = divmod(ver, 256)
ver, minor  = divmod(ver, 256)
ver, major  = divmod(ver, 256)
version_info = (major, minor, fix, patch, status)
OPENSSL_VERSION_INFO = version_info
_OPENSSL_API_VERSION = version_info
del ver, version_info, status, patch, fix, minor, major

HAS_ECDH = bool(lib.Cryptography_HAS_ECDH)
HAS_SNI = bool(lib.Cryptography_HAS_TLSEXT_HOSTNAME)
HAS_ALPN = bool(lib.Cryptography_HAS_ALPN)
HAS_NPN = bool(lib.OPENSSL_NPN_NEGOTIATED)
HAS_TLS_UNIQUE = True

CLIENT = 0
SERVER = 1

VERIFY_DEFAULT = 0
VERIFY_CRL_CHECK_LEAF = lib.X509_V_FLAG_CRL_CHECK 
VERIFY_CRL_CHECK_CHAIN = lib.X509_V_FLAG_CRL_CHECK | lib.X509_V_FLAG_CRL_CHECK_ALL
VERIFY_X509_STRICT = lib.X509_V_FLAG_X509_STRICT
if lib.Cryptography_HAS_X509_V_FLAG_TRUSTED_FIRST:
    VERIFY_X509_TRUSTED_FIRST = lib.X509_V_FLAG_TRUSTED_FIRST

CERT_NONE = 0
CERT_OPTIONAL = 1
CERT_REQUIRED = 2

for name in dir(lib):
    if name.startswith('SSL_OP'):
        globals()[name[4:]] = getattr(lib, name)

OP_ALL = lib.SSL_OP_ALL & ~lib.SSL_OP_DONT_INSERT_EMPTY_FRAGMENTS

SSL_CLIENT = 0
SSL_SERVER = 1

SSL_CB_MAXLEN=128

if lib.Cryptography_HAS_SSL2:
    PROTOCOL_SSLv2  = 0
PROTOCOL_SSLv3  = 1
PROTOCOL_SSLv23 = 2
PROTOCOL_TLS    = PROTOCOL_SSLv23
PROTOCOL_TLSv1    = 3
if lib.Cryptography_HAS_TLSv1_2:
    PROTOCOL_TLSv1 = 3
    PROTOCOL_TLSv1_1 = 4
    PROTOCOL_TLSv1_2 = 5

_PROTOCOL_NAMES = (name for name in dir(lib) if name.startswith('PROTOCOL_'))

_IntEnum._convert('_SSLMethod', __name__,
        lambda name: name.startswith('PROTOCOL_'))

if HAS_TLS_UNIQUE:
    CHANNEL_BINDING_TYPES = ['tls-unique']
else:
    CHANNEL_BINDING_TYPES = []

for name in error.SSL_AD_NAMES:
    lib_attr = 'SSL_AD_' + name
    attr = 'ALERT_DESCRIPTION_' + name
    if hasattr(lib, lib_attr):
        globals()[attr] = getattr(lib, lib_attr)

# init open ssl
lib.SSL_load_error_strings()
lib.SSL_library_init()
lib._setup_ssl_threads()
lib.OpenSSL_add_all_algorithms()

def check_signals():
    # nothing to do, we are on python level, signals are
    # checked frequently in the bytecode dispatch loop
    pass

def _socket_timeout(s):
    if s is None:
        return 0.0
    t = s.gettimeout()
    if t is None:
        return -1.0
    return t

class PasswordInfo(object):
    callable = None
    password = None
    operationerror = None
    handle = None
PWINFO_STORAGE = {}

def _Cryptography_pem_password_cb(buf, size, rwflag, userdata):
    pw_info = ffi.from_handle(userdata)

    password = pw_info.password

    if pw_info.callable:
        try:
            password = pw_info.callable()
        except Exception as e:
            pw_info.operationerror = e
            return 0

        if not isinstance(password, (str, bytes, bytearray)):
            pw_info.operationerror = TypeError("password callback must return a string")
            return 0

    password = _str_to_ffi_buffer(password)

    if (len(password) > size):
        pw_info.operationerror = ValueError("password cannot be longer than %d bytes" % size)
        return 0

    ffi.memmove(buf, password, len(password))
    return len(password)

if lib.Cryptography_STATIC_CALLBACKS:
    ffi.def_extern(_Cryptography_pem_password_cb)
    Cryptography_pem_password_cb = lib.Cryptography_pem_password_cb
else:
    Cryptography_pem_password_cb = ffi.callback("int(char*,int,int,void*)")(_Cryptography_pem_password_cb)

if hasattr(time, 'monotonic'):
    def _monotonic_clock():
        return time.monotonic()
else:
    def _monotonic_clock():
        return time.clock_gettime(time.CLOCK_MONOTONIC)

HAVE_POLL = True

def _ssl_select(sock, writing, timeout):
    if HAVE_POLL:
        p = poll()

    # Nothing to do unless we're in timeout mode (not non-blocking)
    if sock is None or timeout == 0:
        return SOCKET_IS_NONBLOCKING
    elif timeout < 0:
        t = _socket_timeout(sock)
        if t > 0:
            return SOCKET_HAS_TIMED_OUT
        else:
            return SOCKET_IS_BLOCKING

    # Guard against closed socket
    if sock.fileno() < 0:
        return SOCKET_HAS_BEEN_CLOSED

    # Prefer poll, if available, since you can poll() any fd
    # which can't be done with select().
    if HAVE_POLL:
        p.register(sock.fileno(), POLLOUT | POLLIN)

        rc = len(p.poll(timeout * 1000.0))
    else:
        # currently disabled, see HAVE_POLL
        fd = sock.fileno()
        #if (!_PyIsSelectable_fd(s->sock_fd))
        #    return SOCKET_TOO_LARGE_FOR_SELECT;
        if writing:
            rr, wr, xr = select([],[fd],[], timeout)
        else:
            rr, wr, xr = select([fd],[],[], timeout)
        rc = len(rr) + len(wr)
    if rc != 0:
        return SOCKET_OPERATION_OK
    return SOCKET_HAS_TIMED_OUT

SOCKET_IS_NONBLOCKING = 0
SOCKET_IS_BLOCKING = 1
SOCKET_HAS_TIMED_OUT = 2
SOCKET_HAS_BEEN_CLOSED = 3
SOCKET_TOO_LARGE_FOR_SELECT = 4
SOCKET_OPERATION_OK = 5

class _SSLSocket(object):

    @staticmethod
    def _new__ssl_socket(sslctx, sock, socket_type, server_hostname, inbio, outbio):
        self = _SSLSocket(sslctx)
        ctx = sslctx.ctx

        if server_hostname:
            self.server_hostname = server_hostname.decode('idna', 'strict')

        lib.ERR_get_state()
        lib.ERR_clear_error()
        self.ssl = ssl = ffi.gc(lib.SSL_new(ctx), lib.SSL_free)

        self._app_data_handle = ffi.new_handle(self)
        lib.SSL_set_app_data(ssl, ffi.cast("char*", self._app_data_handle))
        if sock:
            lib.SSL_set_fd(ssl, sock.fileno())
        else:
            # BIOs are reference counted and SSL_set_bio borrows our reference.
            # To prevent a double free in memory_bio_dealloc() we need to take an
            # extra reference here.
            lib.BIO_up_ref(inbio.bio);
            lib.BIO_up_ref(outbio.bio);
            lib.SSL_set_bio(self.ssl, inbio.bio, outbio.bio)

        mode = lib.SSL_MODE_ACCEPT_MOVING_WRITE_BUFFER
        if lib.SSL_MODE_AUTO_RETRY:
            mode |= lib.SSL_MODE_AUTO_RETRY
        lib.SSL_set_mode(ssl, mode)

        if HAS_SNI and self.server_hostname:
            name = _str_to_ffi_buffer(self.server_hostname)
            lib.SSL_set_tlsext_host_name(ssl, name)


        # If the socket is in non-blocking mode or timeout mode, set the BIO
        # to non-blocking mode (blocking is the default)
        #
        timeout = _socket_timeout(sock)
        if sock and timeout >= 0:
            lib.BIO_set_nbio(lib.SSL_get_rbio(ssl), 1)
            lib.BIO_set_nbio(lib.SSL_get_wbio(ssl), 1)

        if socket_type == SSL_CLIENT:
            lib.SSL_set_connect_state(ssl)
        else:
            lib.SSL_set_accept_state(ssl)
        self.socket_type = socket_type

        if sock:
            self.socket = weakref.ref(sock)

        return self

    def __init__(self, sslctx):
        self.ctx = sslctx
        self.peer_cert = ffi.NULL
        self.ssl = ffi.NULL
        self.shutdown_seen_zero = 0
        self.handshake_done = 0
        self._owner = None
        self.server_hostname = None
        self.socket = None

    @property
    def owner(self):
        if self._owner is None:
            return None
        return self._owner()

    @owner.setter
    def owner(self, value):
        if value is None:
            self._owner = None
        self._owner = weakref.ref(value)

    @property
    def context(self):
        return self.ctx

    @context.setter
    def context(self, value):
        if isinstance(value, _SSLContext):
            if not HAS_SNI:
                raise NotImplementedError("setting a socket's "
                        "context is not supported by your OpenSSL library")
            self.ctx = value
            lib.SSL_set_SSL_CTX(self.ssl, self.ctx.ctx);
        else:
            raise TypeError("The value must be a SSLContext")

    def do_handshake(self):
        sock = self.get_socket_or_connection_gone()
        ssl = self.ssl
        timeout = _socket_timeout(sock)
        if sock:
            nonblocking = timeout >= 0
            lib.BIO_set_nbio(lib.SSL_get_rbio(ssl), nonblocking)
            lib.BIO_set_nbio(lib.SSL_get_wbio(ssl), nonblocking)

        has_timeout = timeout > 0
        deadline = -1
        if has_timeout:
            deadline = _monotonic_clock() + timeout;
        # Actually negotiate SSL connection
        # XXX If SSL_do_handshake() returns 0, it's also a failure.
        while True:
            # allow threads
            ret = lib.SSL_do_handshake(ssl)
            err = lib.SSL_get_error(ssl, ret)
            # end allow threads

            check_signals()

            if has_timeout:
                # REIVIEW monotonic clock?
                timeout = deadline - _monotonic_clock()

            if err == SSL_ERROR_WANT_READ:
                sockstate = _ssl_select(sock, 0, timeout)
            elif err == SSL_ERROR_WANT_WRITE:
                sockstate = _ssl_select(sock, 1, timeout)
            else:
                sockstate = SOCKET_OPERATION_OK

            if sockstate == SOCKET_HAS_TIMED_OUT:
                raise socket.timeout("The handshake operation timed out")
            elif sockstate == SOCKET_HAS_BEEN_CLOSED:
                raise SSLError("Underlying socket has been closed.")
            elif sockstate == SOCKET_TOO_LARGE_FOR_SELECT:
                raise SSLError("Underlying socket too large for select().")
            elif sockstate == SOCKET_IS_NONBLOCKING:
                break
            if not (err == SSL_ERROR_WANT_READ or err == SSL_ERROR_WANT_WRITE):
                break
        if ret < 1:
            raise pyssl_error(self, ret)

        peer_cert = lib.SSL_get_peer_certificate(ssl)
        if peer_cert != ffi.NULL:
            peer_cert = ffi.gc(peer_cert, lib.X509_free)
        self.peer_cert = peer_cert

        self.handshake_done = 1
        return None

    def peer_certificate(self, binary_mode):
        if not self.handshake_done:
            raise ValueError("handshake not done yet")
        if self.peer_cert == ffi.NULL:
            return None

        if binary_mode:
            # return cert in DER-encoded format
            return _certificate_to_der(self.peer_cert)
        else:
            verification = lib.SSL_CTX_get_verify_mode(lib.SSL_get_SSL_CTX(self.ssl))
            if (verification & lib.SSL_VERIFY_PEER) == 0:
                return {}
            else:
                return _decode_certificate(self.peer_cert)

    def write(self, bytestring):
        deadline = 0
        b = _str_to_ffi_buffer(bytestring)
        sock = self.get_socket_or_connection_gone()
        ssl = self.ssl

        if len(b) > sys.maxsize:
            raise OverflowError("string longer than %d bytes" % sys.maxsize)

        timeout = _socket_timeout(sock)
        if sock:
            nonblocking = timeout >= 0
            lib.BIO_set_nbio(lib.SSL_get_rbio(ssl), nonblocking)
            lib.BIO_set_nbio(lib.SSL_get_wbio(ssl), nonblocking)


        has_timeout = timeout > 0
        if has_timeout:
            deadline = _monotonic_clock() + timeout

        sockstate = _ssl_select(sock, 1, timeout)
        if sockstate == SOCKET_HAS_TIMED_OUT:
            raise socket.timeout("The write operation timed out")
        elif sockstate == SOCKET_HAS_BEEN_CLOSED:
            raise ssl_error("Underlying socket has been closed.")
        elif sockstate == SOCKET_TOO_LARGE_FOR_SELECT:
            raise ssl_error("Underlying socket too large for select().")

        while True:
            length = lib.SSL_write(self.ssl, b, len(b))
            err = lib.SSL_get_error(self.ssl, length)

            check_signals()

            if has_timeout:
                timeout = deadline - _monotonic_clock()

            if err == SSL_ERROR_WANT_READ:
                sockstate = _ssl_select(sock, 0, timeout)
            elif err == SSL_ERROR_WANT_WRITE:
                sockstate = _ssl_select(sock, 1, timeout)
            else:
                sockstate = SOCKET_OPERATION_OK

            if sockstate == SOCKET_HAS_TIMED_OUT:
                raise socket.timeout("The write operation timed out")
            elif sockstate == SOCKET_HAS_BEEN_CLOSED:
                raise ssl_error("Underlying socket has been closed.")
            elif sockstate == SOCKET_IS_NONBLOCKING:
                break
            if not (err == SSL_ERROR_WANT_READ or err == SSL_ERROR_WANT_WRITE):
                break

        if length > 0:
            return length
        else:
            raise pyssl_error(self, length)

    def read(self, length, buffer_into=None):
        ssl = self.ssl

        if length < 0 and buffer_into is None:
            raise ValueError("size should not be negative")

        sock = self.get_socket_or_connection_gone()

        if buffer_into is None:
            dest = ffi.new("char[]", length)
            if length == 0:
                return b""
            mem = dest
        else:
            mem = ffi.from_buffer(buffer_into)
            if length <= 0 or length > len(buffer_into):
                length = len(buffer_into)
                if length > sys.maxsize:
                    raise OverflowError("maximum length can't fit in a C 'int'")
                if len(buffer_into) == 0:
                    return 0

        if sock:
            timeout = _socket_timeout(sock)
            nonblocking = timeout >= 0
            lib.BIO_set_nbio(lib.SSL_get_rbio(ssl), nonblocking)
            lib.BIO_set_nbio(lib.SSL_get_wbio(ssl), nonblocking)

        deadline = 0
        timeout = _socket_timeout(sock)
        has_timeout = timeout > 0
        if has_timeout:
            deadline = _monotonic_clock() + timeout

        shutdown = False
        while True:
            count = lib.SSL_read(self.ssl, mem, length);
            err = lib.SSL_get_error(self.ssl, count);

            check_signals()

            if has_timeout:
                timeout = deadline - _monotonic_clock()

            if err == SSL_ERROR_WANT_READ:
                sockstate = _ssl_select(sock, 0, timeout)
            elif err == SSL_ERROR_WANT_WRITE:
                sockstate = _ssl_select(sock, 1, timeout)
            elif err == SSL_ERROR_ZERO_RETURN and \
                 lib.SSL_get_shutdown(self.ssl) == lib.SSL_RECEIVED_SHUTDOWN:
                shutdown = True
                break;
            else:
                sockstate = SOCKET_OPERATION_OK

            if sockstate == SOCKET_HAS_TIMED_OUT:
                raise socket.timeout("The read operation timed out")
            elif sockstate == SOCKET_IS_NONBLOCKING:
                break
            if not (err == SSL_ERROR_WANT_READ or err == SSL_ERROR_WANT_WRITE):
                break

        if count <= 0 and not shutdown:
            raise pyssl_error(self, count)

        if not buffer_into:
            return _bytes_with_len(dest, count)

        return count

    if HAS_ALPN:
        def selected_alpn_protocol(self):
            out = ffi.new("const unsigned char **")
            outlen = ffi.new("unsigned int*")

            lib.SSL_get0_alpn_selected(self.ssl, out, outlen);
            if out[0] == ffi.NULL:
                return None
            return _str_with_len(out[0], outlen[0]);

    def shared_ciphers(self):
        ciphers = lib.SSL_get_ciphers(self.ssl)
        if ciphers == ffi.NULL:
            return None
        res = []
        count = lib.sk_SSL_CIPHER_num(ciphers)
        for i in range(count):
            tup = cipher_to_tuple(lib.sk_SSL_CIPHER_value(ciphers, i))
            if not tup:
                return None
            res.append(tup)
        return res

    def cipher(self):
        if self.ssl == ffi.NULL:
            return None
        current = lib.SSL_get_current_cipher(self.ssl)
        if current == ffi.NULL:
            return None
        return cipher_to_tuple(current)

    def compression(self):
        if not lib.Cryptography_HAS_COMPRESSION or self.ssl == ffi.NULL:
            return None

        comp_method = lib.SSL_get_current_compression(self.ssl);
        if comp_method == ffi.NULL: # or lib.SSL_COMP_get_type(comp_method) == lib.NID_undef:
            return None
        short_name = lib.SSL_COMP_get_name(comp_method)
        if short_name == ffi.NULL:
            return None
        return _cstr_decode_fs(short_name)

    def version(self):
        if self.ssl == ffi.NULL:
            return None
        version = _str_from_buf(lib.SSL_get_version(self.ssl))
        if version == "unknown":
            return None
        return version

    def get_socket_or_None(self):
        if self.socket is None:
            return None
        return self.socket()

    def get_socket_or_connection_gone(self):
        """ There are three states:
            1) self.socket is None (In C that would mean: self->Socket == NULL)
            2) self.socket() is None (-> The socket is gone)
            3) self.socket() is not None
            This method returns True if there is not weakref object allocated
        """
        if self.socket is None:
            return None
        sock = self.socket()
        if not sock:
            raise ssl_error("Underlying socket connection gone", SSL_ERROR_NO_SOCKET)
        return sock

    def shutdown(self):
        sock = self.get_socket_or_None()
        nonblocking = False
        ssl = self.ssl

        if self.socket is not None:
            # Guard against closed socket
            sock = self.socket()
            if sock is None or sock.fileno() < 0:
                raise ssl_error("Underlying socket connection gone", SSL_ERROR_NO_SOCKET)

            timeout = _socket_timeout(sock)
            nonblocking = timeout >= 0
            if sock and timeout >= 0:
                lib.BIO_set_nbio(lib.SSL_get_rbio(ssl), nonblocking)
                lib.BIO_set_nbio(lib.SSL_get_wbio(ssl), nonblocking)
        else:
            timeout = 0

        has_timeout = (timeout > 0);
        if has_timeout:
            deadline = _monotonic_clock() + timeout;

        zeros = 0

        while True:
            # Disable read-ahead so that unwrap can work correctly.
            # Otherwise OpenSSL might read in too much data,
            # eating clear text data that happens to be
            # transmitted after the SSL shutdown.
            # Should be safe to call repeatedly every time this
            # function is used and the shutdown_seen_zero != 0
            # condition is met.
            #
            if self.shutdown_seen_zero:
                lib.SSL_set_read_ahead(self.ssl, 0)
            err = lib.SSL_shutdown(self.ssl)

            # If err == 1, a secure shutdown with SSL_shutdown() is complete
            if err > 0:
                break
            if err == 0:
                # Don't loop endlessly; instead preserve legacy
                #   behaviour of trying SSL_shutdown() only twice.
                #   This looks necessary for OpenSSL < 0.9.8m
                zeros += 1
                if zeros > 1:
                    break
                # Shutdown was sent, now try receiving
                self.shutdown_seen_zero = 1
                continue

            if has_timeout:
                timeout = deadline - _monotonic_clock()

            # Possibly retry shutdown until timeout or failure
            ssl_err = lib.SSL_get_error(self.ssl, err)
            if ssl_err == SSL_ERROR_WANT_READ:
                sockstate = _ssl_select(sock, 0, timeout)
            elif ssl_err == SSL_ERROR_WANT_WRITE:
                sockstate = _ssl_select(sock, 1, timeout)
            else:
                break

            if sockstate == SOCKET_HAS_TIMED_OUT:
                if ssl_err == SSL_ERROR_WANT_READ:
                    raise socket.timeout("The read operation timed out")
                else:
                    raise socket.timeout("The write operation timed out")
            elif sockstate == SOCKET_TOO_LARGE_FOR_SELECT:
                raise ssl_error("Underlying socket too large for select().")
            elif sockstate != SOCKET_OPERATION_OK:
                # Retain the SSL error code
                break;

        if err < 0:
            raise pyssl_error(self, err)
        if sock:
            return sock
        else:
            return None

    def pending(self):
        count = lib.SSL_pending(self.ssl)
        if count < 0:
            raise pyssl_error(self, count)
        else:
            return count

    def tls_unique_cb(self):
        buf = ffi.new("char[]", SSL_CB_MAXLEN)

        if lib.SSL_session_reused(self.ssl) ^ (not self.socket_type):
            # if session is resumed XOR we are the client
            length = lib.SSL_get_finished(self.ssl, buf, SSL_CB_MAXLEN)
        else:
            # if a new session XOR we are the server
            length = lib.SSL_get_peer_finished(self.ssl, buf, SSL_CB_MAXLEN)

        # It cannot be negative in current OpenSSL version as of July 2011
        if length == 0:
            return None

        return _bytes_with_len(buf, length)

    if HAS_NPN:
        def selected_npn_protocol(self):
            out = ffi.new("unsigned char**")
            outlen = ffi.new("unsigned int*")
            lib.SSL_get0_next_proto_negotiated(self.ssl, out, outlen)
            if (out[0] == ffi.NULL):
                return None
            return _str_with_len(out[0], outlen[0])


def _fs_decode(name):
    return name.decode(sys.getfilesystemencoding())
def _fs_converter(name):
    """ name must not be None """
    if isinstance(name, str):
        return name.encode(sys.getfilesystemencoding())
    return bytes(name)


def cipher_to_tuple(cipher):
    ccipher_name = lib.SSL_CIPHER_get_name(cipher)
    if ccipher_name == ffi.NULL:
        cipher_name = None
    else:
        cipher_name = _str_from_buf(ccipher_name)

    ccipher_protocol = lib.SSL_CIPHER_get_version(cipher)
    if ccipher_protocol == ffi.NULL:
        cipher_protocol = None
    else:
        cipher_protocol = _str_from_buf(ccipher_protocol)

    bits = lib.SSL_CIPHER_get_bits(cipher, ffi.NULL)
    return (cipher_name, cipher_protocol, bits)



SSL_CTX_STATS_NAMES = """
    number connect connect_good connect_renegotiate accept accept_good
    accept_renegotiate hits misses timeouts cache_full""".split()
SSL_CTX_STATS = []
for name in SSL_CTX_STATS_NAMES:
    attr = 'SSL_CTX_sess_'+name
    assert hasattr(lib, attr)
    SSL_CTX_STATS.append((name, getattr(lib, attr)))

class _SSLContext(object):
    __slots__ = ('ctx', '_check_hostname', 'servername_callback',
                 'alpn_protocols', '_alpn_protocols_handle',
                 'npn_protocols', 'set_hostname',
                 '_set_hostname_handle', '_npn_protocols_handle')

    def __new__(cls, protocol):
        self = object.__new__(cls)
        self.ctx = ffi.NULL
        if protocol == PROTOCOL_TLSv1:
            method = lib.TLSv1_method()
        elif lib.Cryptography_HAS_TLSv1_2 and protocol == PROTOCOL_TLSv1_1:
            method = lib.TLSv1_1_method()
        elif lib.Cryptography_HAS_TLSv1_2 and protocol == PROTOCOL_TLSv1_2 :
            method = lib.TLSv1_2_method()
        elif protocol == PROTOCOL_SSLv3 and lib.Cryptography_HAS_SSL3_METHOD:
            method = lib.SSLv3_method()
        elif lib.Cryptography_HAS_SSL2 and protocol == PROTOCOL_SSLv2:
            method = lib.SSLv2_method()
        elif protocol == PROTOCOL_SSLv23:
            method = lib.SSLv23_method()
        else:
            raise ValueError("invalid protocol version")

        ctx = lib.SSL_CTX_new(method)
        if ctx == ffi.NULL:
            raise ssl_error("failed to allocate SSL context")
        self.ctx = ffi.gc(lib.SSL_CTX_new(method), lib.SSL_CTX_free)

        self._check_hostname = False

        # Defaults
        lib.SSL_CTX_set_verify(self.ctx, lib.SSL_VERIFY_NONE, ffi.NULL)
        options = lib.SSL_OP_ALL & ~lib.SSL_OP_DONT_INSERT_EMPTY_FRAGMENTS
        if not lib.Cryptography_HAS_SSL2 or protocol != PROTOCOL_SSLv2:
            options |= lib.SSL_OP_NO_SSLv2
        if protocol != PROTOCOL_SSLv3:
            options |= lib.SSL_OP_NO_SSLv3
        lib.SSL_CTX_set_options(self.ctx, options)
        lib.SSL_CTX_set_session_id_context(self.ctx, b"Python", len(b"Python"))

        if HAS_ECDH:
            # Allow automatic ECDH curve selection (on
            # OpenSSL 1.0.2+), or use prime256v1 by default.
            # This is Apache mod_ssl's initialization
            # policy, so we should be safe.
            if lib.Cryptography_HAS_SET_ECDH_AUTO:
                lib.SSL_CTX_set_ecdh_auto(self.ctx, 1)
            else:
                key = lib.EC_KEY_new_by_curve_name(lib.NID_X9_62_prime256v1)
                lib.SSL_CTX_set_tmp_ecdh(self.ctx, key)
                lib.EC_KEY_free(key)
        if lib.Cryptography_HAS_X509_V_FLAG_TRUSTED_FIRST:
            store = lib.SSL_CTX_get_cert_store(self.ctx)
            lib.X509_STORE_set_flags(store, lib.X509_V_FLAG_TRUSTED_FIRST)
        return self

    @property
    def options(self):
        return lib.SSL_CTX_get_options(self.ctx)

    @options.setter
    def options(self, value):
        new_opts = int(value)
        opts = lib.SSL_CTX_get_options(self.ctx)
        clear = opts & ~new_opts
        set = ~opts & new_opts
        if clear:
            if lib.Cryptography_HAS_SSL_CTX_CLEAR_OPTIONS:
                lib.SSL_CTX_clear_options(self.ctx, clear)
            else:
                raise ValueError("can't clear options before OpenSSL 0.9.8m")
        if set:
            lib.SSL_CTX_set_options(self.ctx, set)

    @property
    def verify_mode(self):
        mode = lib.SSL_CTX_get_verify_mode(self.ctx)
        if mode == lib.SSL_VERIFY_NONE:
            return CERT_NONE
        elif mode == lib.SSL_VERIFY_PEER:
            return CERT_OPTIONAL
        elif mode == lib.SSL_VERIFY_PEER | lib.SSL_VERIFY_FAIL_IF_NO_PEER_CERT:
            return CERT_REQUIRED
        raise ssl_error("invalid return value from SSL_CTX_get_verify_mode")

    @verify_mode.setter
    def verify_mode(self, value):
        n = int(value)
        if n == CERT_NONE:
            mode = lib.SSL_VERIFY_NONE
        elif n == CERT_OPTIONAL:
            mode = lib.SSL_VERIFY_PEER
        elif n == CERT_REQUIRED:
            mode = lib.SSL_VERIFY_PEER | lib.SSL_VERIFY_FAIL_IF_NO_PEER_CERT
        else:
            raise ValueError("invalid value for verify_mode")
        if mode == lib.SSL_VERIFY_NONE and self.check_hostname:
            raise ValueError("Cannot set verify_mode to CERT_NONE when " \
                             "check_hostname is enabled.")
        lib.SSL_CTX_set_verify(self.ctx, mode, ffi.NULL);

    @property
    def verify_flags(self):
        store = lib.SSL_CTX_get_cert_store(self.ctx)
        param = lib.X509_STORE_get0_param(store)
        flags = lib.X509_VERIFY_PARAM_get_flags(param)
        return int(flags)

    @verify_flags.setter
    def verify_flags(self, value):
        new_flags = int(value)
        store = lib.SSL_CTX_get_cert_store(self.ctx);
        param = lib.X509_STORE_get0_param(store)
        flags = lib.X509_VERIFY_PARAM_get_flags(param);
        clear = flags & ~new_flags;
        set = ~flags & new_flags;
        if clear:
            param = lib.X509_STORE_get0_param(store)
            if not lib.X509_VERIFY_PARAM_clear_flags(param, clear):
                raise ssl_error(None, 0)
        if set:
            param = lib.X509_STORE_get0_param(store)
            if not lib.X509_VERIFY_PARAM_set_flags(param, set):
                raise ssl_error(None, 0)

    @property
    def check_hostname(self):
        return self._check_hostname

    @check_hostname.setter
    def check_hostname(self, value):
        check_hostname = bool(value)
        if check_hostname and lib.SSL_CTX_get_verify_mode(self.ctx) == lib.SSL_VERIFY_NONE:
            raise ValueError("check_hostname needs a SSL context with either "
                             "CERT_OPTIONAL or CERT_REQUIRED")
        self._check_hostname = check_hostname

    def set_ciphers(self, cipherlist):
        cipherlistbuf = _str_to_ffi_buffer(cipherlist)
        ret = lib.SSL_CTX_set_cipher_list(self.ctx, cipherlistbuf)
        if ret == 0:
            # Clearing the error queue is necessary on some OpenSSL
            # versions, otherwise the error will be reported again
            # when another SSL call is done.
            lib.ERR_clear_error()
            raise ssl_error("No cipher can be selected.")


    def load_cert_chain(self, certfile, keyfile=None, password=None):
        if keyfile is None:
            keyfile = certfile
        pw_info = PasswordInfo()
        index = -1
        if password is not None:

            if callable(password):
                pw_info.callable = password
            else:
                if isinstance(password, (str, bytes, bytearray)):
                    pw_info.password = password
                else:
                    raise TypeError("password should be a string or callable")

            pw_info.handle = ffi.new_handle(pw_info)
            index = _thread.get_ident()
            PWINFO_STORAGE[index] = pw_info
            lib.SSL_CTX_set_default_passwd_cb(self.ctx, Cryptography_pem_password_cb)
            lib.SSL_CTX_set_default_passwd_cb_userdata(self.ctx, pw_info.handle)

        try:
            ffi.errno = 0
            certfilebuf = _str_to_ffi_buffer(certfile)
            ret = lib.SSL_CTX_use_certificate_chain_file(self.ctx, certfilebuf)
            if ret != 1:
                if pw_info.operationerror:
                    lib.ERR_clear_error()
                    raise pw_info.operationerror
                _errno = ffi.errno
                if _errno:
                    lib.ERR_clear_error()
                    raise OSError(_errno, "Error")
                else:
                    raise ssl_error(None)

            ffi.errno = 0
            buf = _str_to_ffi_buffer(keyfile)
            ret = lib.SSL_CTX_use_PrivateKey_file(self.ctx, buf,
                                                  lib.SSL_FILETYPE_PEM)
            if ret != 1:
                if pw_info.operationerror:
                    lib.ERR_clear_error()
                    raise pw_info.operationerror
                _errno = ffi.errno
                if _errno:
                    lib.ERR_clear_error()
                    raise OSError(_errno, None)
                else:
                    raise ssl_error(None)

            ret = lib.SSL_CTX_check_private_key(self.ctx)
            if ret != 1:
                raise ssl_error(None)
        finally:
            if index >= 0:
                del PWINFO_STORAGE[index]
            lib.SSL_CTX_set_default_passwd_cb(self.ctx, ffi.NULL)
            lib.SSL_CTX_set_default_passwd_cb_userdata(self.ctx, ffi.NULL)


    def _wrap_socket(self, sock, server_side, server_hostname=None):
        if server_hostname:
            server_hostname = server_hostname.encode('idna')
        return _SSLSocket._new__ssl_socket(self, sock, server_side,
                server_hostname, None, None)

    def load_verify_locations(self, cafile=None, capath=None, cadata=None):
        ffi.errno = 0
        if cadata is None:
            ca_file_type = -1
        else:
            if not isinstance(cadata, str):
                ca_file_type = lib.SSL_FILETYPE_ASN1
            else:
                ca_file_type = lib.SSL_FILETYPE_PEM
                try:
                    cadata = cadata.encode('ascii')
                except UnicodeEncodeError:
                    raise TypeError("cadata should be a ASCII string or a bytes-like object")
        if cafile is None and capath is None and cadata is None:
            raise TypeError("cafile and capath cannot be both omitted")
        # load from cadata
        if cadata is not None:
            buf = _str_to_ffi_buffer(cadata)
            self._add_ca_certs(buf, len(buf), ca_file_type)

        # load cafile or capath
        if cafile or capath:
            if cafile is None:
                cafilebuf = ffi.NULL
            else:
                cafilebuf = _str_to_ffi_buffer(cafile)
            if capath is None:
                capathbuf = ffi.NULL
            else:
                capathbuf = _str_to_ffi_buffer(capath)
            ret = lib.SSL_CTX_load_verify_locations(self.ctx, cafilebuf, capathbuf)
            if ret != 1:
                _errno = ffi.errno
                if _errno:
                    lib.ERR_clear_error()
                    raise OSError(_errno, '')
                else:
                    raise ssl_error(None)

    def _add_ca_certs(self, data, size, ca_file_type):
        biobuf = lib.BIO_new_mem_buf(data, size)
        if biobuf == ffi.NULL:
            raise ssl_error("Can't allocate buffer")
        try:
            store = lib.SSL_CTX_get_cert_store(self.ctx)
            loaded = 0
            while True:
                if ca_file_type == lib.SSL_FILETYPE_ASN1:
                    cert = lib.d2i_X509_bio(biobuf, ffi.NULL)
                else:
                    cert = lib.PEM_read_bio_X509(biobuf, ffi.NULL, ffi.NULL, ffi.NULL)
                if not cert:
                    break
                try:
                    r = lib.X509_STORE_add_cert(store, cert)
                finally:
                    lib.X509_free(cert)
                if not r:
                    err = lib.ERR_peek_last_error()
                    if (lib.ERR_GET_LIB(err) == lib.ERR_LIB_X509 and
                        lib.ERR_GET_REASON(err) ==
                        lib.X509_R_CERT_ALREADY_IN_HASH_TABLE):
                        # cert already in hash table, not an error
                        lib.ERR_clear_error()
                    else:
                        break
                loaded += 1

            err = lib.ERR_peek_last_error()
            if (ca_file_type == lib.SSL_FILETYPE_ASN1 and
                loaded > 0 and
                lib.ERR_GET_LIB(err) == lib.ERR_LIB_ASN1 and
                lib.ERR_GET_REASON(err) == lib.ASN1_R_HEADER_TOO_LONG):
                # EOF ASN1 file, not an error
                lib.ERR_clear_error()
            elif (ca_file_type == lib.SSL_FILETYPE_PEM and
                  loaded > 0 and
                  lib.ERR_GET_LIB(err) == lib.ERR_LIB_PEM and
                  lib.ERR_GET_REASON(err) == lib.PEM_R_NO_START_LINE):
                # EOF PEM file, not an error
                lib.ERR_clear_error()
            else:
                raise ssl_error(None)
        finally:
            lib.BIO_free(biobuf)

    def cert_store_stats(self):
        store = lib.SSL_CTX_get_cert_store(self.ctx)
        x509 = 0
        x509_ca = 0
        crl = 0
        objs = lib.X509_STORE_get0_objects(store)
        count = lib.sk_X509_OBJECT_num(objs)
        for i in range(count):
            obj = lib.sk_X509_OBJECT_value(objs, i)
            _type = lib.X509_OBJECT_get_type(obj)
            if _type == lib.X509_LU_X509:
                x509 += 1
                cert = lib.X509_OBJECT_get0_X509(obj)
                if lib.X509_check_ca(cert):
                    x509_ca += 1
            elif _type == lib.X509_LU_CRL:
                crl += 1
            else:
                # Ignore X509_LU_FAIL, X509_LU_RETRY, X509_LU_PKEY.
                # As far as I can tell they are internal states and never
                # stored in a cert store
                pass
        return {'x509': x509, 'x509_ca': x509_ca, 'crl': crl}


    def session_stats(self):
        stats = {}
        for name, ssl_func in SSL_CTX_STATS:
            stats[name] = ssl_func(self.ctx)
        return stats

    def set_default_verify_paths(self):
        if not lib.SSL_CTX_set_default_verify_paths(self.ctx):
            raise ssl_error("")

    def load_dh_params(self, filepath):
        ffi.errno = 0
        if filepath is None:
            raise TypeError("filepath must not be None")
        buf = _fs_converter(filepath)
        mode = ffi.new("char[]",b"r")
        ffi.errno = 0
        bio = lib.BIO_new_file(buf, mode)
        if bio == ffi.NULL:
            _errno = ffi.errno
            lib.ERR_clear_error()
            raise OSError(_errno, '')
        try:
            dh = lib.PEM_read_bio_DHparams(bio, ffi.NULL, ffi.NULL, ffi.NULL)
        finally:
            lib.BIO_free(bio)
        if dh == ffi.NULL:
            _errno = ffi.errno
            if _errno != 0:
                lib.ERR_clear_error()
                raise OSError(_errno, '')
            else:
                raise ssl_error(None)
        try:
            if lib.SSL_CTX_set_tmp_dh(self.ctx, dh) == 0:
                raise ssl_error(None)
        finally:
            lib.DH_free(dh)

    def get_ca_certs(self, binary_form=None):
        binary_mode = bool(binary_form)
        _list = []
        store = lib.SSL_CTX_get_cert_store(self.ctx)
        objs = lib.X509_STORE_get0_objects(store)
        count = lib.sk_X509_OBJECT_num(objs)
        for i in range(count):
            obj = lib.sk_X509_OBJECT_value(objs, i)
            _type = lib.X509_OBJECT_get_type(obj)
            if _type != lib.X509_LU_X509:
                # not a x509 cert
                continue
            # CA for any purpose
            cert = lib.X509_OBJECT_get0_X509(obj)
            if not lib.X509_check_ca(cert):
                continue
            if binary_mode:
                _list.append(_certificate_to_der(cert))
            else:
                _list.append(_decode_certificate(cert))
        return _list

    def set_ecdh_curve(self, name):
        # needs to be zero terminated
        if name is None:
            raise TypeError()
        buf = _fs_converter(name)
        nid = lib.OBJ_sn2nid(buf)
        if nid == 0:
            raise ValueError("unknown elliptic curve name '%s'" % name)
        key = lib.EC_KEY_new_by_curve_name(nid)
        if not key:
            raise ssl_error(None)
        try:
            lib.SSL_CTX_set_tmp_ecdh(self.ctx, key)
        finally:
            lib.EC_KEY_free(key)

    def set_servername_callback(self, callback):
        # cryptography constraint: OPENSSL_NO_TLSEXT will never be set!
        if not HAS_SNI:
            raise NotImplementedError("The TLS extension servername callback, "
                    "SSL_CTX_set_tlsext_servername_callback, "
                    "is not in the current OpenSSL library.")
        if callback is None:
            lib.SSL_CTX_set_tlsext_servername_callback(self.ctx, ffi.NULL)
            self._set_hostname_handle = None
            return
        if not callable(callback):
            raise TypeError("not a callable object")
        scb = ServernameCallback(callback, self)
        self._set_hostname_handle = ffi.new_handle(scb)
        lib.SSL_CTX_set_tlsext_servername_callback(self.ctx, _servername_callback)
        lib.SSL_CTX_set_tlsext_servername_arg(self.ctx, self._set_hostname_handle)

    def _set_alpn_protocols(self, protos):
        if HAS_ALPN:
            self.alpn_protocols = protocols = ffi.from_buffer(protos)
            length = len(protocols)

            if lib.SSL_CTX_set_alpn_protos(self.ctx,ffi.cast("unsigned char*", protocols), length):
                return MemoryError()
            self._alpn_protocols_handle = handle = ffi.new_handle(self)
            lib.SSL_CTX_set_alpn_select_cb(self.ctx, select_alpn_callback, handle)
        else:
            raise NotImplementedError("The ALPN extension requires OpenSSL 1.0.2 or later.")

    def _set_npn_protocols(self, protos):
        if HAS_NPN:
            self.npn_protocols = ffi.from_buffer(protos)
            handle = ffi.new_handle(self)
            self._npn_protocols_handle = handle # track a reference to the handle
            lib.SSL_CTX_set_next_protos_advertised_cb(self.ctx, advertise_npn_callback, handle)
            lib.SSL_CTX_set_next_proto_select_cb(self.ctx, select_npn_callback, handle)
        else:
            raise NotImplementedError("The NPN extension requires OpenSSL 1.0.1 or later.")

    def _wrap_bio(self, incoming, outgoing, server_side, server_hostname):
        # server_hostname is either None (or absent), or to be encoded
        # using the idna encoding.
        hostname = None
        if server_hostname is not None:
            hostname = server_hostname.encode("idna")

        sock = _SSLSocket._new__ssl_socket(self, None, server_side, hostname, incoming, outgoing)
        return sock



# cryptography constraint: OPENSSL_NO_TLSEXT will never be set!
if HAS_SNI:
    @ffi.callback("int(SSL*,int*,void*)")
    def _servername_callback(s, al, arg):
        scb = ffi.from_handle(arg)
        ssl_ctx = scb.ctx
        servername = lib.SSL_get_servername(s, lib.TLSEXT_NAMETYPE_host_name)
        set_hostname = scb.callback
        #ifdef WITH_THREAD
            # TODO PyGILState_STATE gstate = PyGILState_Ensure();
        #endif

        if set_hostname is None:
            #/* remove race condition in this the call back while if removing the
            # * callback is in progress */
            #ifdef WITH_THREAD
                    # TODO PyGILState_Release(gstate);
            #endif
            return lib.SSL_TLSEXT_ERR_OK

        ssl = ffi.from_handle(lib.SSL_get_app_data(s))
        assert isinstance(ssl, _SSLSocket)

        # The servername callback expects an argument that represents the current
        # SSL connection and that has a .context attribute that can be changed to
        # identify the requested hostname. Since the official API is the Python
        # level API we want to pass the callback a Python level object rather than
        # a _ssl.SSLSocket instance. If there's an "owner" (typically an
        # SSLObject) that will be passed. Otherwise if there's a socket then that
        # will be passed. If both do not exist only then the C-level object is
        # passed.
        ssl_socket = ssl.owner
        if not ssl_socket:
            ssl_socket = ssl.get_socket_or_None()

        if ssl_socket is None:
            al[0] = lib.SSL_AD_INTERNAL_ERROR
            return lib.SSL_TLSEXT_ERR_ALERT_FATAL

        if servername == ffi.NULL:
            try:
                result = set_hostname(ssl_socket, None, ssl_ctx)
            except Exception as e:
                pyerr_write_unraisable(e, set_hostname)
                al[0] = lib.SSL_AD_HANDSHAKE_FAILURE
                return lib.SSL_TLSEXT_ERR_ALERT_FATAL
        else:
            servername = ffi.string(servername)

            try:
                servername_idna = servername.decode("idna")
            except UnicodeDecodeError as e:
                pyerr_write_unraisable(e, servername)

            try:
                result = set_hostname(ssl_socket, servername_idna, ssl_ctx)
            except Exception as e:
                pyerr_write_unraisable(e, set_hostname)
                al[0] = lib.SSL_AD_HANDSHAKE_FAILURE
                return lib.SSL_TLSEXT_ERR_ALERT_FATAL

        if result is not None:
            # this is just a poor man's emulation:
            # in CPython this works a bit different, it calls all the way
            # down from PyLong_AsLong to _PyLong_FromNbInt which raises
            # a TypeError if there is no nb_int slot filled.
            try:
                if isinstance(result, int):
                    al[0] = result
                else:
                    if result is not None:
                        if hasattr(result,'__int__'):
                            al[0] = result.__int__()
                            return lib.SSL_TLSEXT_ERR_ALERT_FATAL
                    # needed because sys.exec_info is used in pyerr_write_unraisable
                    raise TypeError("an integer is required (got type %s)" % result)
            except TypeError as e:
                pyerr_write_unraisable(e, result)
                al[0] = lib.SSL_AD_INTERNAL_ERROR
            return lib.SSL_TLSEXT_ERR_ALERT_FATAL
        else:
            # TODO gil state release?
            return lib.SSL_TLSEXT_ERR_OK

class ServernameCallback(object):
    def __init__(self, callback, ctx):
        self.callback = callback
        self.ctx = ctx

SERVERNAME_CALLBACKS = weakref.WeakValueDictionary()

def _asn1obj2py(obj):
    nid = lib.OBJ_obj2nid(obj)
    if nid == lib.NID_undef:
        raise ValueError("Unknown object")
    sn = _str_from_buf(lib.OBJ_nid2sn(nid))
    ln = _str_from_buf(lib.OBJ_nid2ln(nid))
    buf = ffi.new("char[]", 255)
    length = lib.OBJ_obj2txt(buf, len(buf), obj, 1)
    if length < 0:
        ssl_error(None)
    if length > 0:
        return (nid, sn, ln, _str_with_len(buf, length))
    else:
        return (nid, sn, ln, None)

def txt2obj(txt, name):
    _bytes = _str_to_ffi_buffer(txt)
    is_name = 0 if name else 1
    obj = lib.OBJ_txt2obj(_bytes, is_name)
    if obj == ffi.NULL:
        raise ValueError("unknown object '%s'" % txt)
    result = _asn1obj2py(obj)
    lib.ASN1_OBJECT_free(obj)
    return result

def nid2obj(nid):
    if nid < lib.NID_undef:
        raise ValueError("NID must be positive.")
    obj = lib.OBJ_nid2obj(nid);
    if obj == ffi.NULL:
        raise ValueError("unknown NID %i" % nid)
    result = _asn1obj2py(obj);
    lib.ASN1_OBJECT_free(obj);
    return result;
                                                               

class MemoryBIO(object):
    def __init__(self):
        bio = lib.BIO_new(lib.BIO_s_mem());
        if bio == ffi.NULL:
            raise ssl_error("failed to allocate BIO")

        # Since our BIO is non-blocking an empty read() does not indicate EOF,
        # just that no data is currently available. The SSL routines should retry
        # the read, which we can achieve by calling BIO_set_retry_read().
        lib.BIO_set_retry_read(bio);
        lib.BIO_set_mem_eof_return(bio, -1);

        self.bio = ffi.gc(bio, lib.BIO_free)
        self.eof_written = False

    @property
    def eof(self):
        """Whether the memory BIO is at EOF."""
        return lib.BIO_ctrl_pending(self.bio) == 0 and self.eof_written

    def write(self, strlike):
        INT_MAX = 2**31-1
        if isinstance(strlike, memoryview):
            # FIXME pypy must support get_raw_address for
            # StringBuffer to remove this case!
            strlike = strlike.tobytes()
        buf = ffi.from_buffer(strlike)
        if len(buf) > INT_MAX:
            raise OverflowError("string longer than %d bytes", INT_MAX)

        if self.eof_written:
            raise ssl_error("cannot write() after write_eof()")
        nbytes = lib.BIO_write(self.bio, buf, len(buf));
        if nbytes < 0:
            raise ssl_error(None)
        return nbytes

    def write_eof(self):
        self.eof_written = True
        # After an EOF is written, a zero return from read() should be a real EOF
        # i.e. it should not be retried. Clear the SHOULD_RETRY flag.
        lib.BIO_clear_retry_flags(self.bio)
        lib.BIO_set_mem_eof_return(self.bio, 0)

    def read(self, len=-1):
        count = len
        avail = lib.BIO_ctrl_pending(self.bio);
        if count < 0 or count > avail:
            count = avail;

        buf = ffi.new("char[]", count)

        nbytes = lib.BIO_read(self.bio, buf, count);
        #  There should never be any short reads but check anyway.
        if nbytes < count:
            return b""

        return _bytes_with_len(buf, nbytes)

    @property
    def pending(self):
        return lib.BIO_ctrl_pending(self.bio)


def RAND_status():
    return lib.RAND_status()

def _RAND_bytes(count, pseudo):
    if count < 0:
        raise ValueError("num must be positive")
    buf = ffi.new("unsigned char[]", count)
    if pseudo:
        # note by reaperhulk, RAND_pseudo_bytes is deprecated in 3.6 already,
        # it is totally fine to just call RAND_bytes instead
        ok = lib.RAND_bytes(buf, count)
        if ok == 1 or ok == 0:
            _bytes = _bytes_with_len(buf, count)
            return (_bytes, ok == 1)
    else:
        ok = lib.RAND_bytes(buf, count)
        if ok == 1 or (pseudo and ok == 0):
            return _bytes_with_len(buf, count)
    raise ssl_error(None, errcode=lib.ERR_get_error())

def RAND_pseudo_bytes(count):
    return _RAND_bytes(count, True)

def RAND_bytes(count):
    return _RAND_bytes(count, False)

def RAND_add(view, entropy):
    buf = _str_to_ffi_buffer(view)
    lib.RAND_add(buf, len(buf), entropy)

def get_default_verify_paths():

    ofile_env = _cstr_decode_fs(lib.X509_get_default_cert_file_env())
    if ofile_env is None:
        return None
    ofile = _cstr_decode_fs(lib.X509_get_default_cert_file())
    if ofile is None:
        return None
    odir_env = _cstr_decode_fs(lib.X509_get_default_cert_dir_env())
    if odir_env is None:
        return None
    odir = _cstr_decode_fs(lib.X509_get_default_cert_dir())
    if odir is None:
        return odir
    return (ofile_env, ofile, odir_env, odir);

@ffi.callback("int(SSL*,unsigned char **,unsigned char *,const unsigned char *,unsigned int,void *)")
def select_alpn_callback(ssl, out, outlen, client_protocols, client_protocols_len, args):
    ctx = ffi.from_handle(args)
    return do_protocol_selection(1, out, outlen,
                                 ffi.cast("unsigned char*",ctx.alpn_protocols), len(ctx.alpn_protocols),
                                 client_protocols, client_protocols_len)

if lib.OPENSSL_NPN_NEGOTIATED:
    @ffi.callback("int(SSL*,unsigned char **,unsigned char *,const unsigned char *,unsigned int,void *)")
    def select_npn_callback(ssl, out, outlen, server_protocols, server_protocols_len, args):
        ctx = ffi.from_handle(args)
        return do_protocol_selection(0, out, outlen, server_protocols, server_protocols_len,
                                     ffi.cast("unsigned char*",ctx.npn_protocols), len(ctx.npn_protocols))


    @ffi.callback("int(SSL*,const unsigned char**, unsigned int*, void*)")
    def advertise_npn_callback(ssl, data, length, args):
        ctx = ffi.from_handle(args)

        if not ctx.npn_protocols:
            data[0] = ffi.new("unsigned char*", b"")
            length[0] = 0
        else:
            data[0] = ffi.cast("unsigned char*",ctx.npn_protocols)
            length[0] = len(ctx.npn_protocols)

        return lib.SSL_TLSEXT_ERR_OK


    def do_protocol_selection(alpn, out, outlen, server_protocols, server_protocols_len,
                                                 client_protocols, client_protocols_len):
        if client_protocols == ffi.NULL:
            client_protocols = b""
            client_protocols_len = 0
        if server_protocols == ffi.NULL:
            server_protocols = ""
            server_protocols_len = 0

        ret = lib.SSL_select_next_proto(out, outlen,
                                        server_protocols, server_protocols_len,
                                        client_protocols, client_protocols_len);
        if alpn and ret != lib.OPENSSL_NPN_NEGOTIATED:
            return lib.SSL_TLSEXT_ERR_NOACK

        return lib.SSL_TLSEXT_ERR_OK

if lib.Cryptography_HAS_EGD:
    def RAND_egd(path):
        bytecount = lib.RAND_egd_bytes(ffi.from_buffer(path), len(path))
        if bytecount == -1:
            raise SSLError("EGD connection failed or EGD did not return "
                           "enough data to seed the PRNG");
        return bytecount


import sys
import time
import _thread
import socket
import weakref
from _openssl import ffi
from _openssl import lib
from openssl._stdssl.certificate import (_test_decode_cert,
    _decode_certificate, _certificate_to_der)
from openssl._stdssl.utility import _str_with_len, _bytes_with_len, _str_to_ffi_buffer
from openssl._stdssl.error import (ssl_error, ssl_lib_error, ssl_socket_error,
        SSLError, SSLZeroReturnError, SSLWantReadError,
        SSLWantWriteError, SSLSyscallError,
        SSLEOFError)
from openssl._stdssl.error import (SSL_ERROR_NONE,
        SSL_ERROR_SSL, SSL_ERROR_WANT_READ, SSL_ERROR_WANT_WRITE,
        SSL_ERROR_WANT_X509_LOOKUP, SSL_ERROR_SYSCALL,
        SSL_ERROR_ZERO_RETURN, SSL_ERROR_WANT_CONNECT,
        SSL_ERROR_EOF, SSL_ERROR_NO_SOCKET, SSL_ERROR_INVALID_ERROR_CODE)


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
HAS_NPN = False
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

if lib.Cryptography_HAS_SSL2:
    PROTOCOL_SSLv2  = 0
PROTOCOL_SSLv3  = 1
PROTOCOL_SSLv23 = 2
PROTOCOL_TLSv1    = 3
if lib.Cryptography_HAS_TLSv1_2:
    PROTOCOL_TLSv1 = 3
    PROTOCOL_TLSv1_1 = 4
    PROTOCOL_TLSv1_2 = 5

_PROTOCOL_NAMES = (name for name in dir(lib) if name.startswith('PROTOCOL_'))

from enum import Enum as _Enum, IntEnum as _IntEnum
_IntEnum._convert('_SSLMethod', __name__,
        lambda name: name.startswith('PROTOCOL_'))

if HAS_TLS_UNIQUE:
    CHANNEL_BINDING_TYPES = ['tls-unique']
else:
    CHANNEL_BINDING_TYPES = []

# init open ssl
lib.SSL_load_error_strings()
lib.SSL_library_init()
# TODO threads?
lib.OpenSSL_add_all_algorithms()

class PasswordInfo(object):
    callable = None
    password = None
    operationerror = None
PWINFO_STORAGE = {}

def _Cryptography_pem_password_cb(buf, size, rwflag, userdata):
    pw_info = ffi.from_handle(userdata)

    # TODO PySSL_END_ALLOW_THREADS_S(pw_info->thread_state);
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

    #PySSL_BEGIN_ALLOW_THREADS_S(pw_info->thread_state);
    ffi.memmove(buf, password, len(password))
    return len(password)

if lib.Cryptography_STATIC_CALLBACKS:
    ffi.def_extern(_Cryptography_pem_password_cb)
    Cryptography_pem_password_cb = lib.Cryptography_pem_password_cb
else:
    Cryptography_pem_password_cb = ffi.callback("int(char*,int,int,void*)")(_Cryptography_pem_password_cb)

from select import poll, POLLIN, POLLOUT, select

HAVE_POLL = True

def _ssl_select(sock, writing, timeout):
    if HAVE_POLL:
        p = poll()

    # Nothing to do unless we're in timeout mode (not non-blocking)
    if sock is None or timeout == 0:
        return SOCKET_IS_NONBLOCKING
    elif timeout < 0:
        t = sock.gettimeout() or 0
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

        #PySSL_BEGIN_ALLOW_THREADS
        rc = len(p.poll(timeout * 1000.0))
        #PySSL_END_ALLOW_THREADS
    else:
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

def _buffer_new(length):
    return ffi.new("char[%d]"%length)

class _SSLSocket(object):

    @staticmethod
    def _new__ssl_socket(sslctx, sock, socket_type, server_hostname, inbio, outbio):
        self = _SSLSocket(sslctx)
        ctx = sslctx.ctx

        if server_hostname:
            self.server_hostname = server_hostname.decode('idna', 'strict')

        lib.ERR_get_state()
        lib.ERR_clear_error()
        self.ssl = ssl = lib.SSL_new(ctx)

        lib.SSL_set_app_data(ssl, b"")
        if sock:
            lib.SSL_set_fd(ssl, sock.fileno())
        else:
            raise NotImplementedError("implement _SSLSocket inbio, outbio params")
            # /* BIOs are reference counted and SSL_set_bio borrows our reference.
            #  * To prevent a double free in memory_bio_dealloc() we need to take an
            #  * extra reference here. */
            # CRYPTO_add(&inbio->bio->references, 1, CRYPTO_LOCK_BIO);
            # CRYPTO_add(&outbio->bio->references, 1, CRYPTO_LOCK_BIO);
            # SSL_set_bio(self->ssl, inbio->bio, outbio->bio);

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
        timeout = sock.gettimeout() or 0
        if sock and timeout >= 0:
            lib.BIO_set_nbio(lib.SSL_get_rbio(ssl), 1)
            lib.BIO_set_nbio(lib.SSL_get_wbio(ssl), 1)

        #PySSL_BEGIN_ALLOW_THREADS
        if socket_type == SSL_CLIENT:
            lib.SSL_set_connect_state(ssl)
        else:
            lib.SSL_set_accept_state(ssl)
        self.socket_type = socket_type
        #PySSL_END_ALLOW_THREADS

        if sock:
            self.socket = weakref.ref(sock)

        return self

    def __init__(self, sslctx):
        self.ctx = sslctx
        self.peer_cert = ffi.NULL
        self.ssl = ffi.NULL
        self.shutdown_seen_zero = 0
        self.handshake_done = 0
        self.owner = None
        self.server_hostname = None
        self.socket = None

    @property
    def context(self):
        return self.ctx

    @context.setter
    def context(self, value):
        self.ctx = value

    def do_handshake(self):
        sock = self.get_socket_or_None()
        if sock is None:
            raise ssl_error("Underlying socket connection gone", SSL_ERROR_NO_SOCKET)
        ssl = self.ssl
        timeout = 0
        if sock:
            timeout = sock.gettimeout() or 0
            nonblocking = timeout >= 0
            lib.BIO_set_nbio(lib.SSL_get_rbio(ssl), nonblocking)
            lib.BIO_set_nbio(lib.SSL_get_wbio(ssl), nonblocking)

        has_timeout = timeout > 0
        has_timeout = (timeout > 0);
        deadline = -1
        if has_timeout:
            # REVIEW, cpython uses a monotonic clock here
            deadline = time.time() + timeout;
        # Actually negotiate SSL connection
        # XXX If SSL_do_handshake() returns 0, it's also a failure.
        while True:
            # allow threads
            ret = lib.SSL_do_handshake(ssl)
            err = lib.SSL_get_error(ssl, ret)
            # end allow threads

            #if (PyErr_CheckSignals())
            #    goto error;

            if has_timeout:
                # REIVIEW monotonic clock?
                timeout = deadline - time.time()

            if err == SSL_ERROR_WANT_READ:
                sockstate = _ssl_select(sock, 0, timeout)
            elif err == SSL_ERROR_WANT_WRITE:
                sockstate = _ssl_select(sock, 1, timeout)
            else:
                sockstate = SOCKET_OPERATION_OK

            if sockstate == SOCKET_HAS_TIMED_OUT:
                raise SSLError("The handshake operation timed out")
            elif sockstate == SOCKET_HAS_BEEN_CLOSED:
                raise SSLError("Underlying socket has been closed.")
            elif sockstate == SOCKET_TOO_LARGE_FOR_SELECT:
                raise SSLError("Underlying socket too large for select().")
            elif sockstate == SOCKET_IS_NONBLOCKING:
                break
            if not (err == SSL_ERROR_WANT_READ or err == SSL_ERROR_WANT_WRITE):
                break
        if ret < 1:
            raise ssl_lib_error()

        if self.peer_cert != ffi.NULL:
            lib.X509_free(self.peer_cert)
        #PySSL_BEGIN_ALLOW_THREADS
        self.peer_cert = lib.SSL_get_peer_certificate(ssl)
        #PySSL_END_ALLOW_THREADS
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
        sock = self.get_socket_or_None()
        ssl = self.ssl
        if sock:
            timeout = sock.gettimeout() or 0
            nonblocking = timeout >= 0
            lib.BIO_set_nbio(lib.SSL_get_rbio(ssl), nonblocking)
            lib.BIO_set_nbio(lib.SSL_get_wbio(ssl), nonblocking)

        timeout = sock.gettimeout() or 0
        has_timeout = timeout > 0
        if has_timeout:
            # TODO monotonic clock?
            deadline = time.time() + timeout

        sockstate = _ssl_select(sock, 1, timeout)
        if sockstate == SOCKET_HAS_TIMED_OUT:
            raise socket.TimeoutError("The write operation timed out")
        elif sockstate == SOCKET_HAS_BEEN_CLOSED:
            raise ssl_error("Underlying socket has been closed.")
        elif sockstate == SOCKET_TOO_LARGE_FOR_SELECT:
            raise ssl_error("Underlying socket too large for select().")

        while True:
            #PySSL_START_ALLOW_THREADS
            length = lib.SSL_write(self.ssl, b, len(b))
            err = lib.SSL_get_error(self.ssl, length)
            #PySSL_END_ALLOW_THREADS

            # TODO if (PyErr_CheckSignals())
            # TODO     goto error;

            if has_timeout:
                # TODO monotonic clock
                timeout = deadline - time.time()

            if err == SSL_ERROR_WANT_READ:
                sockstate = _ssl_select(sock, 0, timeout)
            elif err == SSL_ERROR_WANT_WRITE:
                sockstate = _ssl_select(sock, 1, timeout)
            else:
                sockstate = SOCKET_OPERATION_OK

            if sockstate == SOCKET_HAS_TIMED_OUT:
                raise socket.TimeoutError("The write operation timed out")
            elif sockstate == SOCKET_HAS_BEEN_CLOSED:
                raise ssl_error("Underlying socket has been closed.")
            elif sockstate == SOCKET_IS_NONBLOCKING:
                break
            if not (err == SSL_ERROR_WANT_READ or err == SSL_ERROR_WANT_WRITE):
                break

        if length > 0:
            return length
        else:
            raise ssl_lib_error()
            # return PySSL_SetError(self, len, __FILE__, __LINE__);

    def read(self, length, buffer_into=None):
        sock = self.get_socket_or_None()
        ssl = self.ssl

        if sock is None:
            raise ssl_error("Underlying socket connection gone", SSL_ERROR_NO_SOCKET)

        if not buffer_into:
            dest = _buffer_new(length)
            mem = dest
        else:
            import pdb; pdb.set_trace()
            mem = ffi.from_buffer(buffer_into)
            if length <= 0 or length > len(buffer_into):
                if len(buffer_into) != length:
                    raise OverflowError("maximum length can't fit in a C 'int'")

        if sock:
            timeout = sock.gettimeout() or 0
            nonblocking = timeout >= 0
            lib.BIO_set_nbio(lib.SSL_get_rbio(ssl), nonblocking)
            lib.BIO_set_nbio(lib.SSL_get_wbio(ssl), nonblocking)

        deadline = 0
        timeout = sock.gettimeout() or 0
        has_timeout = timeout > 0
        if has_timeout:
            # TODO monotonic clock?
            deadline = time.time() + timeout

        shutdown = False
        while True:
            #PySSL_BEGIN_ALLOW_THREADS
            count = lib.SSL_read(self.ssl, mem, length);
            err = lib.SSL_get_error(self.ssl, count);
            #PySSL_END_ALLOW_THREADS

            # TODO
            #if (PyErr_CheckSignals())
            #    goto error;

            if has_timeout:
                timeout = deadline - time.time() # TODO ? _PyTime_GetMonotonicClock();

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
                raise socket.TimeoutError("The read operation timed out")
            elif sockstate == SOCKET_IS_NONBLOCKING:
                break
            if not (err == SSL_ERROR_WANT_READ or err == SSL_ERROR_WANT_WRITE):
                break

        if count <= 0:
            raise ssl_socket_error(self, err)

        if not buffer_into:
            return _bytes_with_len(dest, count)

        return count

    def selected_alpn_protocol(self):
        out = ffi.new("const unsigned char **")
        outlen = ffi.new("unsigned int*")

        lib.SSL_get0_alpn_selected(self.ssl, out, outlen);
        if out == ffi.NULL:
            return None
        return _str_with_len(ffi.cast("char*",out[0]), outlen[0]);

    def shared_ciphers(self):
        sess = lib.SSL_get_session(self.ssl)

        ciphers = lib.Cryptography_get_ssl_session_ciphers(sess)
        if sess is None or ciphers == ffi.NULL:
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
        if comp_method == ffi.NULL: # or comp_method.type == lib.NID_undef:
            return None
        short_name = lib.SSL_COMP_get_name(comp_method)
        if short_name == ffi.NULL:
            return None
        return _fs_decode(_str_from_buf(short_name))

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

    def shutdown(self):
        sock = self.get_socket_or_None()
        nonblocking = False
        ssl = self.ssl

        if sock is not None:
            # Guard against closed socket
            if sock.fileno() < 0:
                raise ssl_error("Underlying socket connection gone", SSL_ERROR_NO_SOCKET)

            timeout = sock.gettimeout() or 0
            nonblocking = timeout >= 0
            if sock and timeout >= 0:
                lib.BIO_set_nbio(lib.SSL_get_rbio(ssl), nonblocking)
                lib.BIO_set_nbio(lib.SSL_get_wbio(ssl), nonblocking)
        else:
            timeout = 0

        has_timeout = (timeout > 0);
        if has_timeout:
            # TODO monotonic clock
            deadline = time.time() + timeout;

        zeros = 0

        while True:
            # TODO PySSL_BEGIN_ALLOW_THREADS
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
            # TODO PySSL_END_ALLOW_THREADS

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
                # TODO monotonic clock
                timeout = deadline - time.time() #_PyTime_GetMonotonicClock();

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
                    raise socket.TimeoutError("The read operation timed out")
                else:
                    raise socket.TimeoutError("The write operation timed out")
            elif sockstate == SOCKET_TOO_LARGE_FOR_SELECT:
                raise ssl_error("Underlying socket too large for select().")
            elif sockstate != SOCKET_OPERATION_OK:
                # Retain the SSL error code
                break;

        if err < 0:
            raise ssl_socket_error(self, err)
        if sock:
            return sock
        else:
            return None


def _fs_decode(name):
    # TODO return PyUnicode_DecodeFSDefault(short_name);
    return name.decode('utf-8')


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
    __slots__ = ('ctx', '_check_hostname', 'servername_callback')

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

        self.ctx = lib.SSL_CTX_new(method)
        if self.ctx == ffi.NULL: 
            raise ssl_error("failed to allocate SSL context")

        self._check_hostname = False
        # TODO self.register_finalizer(space)

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
            if lib.Cryptography_HAS_ECDH_SET_CURVE:
                lib.SSL_CTX_set_ecdh_auto(self.ctx, 1)
            else:
                key = lib.EC_KEY_new_by_curve_name(lib.NID_X9_62_prime256v1)
                if not key:
                    raise ssl_lib_error()
                try:
                    lib.SSL_CTX_set_tmp_ecdh(self.ctx, key)
                finally:
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
        param = lib._X509_STORE_get0_param(store)
        flags = lib.X509_VERIFY_PARAM_get_flags(param)
        return int(flags)

    @verify_flags.setter
    def verify_flags(self, value):
        new_flags = int(value)
        store = lib.SSL_CTX_get_cert_store(self.ctx);
        param = lib._X509_STORE_get0_param(store)
        flags = lib.X509_VERIFY_PARAM_get_flags(param);
        clear = flags & ~new_flags;
        set = ~flags & new_flags;
        if clear:
            param = lib._X509_STORE_get0_param(store)
            if not lib.X509_VERIFY_PARAM_clear_flags(param, clear):
                raise ssl_error(None, 0)
        if set:
            param = lib._X509_STORE_get0_param(store)
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
            index = _thread.get_ident()
            PWINFO_STORAGE[index] = pw_info

            if callable(password):
                pw_info.callable = password
            else:
                if isinstance(password, (str, bytes, bytearray)):
                    pw_info.password = password
                else:
                    raise TypeError("password should be a string or callable")

            lib.SSL_CTX_set_default_passwd_cb(self.ctx, Cryptography_pem_password_cb)
            lib.SSL_CTX_set_default_passwd_cb_userdata(self.ctx, ffi.new_handle(pw_info))

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
                    raise ssl_lib_error()

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
                    raise ssl_lib_error()

            ret = lib.SSL_CTX_check_private_key(self.ctx)
            if ret != 1:
                raise _ssl_seterror(None, -1)
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
                    raise ssl_lib_error()

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
                raise ssl_lib_error()
        finally:
            lib.BIO_free(biobuf)

    def cert_store_stats(self):
        store = lib.SSL_CTX_get_cert_store(self.ctx)
        x509 = 0
        x509_ca = 0
        crl = 0
        objs = store.objs
        count = lib.sk_X509_OBJECT_num(objs)
        for i in range(count):
            obj = lib.sk_X509_OBJECT_value(objs, i)
            _type = lib.Cryptography_X509_OBJECT_get_type(obj)
            if _type == lib.Cryptography_X509_LU_X509:
                x509 += 1
                cert = lib.Cryptography_X509_OBJECT_data_x509(obj)
                if lib.X509_check_ca(cert):
                    x509_ca += 1
            elif _type == lib.Cryptography_X509_LU_CRL:
                crl += 1
            else:
                # Ignore X509_LU_FAIL, X509_LU_RETRY, X509_LU_PKEY.
                # As far as I can tell they are internal states and never
                # stored in a cert store
                pass
        return {'x509': x509, 'x509_ca': x509_ca, 'crl': crl}


#    def _finalize_(self):
#        ctx = self.ctx
#        if ctx:
#            self.ctx = lltype.nullptr(SSL_CTX.TO)
#            libssl_SSL_CTX_free(ctx)
#
#    @staticmethod
#    @unwrap_spec(protocol=int)
#    def descr_new(space, w_subtype, protocol=PY_SSL_VERSION_SSL23):
#        self = space.allocate_instance(SSLContext, w_subtype)
#        self.__init__(space, protocol)
#        return space.wrap(self)

    def session_stats(self):
        stats = {}
        for name, ssl_func in SSL_CTX_STATS:
            stats[name] = ssl_func(self.ctx)
        return stats

    def set_default_verify_paths(self):
        if not lib.SSL_CTX_set_default_verify_paths(self.ctx):
            raise ssl_error("")

#    def descr_get_options(self, space):
#        return space.newlong(libssl_SSL_CTX_get_options(self.ctx))
#
#    def descr_set_options(self, space, w_new_opts):
#        new_opts = space.int_w(w_new_opts)
#        opts = libssl_SSL_CTX_get_options(self.ctx)
#        clear = opts & ~new_opts
#        set = ~opts & new_opts
#        if clear:
#            if HAVE_SSL_CTX_CLEAR_OPTIONS:
#                libssl_SSL_CTX_clear_options(self.ctx, clear)
#            else:
#                raise oefmt(space.w_ValueError,
#                            "can't clear options before OpenSSL 0.9.8m")
#        if set:
#            libssl_SSL_CTX_set_options(self.ctx, set)
#
#    def descr_get_check_hostname(self, space):
#        return space.newbool(self.check_hostname)
#
#    def descr_set_check_hostname(self, space, w_obj):
#        check_hostname = space.is_true(w_obj)
#        if check_hostname and libssl_SSL_CTX_get_verify_mode(self.ctx) == SSL_VERIFY_NONE:
#            raise oefmt(space.w_ValueError,
#                        "check_hostname needs a SSL context with either "
#                        "CERT_OPTIONAL or CERT_REQUIRED")
#        self.check_hostname = check_hostname
#
    def load_dh_params(self, filepath):
        ffi.errno = 0
        if filepath is None:
            raise TypeError("filepath must not be None")
        buf = _str_to_ffi_buffer(filepath, zeroterm=True)
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
                raise ssl_lib_error()
        try:
            if lib.SSL_CTX_set_tmp_dh(self.ctx, dh) == 0:
                raise ssl_lib_error()
        finally:
            lib.DH_free(dh)

#    def cert_store_stats_w(self, space):
#        store = libssl_SSL_CTX_get_cert_store(self.ctx)
#        x509 = 0
#        x509_ca = 0
#        crl = 0
#        for i in range(libssl_sk_X509_OBJECT_num(store[0].c_objs)):
#            obj = libssl_sk_X509_OBJECT_value(store[0].c_objs, i)
#            if intmask(obj.c_type) == X509_LU_X509:
#                x509 += 1
#                if libssl_X509_check_ca(
#                        libssl_pypy_X509_OBJECT_data_x509(obj)):
#                    x509_ca += 1
#            elif intmask(obj.c_type) == X509_LU_CRL:
#                crl += 1
#            else:
#                # Ignore X509_LU_FAIL, X509_LU_RETRY, X509_LU_PKEY.
#                # As far as I can tell they are internal states and never
#                # stored in a cert store
#                pass
#        w_result = space.newdict()
#        space.setitem(w_result,
#                      space.wrap('x509'), space.wrap(x509))
#        space.setitem(w_result,
#                      space.wrap('x509_ca'), space.wrap(x509_ca))
#        space.setitem(w_result,
#                      space.wrap('crl'), space.wrap(crl))
#        return w_result
#
#    @unwrap_spec(protos='bufferstr')
#    def set_npn_protocols_w(self, space, protos):
#        if not HAS_NPN:
#            raise oefmt(space.w_NotImplementedError,
#                        "The NPN extension requires OpenSSL 1.0.1 or later.")
#
#        self.npn_protocols = SSLNpnProtocols(self.ctx, protos)
#
#    @unwrap_spec(protos='bufferstr')
#    def set_alpn_protocols_w(self, space, protos):
#        if not HAS_ALPN:
#            raise oefmt(space.w_NotImplementedError,
#                        "The ALPN extension requires OpenSSL 1.0.2 or later.")
#
#        self.alpn_protocols = SSLAlpnProtocols(self.ctx, protos)
#
    def get_ca_certs(self, binary_form=None):
        binary_mode = bool(binary_form)
        _list = []
        store = lib.SSL_CTX_get_cert_store(self.ctx)
        objs = store.objs
        count = lib.sk_X509_OBJECT_num(objs)
        for i in range(count):
            obj = lib.sk_X509_OBJECT_value(objs, i)
            _type = lib.Cryptography_X509_OBJECT_get_type(obj)
            if _type != lib.Cryptography_X509_LU_X509:
                # not a x509 cert
                continue
            # CA for any purpose
            cert = lib.Cryptography_X509_OBJECT_data_x509(obj)
            if not lib.X509_check_ca(cert):
                continue
            if binary_mode:
                _list.append(_certificate_to_der(cert))
            else:
                _list.append(_decode_certificate(cert))
        return _list

    def set_ecdh_curve(self, name):
        buf = _str_to_ffi_buffer(name, zeroterm=True)
        nid = lib.OBJ_sn2nid(buf)
        if nid == 0:
            raise ValueError("unknown elliptic curve name '%s'" % name)
        key = lib.EC_KEY_new_by_curve_name(nid)
        if not key:
            raise ssl_lib_error()
        try:
            lib.SSL_CTX_set_tmp_ecdh(self.ctx, key)
        finally:
            lib.EC_KEY_free(key)

    def set_servername_callback(self, callback):
        if callback is None:
            lib.SSL_CTX_set_tlsext_servername_callback(self.ctx, ffi.NULL)
            self.servername_callback = None
            return
        if not callable(callback):
            raise TypeError("not a callable object")
        callback_struct = ServernameCallback()
        callback_struct.ctx = self
        callback_struct.set_hostname = callback
        self.servername_callback = callback_struct
        index = id(self)
        SERVERNAME_CALLBACKS[index] = callback_struct
        lib.Cryptography_SSL_CTX_set_tlsext_servername_callback(self.ctx, _servername_callback)
        lib.Cryptography_SSL_CTX_set_tlsext_servername_arg(self.ctx, ffi.new_handle(callback_struct))

@ffi.callback("void(void)")
def _servername_callback(ssl, ad, arg):
    struct = ffi.from_handle(arg)
    w_ctx = struct.w_ctx
    space = struct.space
    w_callback = struct.w_set_hostname
    if not w_ctx.servername_callback:
        # Possible race condition.
        return rffi.cast(rffi.INT, SSL_TLSEXT_ERR_OK)
    # The high-level ssl.SSLSocket object
    index = rffi.cast(lltype.Signed, libssl_SSL_get_app_data(ssl))
    w_ssl = SOCKET_STORAGE.get(index)
    assert isinstance(w_ssl, SSLSocket)
    # The servername callback expects an argument that represents the current
    # SSL connection and that has a .context attribute that can be changed to
    # identify the requested hostname. Since the official API is the Python
    # level API we want to pass the callback a Python level object rather than
    # a _ssl.SSLSocket instance. If there's an "owner" (typically an
    # SSLObject) that will be passed. Otherwise if there's a socket then that
    # will be passed. If both do not exist only then the C-level object is
    # passed.
    if w_ssl.w_owner is not None:
        w_ssl_socket = w_ssl.w_owner()
    elif w_ssl.w_socket is not None:
        w_ssl_socket = w_ssl.w_socket()
    else:
        w_ssl_socket = w_ssl
    if space.is_none(w_ssl_socket):
        ad[0] = rffi.cast(rffi.INT, SSL_AD_INTERNAL_ERROR)
        return rffi.cast(rffi.INT, SSL_TLSEXT_ERR_ALERT_FATAL)

    servername = libssl_SSL_get_servername(ssl, TLSEXT_NAMETYPE_host_name)
    try:
        if not servername:
            w_result = space.call_function(w_callback,
                                           w_ssl_socket, space.w_None, w_ctx)

        else:
            w_servername = space.newbytes(rffi.charp2str(servername))
            try:
                w_servername_idna = space.call_method(
                    w_servername, 'decode', space.wrap('idna'))
            except OperationError as e:
                e.write_unraisable(space, "undecodable server name")
                ad[0] = rffi.cast(rffi.INT, SSL_AD_INTERNAL_ERROR)
                return rffi.cast(rffi.INT, SSL_TLSEXT_ERR_ALERT_FATAL)

            w_result = space.call_function(w_callback,
                                           w_ssl_socket,
                                           w_servername_idna, w_ctx)
    except OperationError as e:
        e.write_unraisable(space, "in servername callback")
        ad[0] = rffi.cast(rffi.INT, SSL_AD_HANDSHAKE_FAILURE)
        return rffi.cast(rffi.INT, SSL_TLSEXT_ERR_ALERT_FATAL)

    if space.is_none(w_result):
        return rffi.cast(rffi.INT, SSL_TLSEXT_ERR_OK)
    else:
        try:
            ad[0] = rffi.cast(rffi.INT, space.int_w(w_result))
        except OperationError as e:
            e.write_unraisable(space, "servername callback result")
            ad[0] = rffi.cast(rffi.INT, SSL_AD_INTERNAL_ERROR)
        return rffi.cast(rffi.INT, SSL_TLSEXT_ERR_ALERT_FATAL)


class ServernameCallback(object):
    ctx = None
SERVERNAME_CALLBACKS = weakref.WeakValueDictionary()

def _str_from_buf(buf):
    return ffi.string(buf).decode('utf-8')

def _asn1obj2py(obj):
    nid = lib.OBJ_obj2nid(obj)
    if nid == lib.NID_undef:
        raise ValueError("Unknown object")
    sn = _str_from_buf(lib.OBJ_nid2sn(nid))
    ln = _str_from_buf(lib.OBJ_nid2ln(nid))
    buf = ffi.new("char[255]")
    length = lib.OBJ_obj2txt(buf, len(buf), obj, 1)
    if length < 0:
        _setSSLError("todo")
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

        self.bio = bio;
        self.eof_written = False

    @property
    def eof(self):
        """Whether the memory BIO is at EOF."""
        return lib.BIO_ctrl_pending(self.bio) == 0 and self.eof_written

    def write(self, _bytes):
        INT_MAX = 2**31-1
        if isinstance(_bytes, memoryview):
            # REVIEW pypy does not support from_buffer of a memoryview
            # copies the data!
            _bytes = bytes(_bytes)
        buf = ffi.from_buffer(_bytes)
        if len(buf) > INT_MAX:
            raise OverflowError("string longer than %d bytes", INT_MAX)

        if self.eof_written:
            raise ssl_error("cannot write() after write_eof()")
        nbytes = lib.BIO_write(self.bio, buf, len(buf));
        if nbytes < 0:
            raise ssl_lib_error()
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

        buf = ffi.new("char[%d]" % count)

        nbytes = lib.BIO_read(self.bio, buf, count);
        #  There should never be any short reads but check anyway.
        if nbytes < count:
            return b""

        return _bytes_with_len(buf, nbytes)

    @property
    def pending(self):
        return lib.BIO_ctrl_pending(self.bio)

RAND_status = lib.RAND_status
RAND_add = lib.RAND_add

def _RAND_bytes(count, pseudo):
    if count < 0:
        raise ValueError("num must be positive")
    buf = ffi.new("unsigned char[]", b"\x00"*count)
    if pseudo:
        ok = lib.RAND_pseudo_bytes(buf, count)
        if ok == 1 or ok == 0:
            return (ffi.string(buf), ok == 1)
    else:
        ok = lib.RAND_bytes(buf, count)
        if ok == 1:
            return ffi.string(buf)
    raise ssl_error("", errcode=lib.ERR_get_error())

def RAND_pseudo_bytes(count):
    return _RAND_bytes(count, True)

def RAND_bytes(count):
    return _RAND_bytes(count, False)

def RAND_add(view, entropy):
    buf = _str_to_ffi_buffer(view)
    lib.RAND_add(buf, len(buf), entropy)


def _cstr_decode_fs(buf):
#define CONVERT(info, target) { \
#        const char *tmp = (info); \
#        target = NULL; \
#        if (!tmp) { Py_INCREF(Py_None); target = Py_None; } \
#        else if ((target = PyUnicode_DecodeFSDefault(tmp)) == NULL) { \
#            target = PyBytes_FromString(tmp); } \
#        if (!target) goto error; \
#    }
    # XXX
    return ffi.string(buf).decode(sys.getfilesystemencoding())

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

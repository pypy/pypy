import weakref

from rpython.rlib import rpoll, rsocket, rthread, rweakref, rgc
from rpython.rlib.rarithmetic import intmask, widen, r_uint
from rpython.rlib.ropenssl import *
from rpython.rlib._rsocket_rffi import MAX_FD_SIZE
from rpython.rlib.rposix import get_saved_errno
from rpython.rlib.rweakref import RWeakValueDictionary
from rpython.rlib.objectmodel import specialize, compute_unique_id
from rpython.rtyper.lltypesystem import lltype, rffi

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt, wrap_oserror
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.unicodehelper import fsdecode
from pypy.module._ssl.ssl_data import (
    LIBRARY_CODES_TO_NAMES, ERROR_CODES_TO_NAMES)
from pypy.module._socket import interp_socket
from pypy.module.exceptions import interp_exceptions


# user defined constants
X509_NAME_MAXLEN = 256
# these mirror ssl.h
PY_SSL_ERROR_NONE, PY_SSL_ERROR_SSL = 0, 1
PY_SSL_ERROR_WANT_READ, PY_SSL_ERROR_WANT_WRITE = 2, 3
PY_SSL_ERROR_WANT_X509_LOOKUP = 4
PY_SSL_ERROR_SYSCALL = 5  # look at error stack/return value/errno
PY_SSL_ERROR_ZERO_RETURN, PY_SSL_ERROR_WANT_CONNECT = 6, 7
# start of non ssl.h errorcodes
PY_SSL_ERROR_EOF = 8  # special case of SSL_ERROR_SYSCALL
PY_SSL_ERROR_INVALID_ERROR_CODE = 9

PY_SSL_CERT_NONE, PY_SSL_CERT_OPTIONAL, PY_SSL_CERT_REQUIRED = 0, 1, 2

PY_SSL_CLIENT, PY_SSL_SERVER = 0, 1

(PY_SSL_VERSION_SSL2, PY_SSL_VERSION_SSL3,
 PY_SSL_VERSION_SSL23, PY_SSL_VERSION_TLS1, PY_SSL_VERSION_TLS1_1,
 PY_SSL_VERSION_TLS1_2) = range(6)

SOCKET_IS_NONBLOCKING, SOCKET_IS_BLOCKING = 0, 1
SOCKET_HAS_TIMED_OUT, SOCKET_HAS_BEEN_CLOSED = 2, 3
SOCKET_TOO_LARGE_FOR_SELECT, SOCKET_OPERATION_OK = 4, 5

HAVE_RPOLL = 'poll' in dir(rpoll)

constants = {}
constants["SSL_ERROR_ZERO_RETURN"] = PY_SSL_ERROR_ZERO_RETURN
constants["SSL_ERROR_WANT_READ"] = PY_SSL_ERROR_WANT_READ
constants["SSL_ERROR_WANT_WRITE"] = PY_SSL_ERROR_WANT_WRITE
constants["SSL_ERROR_WANT_X509_LOOKUP"] = PY_SSL_ERROR_WANT_X509_LOOKUP
constants["SSL_ERROR_SYSCALL"] = PY_SSL_ERROR_SYSCALL
constants["SSL_ERROR_SSL"] = PY_SSL_ERROR_SSL
constants["SSL_ERROR_WANT_CONNECT"] = PY_SSL_ERROR_WANT_CONNECT
constants["SSL_ERROR_EOF"] = PY_SSL_ERROR_EOF
constants["SSL_ERROR_INVALID_ERROR_CODE"] = PY_SSL_ERROR_INVALID_ERROR_CODE

constants["CERT_NONE"]     = PY_SSL_CERT_NONE
constants["CERT_OPTIONAL"] = PY_SSL_CERT_OPTIONAL
constants["CERT_REQUIRED"] = PY_SSL_CERT_REQUIRED

constants["VERIFY_DEFAULT"] = 0
constants["VERIFY_CRL_CHECK_LEAF"] = X509_V_FLAG_CRL_CHECK
constants["VERIFY_CRL_CHECK_CHAIN"] = X509_V_FLAG_CRL_CHECK|X509_V_FLAG_CRL_CHECK_ALL
constants["VERIFY_X509_STRICT"] = X509_V_FLAG_X509_STRICT

constants["HAS_SNI"] = HAS_SNI
constants["HAS_TLS_UNIQUE"] = HAVE_OPENSSL_FINISHED
constants["HAS_ECDH"] = not OPENSSL_NO_ECDH
constants["HAS_NPN"] = HAS_NPN
constants["HAS_ALPN"] = HAS_ALPN

if not OPENSSL_NO_SSL2:
    constants["PROTOCOL_SSLv2"]  = PY_SSL_VERSION_SSL2
if not OPENSSL_NO_SSL3:
    constants["PROTOCOL_SSLv3"]  = PY_SSL_VERSION_SSL3
constants["PROTOCOL_SSLv23"] = PY_SSL_VERSION_SSL23
constants["PROTOCOL_TLSv1"]  = PY_SSL_VERSION_TLS1
if HAVE_TLSv1_2:
    constants["PROTOCOL_TLSv1_1"] = PY_SSL_VERSION_TLS1_1
    constants["OP_NO_TLSv1_1"] = SSL_OP_NO_TLSv1_1
    constants["PROTOCOL_TLSv1_2"] = PY_SSL_VERSION_TLS1_2
    constants["OP_NO_TLSv1_2"] = SSL_OP_NO_TLSv1_2

# protocol options
constants["OP_ALL"] = SSL_OP_ALL & ~SSL_OP_DONT_INSERT_EMPTY_FRAGMENTS
constants["OP_NO_SSLv2"] = SSL_OP_NO_SSLv2
constants["OP_NO_SSLv3"] = SSL_OP_NO_SSLv3
constants["OP_NO_TLSv1"] = SSL_OP_NO_TLSv1
constants["OP_CIPHER_SERVER_PREFERENCE"] = SSL_OP_CIPHER_SERVER_PREFERENCE
constants["OP_SINGLE_DH_USE"] = SSL_OP_SINGLE_DH_USE
constants["OP_SINGLE_ECDH_USE"] = SSL_OP_SINGLE_ECDH_USE
if SSL_OP_NO_COMPRESSION is not None:
    constants["OP_NO_COMPRESSION"] = SSL_OP_NO_COMPRESSION

# OpenSSL version
constants["OPENSSL_VERSION_NUMBER"] = OPENSSL_VERSION_NUMBER
ver = OPENSSL_VERSION_NUMBER
ver, status = divmod(ver, 16)
ver, patch  = divmod(ver, 256)
ver, fix    = divmod(ver, 256)
ver, minor  = divmod(ver, 256)
ver, major  = divmod(ver, 256)
version_info = (major, minor, fix, patch, status)
constants["OPENSSL_VERSION_INFO"] = version_info
constants["_OPENSSL_API_VERSION"] = version_info
constants["OPENSSL_VERSION"] = SSLEAY_VERSION


def ssl_error(space, msg, errno=0, w_errtype=None, errcode=0):
    reason_str = None
    lib_str = None
    if errcode:
        err_lib = libssl_ERR_GET_LIB(errcode)
        err_reason = libssl_ERR_GET_REASON(errcode)
        reason_str = ERROR_CODES_TO_NAMES.get((err_lib, err_reason), None)
        lib_str = LIBRARY_CODES_TO_NAMES.get(err_lib, None)
        msg = rffi.charp2str(libssl_ERR_reason_error_string(errcode))
    if not msg:
        msg = "unknown error"
    if reason_str and lib_str:
        msg = "[%s: %s] %s" % (lib_str, reason_str, msg)
    elif lib_str:
        msg = "[%s] %s" % (lib_str, msg)

    w_exception_class = w_errtype or get_error(space).w_error
    if errno or errcode:
        w_exception = space.call_function(w_exception_class,
                                          space.wrap(errno), space.wrap(msg))
    else:
        w_exception = space.call_function(w_exception_class, space.wrap(msg))
    space.setattr(w_exception, space.wrap("reason"),
                  space.wrap(reason_str) if reason_str else space.w_None)
    space.setattr(w_exception, space.wrap("library"),
                  space.wrap(lib_str) if lib_str else space.w_None)
    return OperationError(w_exception_class, w_exception)

def timeout_error(space, msg):
    w_exc_class = interp_socket.get_error(space, 'timeout')
    w_exc = space.call_function(w_exc_class, space.wrap(msg))
    return OperationError(w_exc_class, w_exc)

class SSLNpnProtocols(object):

    def __init__(self, ctx, protos):
        self.protos = protos
        self.buf, self.bufflag = rffi.get_nonmovingbuffer(protos)
        NPN_STORAGE.set(rffi.cast(lltype.Unsigned, self.buf), self)

        # set both server and client callbacks, because the context
        # can be used to create both types of sockets
        libssl_SSL_CTX_set_next_protos_advertised_cb(
            ctx, self.advertiseNPN_cb, self.buf)
        libssl_SSL_CTX_set_next_proto_select_cb(
            ctx, self.selectNPN_cb, self.buf)

    def __del__(self):
        rffi.free_nonmovingbuffer(
            self.protos, self.buf, self.bufflag)

    @staticmethod
    def advertiseNPN_cb(s, data_ptr, len_ptr, args):
        npn = NPN_STORAGE.get(rffi.cast(lltype.Unsigned, args))
        if npn and npn.protos:
            data_ptr[0] = npn.buf
            len_ptr[0] = rffi.cast(rffi.UINT, len(npn.protos))
        else:
            data_ptr[0] = lltype.nullptr(rffi.CCHARP.TO)
            len_ptr[0] = rffi.cast(rffi.UINT, 0)

        return rffi.cast(rffi.INT, SSL_TLSEXT_ERR_OK)

    @staticmethod
    def selectNPN_cb(s, out_ptr, outlen_ptr, server, server_len, args):
        npn = NPN_STORAGE.get(rffi.cast(lltype.Unsigned, args))
        if npn and npn.protos:
            client = npn.buf
            client_len = len(npn.protos)
        else:
            client = lltype.nullptr(rffi.CCHARP.TO)
            client_len = 0

        libssl_SSL_select_next_proto(out_ptr, outlen_ptr,
                                     server, server_len,
                                     client, client_len)
        return rffi.cast(rffi.INT, SSL_TLSEXT_ERR_OK)


class SSLAlpnProtocols(object):

    def __init__(self, ctx, protos):
        self.protos = protos
        self.buf, self.bufflag = rffi.get_nonmovingbuffer(protos)
        ALPN_STORAGE.set(rffi.cast(lltype.Unsigned, self.buf), self)

        with rffi.scoped_str2charp(protos) as protos_buf:
            if libssl_SSL_CTX_set_alpn_protos(
                    ctx, rffi.cast(rffi.UCHARP, protos_buf), len(protos)):
                raise MemoryError
        libssl_SSL_CTX_set_alpn_select_cb(
            ctx, self.selectALPN_cb, self.buf)

    def __del__(self):
        rffi.free_nonmovingbuffer(
            self.protos, self.buf, self.bufflag)

    @staticmethod
    def selectALPN_cb(s, out_ptr, outlen_ptr, client, client_len, args):
        alpn = ALPN_STORAGE.get(rffi.cast(lltype.Unsigned, args))
        if alpn and alpn.protos:
            server = alpn.buf
            server_len = len(alpn.protos)
        else:
            server = lltype.nullptr(rffi.CCHARP.TO)
            server_len = 0

        ret = libssl_SSL_select_next_proto(out_ptr, outlen_ptr,
                                           server, server_len,
                                           client, client_len)
        if ret != OPENSSL_NPN_NEGOTIATED:
            return rffi.cast(rffi.INT, SSL_TLSEXT_ERR_NOACK)
        return rffi.cast(rffi.INT, SSL_TLSEXT_ERR_OK)


NPN_STORAGE = RWeakValueDictionary(r_uint, SSLNpnProtocols)
ALPN_STORAGE = RWeakValueDictionary(r_uint, SSLAlpnProtocols)

SOCKET_STORAGE = RWeakValueDictionary(int, W_Root)


if HAVE_OPENSSL_RAND:
    # helper routines for seeding the SSL PRNG
    @unwrap_spec(string=str, entropy=float)
    def RAND_add(space, string, entropy):
        """RAND_add(string, entropy)


        Mix string into the OpenSSL PRNG state.  entropy (a float) is a lower
        bound on the entropy contained in string."""
        with rffi.scoped_nonmovingbuffer(string) as buf:
            libssl_RAND_add(buf, len(string), entropy)

    def _RAND_bytes(space, n, pseudo):
        if n < 0:
            raise oefmt(space.w_ValueError, "num must be positive")

        with rffi.scoped_alloc_buffer(n) as buf:
            if pseudo:
                ok = libssl_RAND_pseudo_bytes(
                    rffi.cast(rffi.UCHARP, buf.raw), n)
                if ok == 0 or ok == 1:
                    return space.newtuple([
                        space.newbytes(buf.str(n)),
                        space.wrap(ok == 1),
                    ])
            else:
                ok = libssl_RAND_bytes(
                    rffi.cast(rffi.UCHARP, buf.raw), n)
                if ok == 1:
                    return space.newbytes(buf.str(n))

        raise ssl_error(space, "", errcode=libssl_ERR_get_error())

    @unwrap_spec(n=int)
    def RAND_bytes(space, n):
        """RAND_bytes(n) -> bytes

        Generate n cryptographically strong pseudo-random bytes."""
        return _RAND_bytes(space, n, pseudo=False)

    @unwrap_spec(n=int)
    def RAND_pseudo_bytes(space, n):
        """RAND_pseudo_bytes(n) -> (bytes, is_cryptographic)

        Generate n pseudo-random bytes. is_cryptographic is True if the bytes
        generated are cryptographically strong."""
        return _RAND_bytes(space, n, pseudo=True)

    def RAND_status(space):
        """RAND_status() -> 0 or 1

        Returns 1 if the OpenSSL PRNG has been seeded with enough data
        and 0 if not.  It is necessary to seed the PRNG with RAND_add()
        on some platforms before using the ssl() function."""

        res = libssl_RAND_status()
        return space.wrap(res)

    if HAVE_OPENSSL_RAND_EGD:
        @unwrap_spec(path=str)
        def RAND_egd(space, path):
            """RAND_egd(path) -> bytes

            Queries the entropy gather daemon (EGD) on socket path.  Returns number
            of bytes read.  Raises socket.sslerror if connection to EGD fails or
            if it does provide enough data to seed PRNG."""
            with rffi.scoped_str2charp(path) as socket_path:
                bytes = libssl_RAND_egd(socket_path)
            if bytes == -1:
                raise ssl_error(space,
                                "EGD connection failed or EGD did not return "
                                "enough data to seed the PRNG")
            return space.wrap(bytes)
    else:
        # Dummy func for platforms missing RAND_egd(). Most likely LibreSSL.
        @unwrap_spec(path=str)
        def RAND_egd(space, path):
            raise ssl_error(space, "RAND_egd unavailable")


class SSLSocket(W_Root):
    def __init__(self, space):
        self.w_socket = None
        self.ssl = lltype.nullptr(SSL.TO)
        self.peer_cert = lltype.nullptr(X509.TO)
        self.shutdown_seen_zero = False
        self.handshake_done = False
        self.register_finalizer(space)

    def _finalize_(self):
        peer_cert = self.peer_cert
        if peer_cert:
            self.peer_cert = lltype.nullptr(X509.TO)
            libssl_X509_free(peer_cert)
        ssl = self.ssl
        if ssl:
            self.ssl = lltype.nullptr(SSL.TO)
            libssl_SSL_free(ssl)

    @unwrap_spec(data='bufferstr')
    def write(self, space, data):
        """write(s) -> len

        Writes the string s into the SSL object.  Returns the number
        of bytes written."""
        w_socket = self._get_socket(space)

        sockstate = checkwait(space, w_socket, True)
        if sockstate == SOCKET_HAS_TIMED_OUT:
            raise timeout_error(space, "The write operation timed out")
        elif sockstate == SOCKET_HAS_BEEN_CLOSED:
            raise ssl_error(space, "Underlying socket has been closed.")
        elif sockstate == SOCKET_TOO_LARGE_FOR_SELECT:
            raise ssl_error(space, "Underlying socket too large for select().")

        num_bytes = 0
        while True:
            err = 0

            num_bytes = libssl_SSL_write(self.ssl, data, len(data))
            err = libssl_SSL_get_error(self.ssl, num_bytes)

            if err == SSL_ERROR_WANT_READ:
                sockstate = checkwait(space, w_socket, False)
            elif err == SSL_ERROR_WANT_WRITE:
                sockstate = checkwait(space, w_socket, True)
            else:
                sockstate = SOCKET_OPERATION_OK

            if sockstate == SOCKET_HAS_TIMED_OUT:
                raise timeout_error(space, "The write operation timed out")
            elif sockstate == SOCKET_HAS_BEEN_CLOSED:
                raise ssl_error(space, "Underlying socket has been closed.")
            elif sockstate == SOCKET_IS_NONBLOCKING:
                break

            if err == SSL_ERROR_WANT_READ or err == SSL_ERROR_WANT_WRITE:
                continue
            else:
                break

        if num_bytes > 0:
            return space.wrap(num_bytes)
        else:
            raise _ssl_seterror(space, self, num_bytes)

    def pending(self, space):
        """pending() -> count

        Returns the number of already decrypted bytes available for read,
        pending on the connection."""
        count = libssl_SSL_pending(self.ssl)
        if count < 0:
            raise _ssl_seterror(space, self, count)
        return space.wrap(count)

    @unwrap_spec(num_bytes=int)
    def read(self, space, num_bytes, w_buffer=None):
        """read([len]) -> string

        Read up to len bytes from the SSL socket."""
        w_socket = self._get_socket(space)

        count = libssl_SSL_pending(self.ssl)
        if not count:
            sockstate = checkwait(space, w_socket, False)
            if sockstate == SOCKET_HAS_TIMED_OUT:
                raise timeout_error(space, "The read operation timed out")
            elif sockstate == SOCKET_TOO_LARGE_FOR_SELECT:
                raise ssl_error(space,
                                "Underlying socket too large for select().")
            elif sockstate == SOCKET_HAS_BEEN_CLOSED:
                if libssl_SSL_get_shutdown(self.ssl) == SSL_RECEIVED_SHUTDOWN:
                    if space.is_none(w_buffer):
                        return space.newbytes('')
                    else:
                        return space.wrap(0)
                raise ssl_error(space,
                                "Socket closed without SSL shutdown handshake")

        if w_buffer:
            rwbuffer = space.getarg_w('w*', w_buffer)
            buflen = rwbuffer.getlength()
            if not 0 < num_bytes <= buflen:
                num_bytes = buflen
        else:
            if num_bytes < 0:
                raise oefmt(space.w_ValueError, "size should not be negative")
            rwbuffer = None

        with rffi.scoped_alloc_buffer(num_bytes) as buf:
            while True:
                err = 0

                count = libssl_SSL_read(self.ssl, buf.raw, num_bytes)
                err = libssl_SSL_get_error(self.ssl, count)

                if err == SSL_ERROR_WANT_READ:
                    sockstate = checkwait(space, w_socket, False)
                elif err == SSL_ERROR_WANT_WRITE:
                    sockstate = checkwait(space, w_socket, True)
                elif (err == SSL_ERROR_ZERO_RETURN and
                      libssl_SSL_get_shutdown(self.ssl) == SSL_RECEIVED_SHUTDOWN):
                    if space.is_none(w_buffer):
                        return space.newbytes('')
                    else:
                        return space.wrap(0)
                else:
                    sockstate = SOCKET_OPERATION_OK

                if sockstate == SOCKET_HAS_TIMED_OUT:
                    raise timeout_error(space, "The read operation timed out")
                elif sockstate == SOCKET_IS_NONBLOCKING:
                    break

                if err == SSL_ERROR_WANT_READ or err == SSL_ERROR_WANT_WRITE:
                    continue
                else:
                    break

            if count <= 0:
                raise _ssl_seterror(space, self, count)

            result = buf.str(count)

        if rwbuffer is not None:
            rwbuffer.setslice(0, result)
            return space.wrap(count)
        else:
            return space.newbytes(result)

    def _get_socket(self, space):
        w_socket = self.w_socket()
        if w_socket is None:
            raise ssl_error(space, "Underlying socket connection gone")

        # just in case the blocking state of the socket has been changed
        w_timeout = space.call_method(w_socket, "gettimeout")
        nonblocking = not space.is_w(w_timeout, space.w_None)
        libssl_BIO_set_nbio(libssl_SSL_get_rbio(self.ssl), nonblocking)
        libssl_BIO_set_nbio(libssl_SSL_get_wbio(self.ssl), nonblocking)

        return w_socket

    def do_handshake(self, space):
        w_socket = self._get_socket(space)

        # Actually negotiate SSL connection
        # XXX If SSL_do_handshake() returns 0, it's also a failure.
        while True:
            ret = libssl_SSL_do_handshake(self.ssl)
            err = libssl_SSL_get_error(self.ssl, ret)
            # XXX PyErr_CheckSignals()
            if err == SSL_ERROR_WANT_READ:
                sockstate = checkwait(space, w_socket, False)
            elif err == SSL_ERROR_WANT_WRITE:
                sockstate = checkwait(space, w_socket, True)
            else:
                sockstate = SOCKET_OPERATION_OK
            if sockstate == SOCKET_HAS_TIMED_OUT:
                raise timeout_error(space, "The handshake operation timed out")
            elif sockstate == SOCKET_HAS_BEEN_CLOSED:
                raise ssl_error(space, "Underlying socket has been closed.")
            elif sockstate == SOCKET_TOO_LARGE_FOR_SELECT:
                raise ssl_error(space,
                                "Underlying socket too large for select().")
            elif sockstate == SOCKET_IS_NONBLOCKING:
                break

            if err == SSL_ERROR_WANT_READ or err == SSL_ERROR_WANT_WRITE:
                continue
            else:
                break

        if ret <= 0:
            raise _ssl_seterror(space, self, ret)

        if self.peer_cert:
            libssl_X509_free(self.peer_cert)
        self.peer_cert = libssl_SSL_get_peer_certificate(self.ssl)
        self.handshake_done = True

    def shutdown(self, space):
        w_socket = self._get_socket(space)

        # Guard against closed socket
        w_fileno = space.call_method(w_socket, "fileno")
        if space.int_w(w_fileno) < 0:
            raise ssl_error(space, "Underlying socket has been closed")

        zeros = 0
        while True:
            # Disable read-ahead so that unwrap can work correctly.
            # Otherwise OpenSSL might read in too much data,
            # eating clear text data that happens to be
            # transmitted after the SSL shutdown.
            # Should be safe to call repeatedly everytime this
            # function is used and the shutdown_seen_zero != 0
            # condition is met.
            if self.shutdown_seen_zero:
                libssl_SSL_set_read_ahead(self.ssl, 0)
            ret = libssl_SSL_shutdown(self.ssl)

            # if err == 1, a secure shutdown with SSL_shutdown() is complete
            if ret > 0:
                break
            if ret == 0:
                # Don't loop endlessly; instead preserve legacy
                # behaviour of trying SSL_shutdown() only twice.
                # This looks necessary for OpenSSL < 0.9.8m
                zeros += 1
                if zeros > 1:
                    break
                # Shutdown was sent, now try receiving
                self.shutdown_seen_zero = True
                continue

            # Possibly retry shutdown until timeout or failure
            ssl_err = libssl_SSL_get_error(self.ssl, ret)
            if ssl_err == SSL_ERROR_WANT_READ:
                sockstate = checkwait(space, w_socket, False)
            elif ssl_err == SSL_ERROR_WANT_WRITE:
                sockstate = checkwait(space, w_socket, True)
            else:
                break

            if sockstate == SOCKET_HAS_TIMED_OUT:
                if ssl_err == SSL_ERROR_WANT_READ:
                    raise timeout_error(space, "The read operation timed out")
                else:
                    raise timeout_error(space, "The write operation timed out")
            elif sockstate == SOCKET_TOO_LARGE_FOR_SELECT:
                raise ssl_error(space,
                                "Underlying socket too large for select().")
            elif sockstate != SOCKET_OPERATION_OK:
                # Retain the SSL error code
                break

        if ret < 0:
            raise _ssl_seterror(space, self, ret)

        return w_socket

    def cipher(self, space):
        if not self.ssl:
            return space.w_None
        current = libssl_SSL_get_current_cipher(self.ssl)
        if not current:
            return space.w_None

        name = libssl_SSL_CIPHER_get_name(current)
        w_name = space.wrap(rffi.charp2str(name)) if name else space.w_None

        proto = libssl_SSL_CIPHER_get_version(current)
        w_proto = space.wrap(rffi.charp2str(proto)) if proto else space.w_None

        bits = libssl_SSL_CIPHER_get_bits(current,
                                          lltype.nullptr(rffi.INTP.TO))
        w_bits = space.newint(bits)
        return space.newtuple([w_name, w_proto, w_bits])

    @unwrap_spec(der=bool)
    def peer_certificate(self, space, der=False):
        """peer_certificate([der=False]) -> certificate

        Returns the certificate for the peer.  If no certificate was
        provided, returns None.  If a certificate was provided, but not
        validated, returns an empty dictionary.  Otherwise returns a
        dict containing information about the peer certificate.

        If the optional argument is True, returns a DER-encoded copy of
        the peer certificate, or None if no certificate was provided.
        This will return the certificate even if it wasn't validated.
        """
        if not self.handshake_done:
            raise oefmt(space.w_ValueError, "hanshake not done yet")
        if not self.peer_cert:
            return space.w_None

        if der:
            # return cert in DER-encoded format
            return _certificate_to_der(space, self.peer_cert)
        else:
            verification = libssl_SSL_CTX_get_verify_mode(
                libssl_SSL_get_SSL_CTX(self.ssl))
            if not verification & SSL_VERIFY_PEER:
                return space.newdict()
            else:
                return _decode_certificate(space, self.peer_cert)

    def selected_npn_protocol(self, space):
        if not HAS_NPN:
            raise oefmt(space.w_NotImplementedError,
                        "The NPN extension requires OpenSSL 1.0.1 or later.")
        with lltype.scoped_alloc(rffi.CCHARPP.TO, 1) as out_ptr:
            with lltype.scoped_alloc(rffi.UINTP.TO, 1) as len_ptr:
                libssl_SSL_get0_next_proto_negotiated(self.ssl,
                                                      out_ptr, len_ptr)
                if out_ptr[0]:
                    return space.wrap(
                        rffi.charpsize2str(out_ptr[0], intmask(len_ptr[0])))

    def selected_alpn_protocol(self, space):
        if not HAS_ALPN:
            raise oefmt(space.w_NotImplementedError,
                        "The ALPN extension requires OpenSSL 1.0.2 or later.")
        with lltype.scoped_alloc(rffi.CCHARPP.TO, 1) as out_ptr:
            with lltype.scoped_alloc(rffi.UINTP.TO, 1) as len_ptr:
                libssl_SSL_get0_alpn_selected(self.ssl,
                                              out_ptr, len_ptr)
                if out_ptr[0]:
                    return space.wrap(
                        rffi.charpsize2str(out_ptr[0], intmask(len_ptr[0])))

    def compression_w(self, space):
        if not self.ssl:
            return space.w_None
        comp_method = libssl_SSL_get_current_compression(self.ssl)
        if not comp_method or intmask(comp_method[0].c_type) == NID_undef:
            return space.w_None
        short_name = libssl_OBJ_nid2sn(comp_method[0].c_type)
        if not short_name:
            return space.w_None
        return space.wrap(rffi.charp2str(short_name))

    def version_w(self, space):
        if not self.ssl:
            return space.w_None
        version = libssl_SSL_get_version(self.ssl)
        if not version:
            return space.w_None
        return space.wrap(rffi.charp2str(version))

    def tls_unique_cb_w(self, space):
        """Returns the 'tls-unique' channel binding data, as defined by RFC 5929.
        If the TLS handshake is not yet complete, None is returned"""

        # In case of 'tls-unique' it will be 12 bytes for TLS, 36
        # bytes for older SSL, but let's be safe
        CB_MAXLEN = 128

        with lltype.scoped_alloc(rffi.CCHARP.TO, CB_MAXLEN) as buf:
            if (libssl_SSL_session_reused(self.ssl) ^
                (self.socket_type == PY_SSL_CLIENT)):
                # if session is resumed XOR we are the client
                length = libssl_SSL_get_finished(self.ssl, buf, CB_MAXLEN)
            else:
                # if a new session XOR we are the server
                length = libssl_SSL_get_peer_finished(self.ssl, buf, CB_MAXLEN)

            if length > 0:
                return space.newbytes(rffi.charpsize2str(buf, intmask(length)))

    def descr_get_context(self, space):
        return self.w_ctx

    def descr_set_context(self, space, w_ctx):
        ctx = space.interp_w(SSLContext, w_ctx)
        if not HAS_SNI:
            raise oefmt(space.w_NotImplementedError,
                        "setting a socket's context "
                        "is not supported by your OpenSSL library")
        self.w_ctx = w_ctx
        libssl_SSL_set_SSL_CTX(self.ssl, ctx.ctx)


SSLSocket.typedef = TypeDef("_ssl._SSLSocket",
    write = interp2app(SSLSocket.write),
    pending = interp2app(SSLSocket.pending),
    read = interp2app(SSLSocket.read),
    do_handshake = interp2app(SSLSocket.do_handshake),
    shutdown = interp2app(SSLSocket.shutdown),
    cipher = interp2app(SSLSocket.cipher),
    peer_certificate = interp2app(SSLSocket.peer_certificate),
    selected_npn_protocol = interp2app(SSLSocket.selected_npn_protocol),
    selected_alpn_protocol = interp2app(SSLSocket.selected_alpn_protocol),
    compression = interp2app(SSLSocket.compression_w),
    version = interp2app(SSLSocket.version_w),
    tls_unique_cb = interp2app(SSLSocket.tls_unique_cb_w),
    context=GetSetProperty(SSLSocket.descr_get_context,
                           SSLSocket.descr_set_context),
)

def _certificate_to_der(space, certificate):
    with lltype.scoped_alloc(rffi.CCHARPP.TO, 1) as buf_ptr:
        buf_ptr[0] = lltype.nullptr(rffi.CCHARP.TO)
        length = libssl_i2d_X509(certificate, buf_ptr)
        if length < 0:
            raise _ssl_seterror(space, None, 0)
        try:
            return space.newbytes(rffi.charpsize2str(buf_ptr[0], length))
        finally:
            libssl_OPENSSL_free(buf_ptr[0])

def _decode_certificate(space, certificate):
    w_retval = space.newdict()

    w_peer = _create_tuple_for_X509_NAME(
        space, libssl_X509_get_subject_name(certificate))
    space.setitem(w_retval, space.wrap("subject"), w_peer)

    w_issuer = _create_tuple_for_X509_NAME(
        space, libssl_X509_get_issuer_name(certificate))
    space.setitem(w_retval, space.wrap("issuer"), w_issuer)

    space.setitem(w_retval, space.wrap("version"),
                  space.wrap(libssl_X509_get_version(certificate) + 1))

    biobuf = libssl_BIO_new(libssl_BIO_s_mem())
    try:

        libssl_BIO_reset(biobuf)
        serialNumber = libssl_X509_get_serialNumber(certificate)
        libssl_i2a_ASN1_INTEGER(biobuf, serialNumber)
        # should not exceed 20 octets, 160 bits, so buf is big enough
        with lltype.scoped_alloc(rffi.CCHARP.TO, 100) as buf:
            length = libssl_BIO_gets(biobuf, buf, 99)
            if length < 0:
                raise _ssl_seterror(space, None, length)

            w_serial = space.wrap(rffi.charpsize2str(buf, length))
        space.setitem(w_retval, space.wrap("serialNumber"), w_serial)

        libssl_BIO_reset(biobuf)
        notBefore = libssl_X509_get_notBefore(certificate)
        libssl_ASN1_TIME_print(biobuf, notBefore)
        with lltype.scoped_alloc(rffi.CCHARP.TO, 100) as buf:
            length = libssl_BIO_gets(biobuf, buf, 99)
            if length < 0:
                raise _ssl_seterror(space, None, length)
            w_date = space.wrap(rffi.charpsize2str(buf, length))
        space.setitem(w_retval, space.wrap("notBefore"), w_date)

        libssl_BIO_reset(biobuf)
        notAfter = libssl_X509_get_notAfter(certificate)
        libssl_ASN1_TIME_print(biobuf, notAfter)
        with lltype.scoped_alloc(rffi.CCHARP.TO, 100) as buf:
            length = libssl_BIO_gets(biobuf, buf, 99)
            if length < 0:
                raise _ssl_seterror(space, None, length)
            w_date = space.wrap(rffi.charpsize2str(buf, length))
        space.setitem(w_retval, space.wrap("notAfter"), w_date)
    finally:
        libssl_BIO_free(biobuf)

    # Now look for subjectAltName
    w_alt_names = _get_peer_alt_names(space, certificate)
    if w_alt_names is not space.w_None:
        space.setitem(w_retval, space.wrap("subjectAltName"), w_alt_names)

    # Authority Information Access: OCSP URIs
    w_ocsp = _get_aia_uri(space, certificate, NID_ad_OCSP)
    if not space.is_none(w_ocsp):
        space.setitem(w_retval, space.wrap("OCSP"), w_ocsp)
    w_issuers = _get_aia_uri(space, certificate, NID_ad_ca_issuers)
    if not space.is_none(w_issuers):
        space.setitem(w_retval, space.wrap("caIssuers"), w_issuers)

    # CDP (CRL distribution points)
    w_cdp = _get_crl_dp(space, certificate)
    if not space.is_none(w_cdp):
        space.setitem(w_retval, space.wrap("crlDistributionPoints"), w_cdp)

    return w_retval


def _create_tuple_for_X509_NAME(space, xname):
    entry_count = libssl_X509_NAME_entry_count(xname)
    dn_w = []
    rdn_w = []
    rdn_level = -1
    for index in range(entry_count):
        entry = libssl_X509_NAME_get_entry(xname, index)
        # check to see if we've gotten to a new RDN
        entry_level = intmask(entry[0].c_set)
        if rdn_level >= 0:
            if rdn_level != entry_level:
                # yes, new RDN
                # add old RDN to DN
                dn_w.append(space.newtuple(list(rdn_w)))
                rdn_w = []
        rdn_level = entry_level

        # Now add this attribute to the current RDN
        name = libssl_X509_NAME_ENTRY_get_object(entry)
        value = libssl_X509_NAME_ENTRY_get_data(entry)
        attr = _create_tuple_for_attribute(space, name, value)
        rdn_w.append(attr)

    # Now, there is typically a dangling RDN
    if rdn_w:
        dn_w.append(space.newtuple(list(rdn_w)))
    return space.newtuple(list(dn_w))


def _get_peer_alt_names(space, certificate):
    # this code follows the procedure outlined in
    # OpenSSL's crypto/x509v3/v3_prn.c:X509v3_EXT_print()
    # function to extract the STACK_OF(GENERAL_NAME),
    # then iterates through the stack to add the
    # names.

    if not certificate:
        return space.w_None

    # get a memory buffer
    biobuf = libssl_BIO_new(libssl_BIO_s_mem())

    try:
        alt_names_w = []
        i = -1
        while True:
            i = libssl_X509_get_ext_by_NID(
                certificate, NID_subject_alt_name, i)
            if i < 0:
                break

            # now decode the altName
            ext = libssl_X509_get_ext(certificate, i)
            method = libssl_X509V3_EXT_get(ext)
            if not method:
                raise ssl_error(space,
                                "No method for internalizing subjectAltName!'")

            with lltype.scoped_alloc(rffi.CCHARPP.TO, 1) as p_ptr:
                p_ptr[0] = ext[0].c_value.c_data
                length = intmask(ext[0].c_value.c_length)
                null = lltype.nullptr(rffi.VOIDP.TO)
                if method[0].c_it:
                    names = rffi.cast(GENERAL_NAMES, libssl_ASN1_item_d2i(
                        null, p_ptr, length,
                        libssl_ASN1_ITEM_ptr(method[0].c_it)))
                else:
                    names = rffi.cast(GENERAL_NAMES, method[0].c_d2i(
                        null, p_ptr, length))

            try:
                for j in range(libssl_sk_GENERAL_NAME_num(names)):
                    # Get a rendering of each name in the set of names

                    name = libssl_sk_GENERAL_NAME_value(names, j)
                    gntype = intmask(name.c_type)
                    if gntype == GEN_DIRNAME:
                        # we special-case DirName as a tuple of tuples of
                        # attributes
                        dirname = libssl_pypy_GENERAL_NAME_dirn(name)
                        w_t = space.newtuple([
                            space.wrap("DirName"),
                            _create_tuple_for_X509_NAME(space, dirname)
                            ])
                    elif gntype in (GEN_EMAIL, GEN_DNS, GEN_URI):
                        # GENERAL_NAME_print() doesn't handle NULL bytes in
                        # ASN1_string correctly, CVE-2013-4238
                        if gntype == GEN_EMAIL:
                            v = space.wrap("email")
                        elif gntype == GEN_DNS:
                            v = space.wrap("DNS")
                        elif gntype == GEN_URI:
                            v = space.wrap("URI")
                        else:
                            assert False
                        as_ = libssl_pypy_GENERAL_NAME_dirn(name)
                        as_ = rffi.cast(ASN1_STRING, as_)
                        buf = libssl_ASN1_STRING_data(as_)
                        length = libssl_ASN1_STRING_length(as_)
                        w_t = space.newtuple([
                            v, space.wrap(rffi.charpsize2str(buf, length))])
                    else:
                        # for everything else, we use the OpenSSL print form
                        if gntype not in (GEN_OTHERNAME, GEN_X400, GEN_EDIPARTY,
                                          GEN_IPADD, GEN_RID):
                            space.warn(space.wrap("Unknown general name type"),
                                       space.w_RuntimeWarning)
                        libssl_BIO_reset(biobuf)
                        libssl_GENERAL_NAME_print(biobuf, name)
                        with lltype.scoped_alloc(rffi.CCHARP.TO, 2048) as buf:
                            length = libssl_BIO_gets(biobuf, buf, 2047)
                            if length < 0:
                                raise _ssl_seterror(space, None, 0)

                            v = rffi.charpsize2str(buf, length)
                        v1, v2 = v.split(':', 1)
                        w_t = space.newtuple([space.wrap(v1),
                                              space.wrap(v2)])

                    alt_names_w.append(w_t)
            finally:
                libssl_pypy_GENERAL_NAME_pop_free(names)
    finally:
        libssl_BIO_free(biobuf)

    if alt_names_w:
        return space.newtuple(list(alt_names_w))
    else:
        return space.w_None


def _create_tuple_for_attribute(space, name, value):
    with lltype.scoped_alloc(rffi.CCHARP.TO, X509_NAME_MAXLEN) as buf:
        length = libssl_OBJ_obj2txt(buf, X509_NAME_MAXLEN, name, 0)
        if length < 0:
            raise _ssl_seterror(space, None, 0)
        w_name = space.wrap(rffi.charpsize2str(buf, length))

    with lltype.scoped_alloc(rffi.CCHARPP.TO, 1) as buf_ptr:
        length = libssl_ASN1_STRING_to_UTF8(buf_ptr, value)
        if length < 0:
            raise _ssl_seterror(space, None, 0)
        try:
            w_value = space.newbytes(rffi.charpsize2str(buf_ptr[0], length))
            w_value = space.call_method(w_value, "decode", space.wrap("utf-8"))
        finally:
            libssl_OPENSSL_free(buf_ptr[0])

    return space.newtuple([w_name, w_value])


def _get_aia_uri(space, certificate, nid):
    info = rffi.cast(AUTHORITY_INFO_ACCESS, libssl_X509_get_ext_d2i(
        certificate, NID_info_access, None, None))
    try:
        if not info or libssl_sk_ACCESS_DESCRIPTION_num(info) == 0:
            return

        result_w = []
        for i in range(libssl_sk_ACCESS_DESCRIPTION_num(info)):
            ad = libssl_sk_ACCESS_DESCRIPTION_value(info, i)
            if libssl_OBJ_obj2nid(ad[0].c_method) != nid:
                continue

            name = ad[0].c_location
            gntype = intmask(name.c_type)
            if gntype != GEN_URI:
                continue
            uri = libssl_pypy_GENERAL_NAME_uri(name)
            length = intmask(uri.c_length)
            s_uri = rffi.charpsize2str(uri.c_data, length)
            result_w.append(space.wrap(s_uri))
        return space.newtuple(result_w[:])
    finally:
        libssl_AUTHORITY_INFO_ACCESS_free(info)

def _get_crl_dp(space, certificate):
    if OPENSSL_VERSION_NUMBER >= 0x10001000:
        # Calls x509v3_cache_extensions and sets up crldp
        libssl_X509_check_ca(certificate)
        dps = certificate[0].c_crldp
    else:
        dps = rffi.cast(stack_st_DIST_POINT, libssl_X509_get_ext_d2i(
            certificate, NID_crl_distribution_points, None, None))
    if not dps:
        return None

    try:
        cdp_w = []
        for i in range(libssl_sk_DIST_POINT_num(dps)):
            dp = libssl_sk_DIST_POINT_value(dps, i)
            gns = libssl_pypy_DIST_POINT_fullname(dp)

            for j in range(libssl_sk_GENERAL_NAME_num(gns)):
                name = libssl_sk_GENERAL_NAME_value(gns, j)
                gntype = intmask(name.c_type)
                if gntype != GEN_URI:
                    continue
                uri = libssl_pypy_GENERAL_NAME_uri(name)
                length = intmask(uri.c_length)
                s_uri = rffi.charpsize2str(uri.c_data, length)
                cdp_w.append(space.wrap(s_uri))
    finally:
        if OPENSSL_VERSION_NUMBER < 0x10001000:
            libssl_sk_DIST_POINT_free(dps)
    return space.newtuple(cdp_w[:])

def new_sslobject(space, ctx, w_sock, side, server_hostname):
    ss = SSLSocket(space)

    sock_fd = space.int_w(space.call_method(w_sock, "fileno"))
    w_timeout = space.call_method(w_sock, "gettimeout")
    has_timeout = not space.is_none(w_timeout)

    ss.ssl = libssl_SSL_new(ctx) # new ssl struct
    libssl_SSL_set_fd(ss.ssl, sock_fd) # set the socket for SSL
    # The ACCEPT_MOVING_WRITE_BUFFER flag is necessary because the address
    # of a str object may be changed by the garbage collector.
    libssl_SSL_set_mode(
        ss.ssl, SSL_MODE_AUTO_RETRY | SSL_MODE_ACCEPT_MOVING_WRITE_BUFFER)

    if server_hostname:
        libssl_SSL_set_tlsext_host_name(ss.ssl, server_hostname);

    # If the socket is in non-blocking mode or timeout mode, set the BIO
    # to non-blocking mode (blocking is the default)
    if has_timeout:
        # Set both the read and write BIO's to non-blocking mode
        libssl_BIO_set_nbio(libssl_SSL_get_rbio(ss.ssl), 1)
        libssl_BIO_set_nbio(libssl_SSL_get_wbio(ss.ssl), 1)

    if side == PY_SSL_CLIENT:
        libssl_SSL_set_connect_state(ss.ssl)
    else:
        libssl_SSL_set_accept_state(ss.ssl)
    ss.socket_type = side

    ss.w_socket = weakref.ref(w_sock)
    return ss

def checkwait(space, w_sock, writing):
    """If the socket has a timeout, do a select()/poll() on the socket.
    The argument writing indicates the direction.
    Returns one of the possibilities in the timeout_state enum (above)."""

    w_timeout = space.call_method(w_sock, "gettimeout")
    if space.is_w(w_timeout, space.w_None):
        return SOCKET_IS_BLOCKING
    elif space.float_w(w_timeout) == 0.0:
        return SOCKET_IS_NONBLOCKING
    sock_timeout = space.float_w(w_timeout)

    sock_fd = space.int_w(space.call_method(w_sock, "fileno"))

    # guard against closed socket
    if sock_fd < 0:
        return SOCKET_HAS_BEEN_CLOSED

    # see if the socket is ready

    # Prefer poll, if available, since you can poll() any fd
    # which can't be done with select().
    if HAVE_RPOLL:
        if writing:
            fddict = {sock_fd: rpoll.POLLOUT}
        else:
            fddict = {sock_fd: rpoll.POLLIN}

        # socket's timeout is in seconds, poll's timeout in ms
        timeout = int(sock_timeout * 1000 + 0.5)
        try:
            ready = rpoll.poll(fddict, timeout)
        except rpoll.PollError as e:
            message = e.get_msg()
            raise ssl_error(space, message, e.errno)
    else:
        if MAX_FD_SIZE is not None and sock_fd >= MAX_FD_SIZE:
            return SOCKET_TOO_LARGE_FOR_SELECT

        try:
            if writing:
                r, w, e = rpoll.select([], [sock_fd], [], sock_timeout)
                ready = w
            else:
                r, w, e = rpoll.select([sock_fd], [], [], sock_timeout)
                ready = r
        except rpoll.SelectError as e:
            message = e.get_msg()
            raise ssl_error(space, message, e.errno)
    if ready:
        return SOCKET_OPERATION_OK
    else:
        return SOCKET_HAS_TIMED_OUT


def _ssl_seterror(space, ss, ret):
    assert ret <= 0

    errcode = libssl_ERR_peek_last_error()

    if ss is None:
        return ssl_error(space, None, errcode=errcode)
    elif ss.ssl:
        err = libssl_SSL_get_error(ss.ssl, ret)
    else:
        err = SSL_ERROR_SSL
    w_errtype = None
    errstr = ""
    errval = 0

    if err == SSL_ERROR_ZERO_RETURN:
        w_errtype = get_error(space).w_ZeroReturnError
        errstr = "TLS/SSL connection has been closed"
        errval = PY_SSL_ERROR_ZERO_RETURN
    elif err == SSL_ERROR_WANT_READ:
        w_errtype = get_error(space).w_WantReadError
        errstr = "The operation did not complete (read)"
        errval = PY_SSL_ERROR_WANT_READ
    elif err == SSL_ERROR_WANT_WRITE:
        w_errtype = get_error(space).w_WantWriteError
        errstr = "The operation did not complete (write)"
        errval = PY_SSL_ERROR_WANT_WRITE
    elif err == SSL_ERROR_WANT_X509_LOOKUP:
        errstr = "The operation did not complete (X509 lookup)"
        errval = PY_SSL_ERROR_WANT_X509_LOOKUP
    elif err == SSL_ERROR_WANT_CONNECT:
        errstr = "The operation did not complete (connect)"
        errval = PY_SSL_ERROR_WANT_CONNECT
    elif err == SSL_ERROR_SYSCALL:
        e = libssl_ERR_get_error()
        if e == 0:
            if ret == 0 or ss.w_socket() is None:
                w_errtype = get_error(space).w_EOFError
                errstr = "EOF occurred in violation of protocol"
                errval = PY_SSL_ERROR_EOF
            elif ret == -1:
                # the underlying BIO reported an I/0 error
                error = rsocket.last_error()
                return interp_socket.converted_error(space, error)
            else:
                w_errtype = get_error(space).w_SyscallError
                errstr = "Some I/O error occurred"
                errval = PY_SSL_ERROR_SYSCALL
        else:
            errstr = rffi.charp2str(libssl_ERR_error_string(e, None))
            errval = PY_SSL_ERROR_SYSCALL
    elif err == SSL_ERROR_SSL:
        errval = PY_SSL_ERROR_SSL
        if errcode != 0:
            errstr = rffi.charp2str(libssl_ERR_error_string(errcode, None))
        else:
            errstr = "A failure in the SSL library occurred"
    else:
        errstr = "Invalid error code"
        errval = PY_SSL_ERROR_INVALID_ERROR_CODE

    return ssl_error(space, errstr, errval, w_errtype=w_errtype,
                     errcode=errcode)

def SSLError_descr_str(space, w_exc):
    w_strerror = space.getattr(w_exc, space.wrap("strerror"))
    if not space.is_none(w_strerror):
        return w_strerror
    return space.str(space.getattr(w_exc, space.wrap("args")))


class ErrorCache:
    def __init__(self, space):
        w_socketerror = interp_socket.get_error(space, "error")
        self.w_error = space.new_exception_class(
            "_ssl.SSLError", w_socketerror)
        space.setattr(self.w_error, space.wrap('__str__'),
                      space.wrap(interp2app(SSLError_descr_str)))
        self.w_ZeroReturnError = space.new_exception_class(
            "ssl.SSLZeroReturnError", self.w_error)
        self.w_WantReadError = space.new_exception_class(
            "ssl.SSLWantReadError", self.w_error)
        self.w_WantWriteError = space.new_exception_class(
            "ssl.SSLWantWriteError", self.w_error)
        self.w_EOFError = space.new_exception_class(
            "ssl.SSLEOFError", self.w_error)
        self.w_SyscallError = space.new_exception_class(
            "ssl.SSLSyscallError", self.w_error)

def get_error(space):
    return space.fromcache(ErrorCache)


@unwrap_spec(filename=str)
def _test_decode_cert(space, filename):
    cert = libssl_BIO_new(libssl_BIO_s_file())
    if not cert:
        raise ssl_error(space, "Can't malloc memory to read file")

    try:
        if libssl_BIO_read_filename(cert, filename) <= 0:
            raise ssl_error(space, "Can't open file")

        x = libssl_PEM_read_bio_X509_AUX(cert, None, None, None)
        if not x:
            raise ssl_error(space, "Error decoding PEM-encoded file")

        try:
            return _decode_certificate(space, x)
        finally:
            libssl_X509_free(x)
    finally:
        libssl_BIO_free(cert)


# Data structure for the password callbacks
class PasswordInfo(object):
    w_callable = None
    password = None
    operationerror = None
PWINFO_STORAGE = {}

def _password_callback(buf, size, rwflag, userdata):
    index = rffi.cast(lltype.Signed, userdata)
    pw_info = PWINFO_STORAGE.get(index, None)
    if not pw_info:
        return rffi.cast(rffi.INT, -1)
    space = pw_info.space
    password = ""
    if pw_info.w_callable:
        try:
            w_result = space.call_function(pw_info.w_callable)
            if space.isinstance_w(w_result, space.w_unicode):
                password = space.str_w(w_result)
            else:
                try:
                    password = pw_info.space.bufferstr_w(w_result)
                except OperationError as e:
                    if not e.match(space, space.w_TypeError):
                        raise
                    raise oefmt(space.w_TypeError,
                                "password callback must return a string")
        except OperationError as e:
            pw_info.operationerror = e
            return rffi.cast(rffi.INT, -1)
    else:
        password = pw_info.password
    size = widen(size)
    if len(password) > size:
        pw_info.operationerror = oefmt(
            space.w_ValueError,
            "password cannot be longer than %d bytes", size)
        return rffi.cast(rffi.INT, -1)
    for i, c in enumerate(password):
        buf[i] = c
    return rffi.cast(rffi.INT, len(password))

class ServernameCallback(object):
    w_ctx = None
    space = None
SERVERNAME_CALLBACKS = RWeakValueDictionary(int, ServernameCallback)

def _servername_callback(ssl, ad, arg):
    struct = SERVERNAME_CALLBACKS.get(rffi.cast(lltype.Signed, arg))
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
    w_ssl_socket = w_ssl  # So far. Need to change in 3.3.
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


class SSLContext(W_Root):
    ctx = lltype.nullptr(SSL_CTX.TO)

    def __init__(self, space, protocol):
        if protocol == PY_SSL_VERSION_TLS1:
            method = libssl_TLSv1_method()
        elif protocol == PY_SSL_VERSION_SSL3 and not OPENSSL_NO_SSL3:
            method = libssl_SSLv3_method()
        elif protocol == PY_SSL_VERSION_SSL2 and not OPENSSL_NO_SSL2:
            method = libssl_SSLv2_method()
        elif protocol == PY_SSL_VERSION_SSL23:
            method = libssl_SSLv23_method()
        elif protocol == PY_SSL_VERSION_TLS1_1 and HAVE_TLSv1_2:
            method = libssl_TLSv1_1_method()
        elif protocol == PY_SSL_VERSION_TLS1_2 and HAVE_TLSv1_2:
            method = libssl_TLSv1_2_method()
        else:
            raise oefmt(space.w_ValueError, "invalid protocol version")
        self.ctx = libssl_SSL_CTX_new(method)
        if not self.ctx:
            raise ssl_error(space, "failed to allocate SSL context")

        rgc.add_memory_pressure(10 * 1024 * 1024)
        self.check_hostname = False
        self.register_finalizer(space)

        # Defaults
        libssl_SSL_CTX_set_verify(self.ctx, SSL_VERIFY_NONE, None)
        options = SSL_OP_ALL & ~SSL_OP_DONT_INSERT_EMPTY_FRAGMENTS
        if protocol != PY_SSL_VERSION_SSL2:
            options |= SSL_OP_NO_SSLv2
        libssl_SSL_CTX_set_options(self.ctx, options)
        libssl_SSL_CTX_set_session_id_context(self.ctx, "Python", len("Python"))

        if not OPENSSL_NO_ECDH:
            # Allow automatic ECDH curve selection (on
            # OpenSSL 1.0.2+), or use prime256v1 by default.
            # This is Apache mod_ssl's initialization
            # policy, so we should be safe.
            if libssl_SSL_CTX_set_ecdh_auto:
                libssl_SSL_CTX_set_ecdh_auto(self.ctx, 1)
            else:
                key = libssl_EC_KEY_new_by_curve_name(NID_X9_62_prime256v1)
                if not key:
                    raise _ssl_seterror(space, None, 0)
                try:
                    libssl_SSL_CTX_set_tmp_ecdh(self.ctx, key)
                finally:
                    libssl_EC_KEY_free(key)

    def _finalize_(self):
        ctx = self.ctx
        if ctx:
            self.ctx = lltype.nullptr(SSL_CTX.TO)
            libssl_SSL_CTX_free(ctx)

    @staticmethod
    @unwrap_spec(protocol=int)
    def descr_new(space, w_subtype, protocol=PY_SSL_VERSION_SSL23):
        self = space.allocate_instance(SSLContext, w_subtype)
        self.__init__(space, protocol)
        return space.wrap(self)

    @unwrap_spec(cipherlist=str)
    def set_ciphers_w(self, space, cipherlist):
        ret = libssl_SSL_CTX_set_cipher_list(self.ctx, cipherlist)
        if ret == 0:
            # Clearing the error queue is necessary on some OpenSSL
            # versions, otherwise the error will be reported again
            # when another SSL call is done.
            libssl_ERR_clear_error()
            raise ssl_error(space, "No cipher can be selected.")

    @unwrap_spec(server_side=int)
    def wrap_socket_w(self, space, w_sock, server_side,
                      w_server_hostname=None):
        assert w_sock is not None
        # server_hostname is either None (or absent), or to be encoded
        # using the idna encoding.
        if space.is_none(w_server_hostname):
            hostname = None
        else:
            hostname = space.bytes_w(
                space.call_method(w_server_hostname,
                                  "encode", space.wrap("idna")))

        if hostname and not HAS_SNI:
            raise oefmt(space.w_ValueError,
                        "server_hostname is not supported by your OpenSSL "
                        "library")

        return new_sslobject(space, self.ctx, w_sock, server_side, hostname)

    def session_stats_w(self, space):
        w_stats = space.newdict()
        for name, ssl_func in SSL_CTX_STATS:
            w_value = space.wrap(ssl_func(self.ctx))
            space.setitem_str(w_stats, name, w_value)
        return w_stats

    def descr_set_default_verify_paths(self, space):
        if not libssl_SSL_CTX_set_default_verify_paths(self.ctx):
            raise ssl_error(space, "")

    def descr_get_options(self, space):
        return space.newlong(libssl_SSL_CTX_get_options(self.ctx))

    def descr_set_options(self, space, w_new_opts):
        new_opts = space.int_w(w_new_opts)
        opts = libssl_SSL_CTX_get_options(self.ctx)
        clear = opts & ~new_opts
        set = ~opts & new_opts
        if clear:
            if HAVE_SSL_CTX_CLEAR_OPTIONS:
                libssl_SSL_CTX_clear_options(self.ctx, clear)
            else:
                raise oefmt(space.w_ValueError,
                            "can't clear options before OpenSSL 0.9.8m")
        if set:
            libssl_SSL_CTX_set_options(self.ctx, set)

    def descr_get_verify_mode(self, space):
        mode = libssl_SSL_CTX_get_verify_mode(self.ctx)
        if mode == SSL_VERIFY_NONE:
            return space.newlong(PY_SSL_CERT_NONE)
        elif mode == SSL_VERIFY_PEER:
            return space.newlong(PY_SSL_CERT_OPTIONAL)
        elif mode == SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT:
            return space.newlong(PY_SSL_CERT_REQUIRED)
        raise ssl_error(space, "invalid return value from SSL_CTX_get_verify_mode")

    def descr_set_verify_mode(self, space, w_mode):
        n = space.int_w(w_mode)
        if n == PY_SSL_CERT_NONE:
            mode = SSL_VERIFY_NONE
        elif n == PY_SSL_CERT_OPTIONAL:
            mode = SSL_VERIFY_PEER
        elif n == PY_SSL_CERT_REQUIRED:
            mode = SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT
        else:
            raise oefmt(space.w_ValueError,
                        "invalid value for verify_mode")
        if mode == SSL_VERIFY_NONE and self.check_hostname:
            raise oefmt(space.w_ValueError,
                        "Cannot set verify_mode to CERT_NONE when "
                        "check_hostname is enabled.")
        libssl_SSL_CTX_set_verify(self.ctx, mode, None)

    def descr_get_verify_flags(self, space):
        store = libssl_SSL_CTX_get_cert_store(self.ctx)
        flags = libssl_X509_VERIFY_PARAM_get_flags(store[0].c_param)
        return space.wrap(flags)

    def descr_set_verify_flags(self, space, w_obj):
        new_flags = space.int_w(w_obj)
        store = libssl_SSL_CTX_get_cert_store(self.ctx)
        flags = libssl_X509_VERIFY_PARAM_get_flags(store[0].c_param)
        flags_clear = flags & ~new_flags
        flags_set = ~flags & new_flags
        if flags_clear and not libssl_X509_VERIFY_PARAM_clear_flags(
                store[0].c_param, flags_clear):
            raise _ssl_seterror(space, None, 0)
        if flags_set and not libssl_X509_VERIFY_PARAM_set_flags(
                store[0].c_param, flags_set):
            raise _ssl_seterror(space, None, 0)

    def descr_get_check_hostname(self, space):
        return space.newbool(self.check_hostname)

    def descr_set_check_hostname(self, space, w_obj):
        check_hostname = space.is_true(w_obj)
        if check_hostname and libssl_SSL_CTX_get_verify_mode(self.ctx) == SSL_VERIFY_NONE:
            raise oefmt(space.w_ValueError,
                        "check_hostname needs a SSL context with either "
                        "CERT_OPTIONAL or CERT_REQUIRED")
        self.check_hostname = check_hostname

    def load_cert_chain_w(self, space, w_certfile, w_keyfile=None,
                          w_password=None):
        if space.is_none(w_certfile):
            certfile = None
        else:
            certfile = space.str_w(w_certfile)
        if space.is_none(w_keyfile):
            keyfile = certfile
        else:
            keyfile = space.str_w(w_keyfile)
        pw_info = PasswordInfo()
        pw_info.space = space
        index = -1
        if not space.is_none(w_password):
            index = rthread.get_ident()
            PWINFO_STORAGE[index] = pw_info

            if space.is_true(space.callable(w_password)):
                pw_info.w_callable = w_password
            else:
                if space.isinstance_w(w_password, space.w_unicode):
                    pw_info.password = space.str_w(w_password)
                else:
                    try:
                        pw_info.password = space.bufferstr_w(w_password)
                    except OperationError as e:
                        if not e.match(space, space.w_TypeError):
                            raise
                        raise oefmt(space.w_TypeError,
                                    "password should be a string or callable")

            libssl_SSL_CTX_set_default_passwd_cb(
                self.ctx, _password_callback)
            libssl_SSL_CTX_set_default_passwd_cb_userdata(
                self.ctx, rffi.cast(rffi.VOIDP, index))

        try:
            ret = libssl_SSL_CTX_use_certificate_chain_file(self.ctx, certfile)
            if ret != 1:
                if pw_info.operationerror:
                    libssl_ERR_clear_error()
                    raise pw_info.operationerror
                errno = get_saved_errno()
                if errno:
                    libssl_ERR_clear_error()
                    raise wrap_oserror(space, OSError(errno, ''),
                                       exception_name = 'w_IOError')
                else:
                    raise _ssl_seterror(space, None, -1)

            ret = libssl_SSL_CTX_use_PrivateKey_file(self.ctx, keyfile,
                                                     SSL_FILETYPE_PEM)
            if ret != 1:
                if pw_info.operationerror:
                    libssl_ERR_clear_error()
                    raise pw_info.operationerror
                errno = get_saved_errno()
                if errno:
                    libssl_ERR_clear_error()
                    raise wrap_oserror(space, OSError(errno, ''),
                                       exception_name = 'w_IOError')
                else:
                    raise _ssl_seterror(space, None, -1)

            ret = libssl_SSL_CTX_check_private_key(self.ctx)
            if ret != 1:
                raise _ssl_seterror(space, None, -1)
        finally:
            if index >= 0:
                del PWINFO_STORAGE[index]
            libssl_SSL_CTX_set_default_passwd_cb(
                self.ctx, lltype.nullptr(pem_password_cb.TO))
            libssl_SSL_CTX_set_default_passwd_cb_userdata(
                self.ctx, None)

    @unwrap_spec(filepath=str)
    def load_dh_params_w(self, space, filepath):
        bio = libssl_BIO_new_file(filepath, "r")
        if not bio:
            errno = get_saved_errno()
            libssl_ERR_clear_error()
            raise wrap_oserror(space, OSError(errno, ''),
                               exception_name = 'w_IOError')
        try:
            dh = libssl_PEM_read_bio_DHparams(bio, None, None, None)
        finally:
            libssl_BIO_free(bio)
        if not dh:
            errno = get_saved_errno()
            if errno != 0:
                libssl_ERR_clear_error()
                raise wrap_oserror(space, OSError(errno, ''))
            else:
                raise _ssl_seterror(space, None, 0)
        try:
            if libssl_SSL_CTX_set_tmp_dh(self.ctx, dh) == 0:
                raise _ssl_seterror(space, None, 0)
        finally:
            libssl_DH_free(dh)

    def load_verify_locations_w(self, space, w_cafile=None, w_capath=None,
                                w_cadata=None):
        if space.is_none(w_cafile):
            cafile = None
        else:
            cafile = space.str_w(w_cafile)
        if space.is_none(w_capath):
            capath = None
        else:
            capath = space.str_w(w_capath)
        if space.is_none(w_cadata):
            cadata = None
            ca_file_type = -1
        else:
            if not space.isinstance_w(w_cadata, space.w_unicode):
                ca_file_type = SSL_FILETYPE_ASN1
                cadata = space.bufferstr_w(w_cadata)
            else:
                ca_file_type = SSL_FILETYPE_PEM
                try:
                    cadata = space.unicode_w(w_cadata).encode('ascii')
                except UnicodeEncodeError:
                    raise oefmt(space.w_TypeError,
                                "cadata should be a ASCII string or a "
                                "bytes-like object")
        if cafile is None and capath is None and cadata is None:
            raise oefmt(space.w_TypeError,
                        "cafile and capath cannot be both omitted")
        # load from cadata
        if cadata is not None:
            with rffi.scoped_nonmovingbuffer(cadata) as buf:
                self._add_ca_certs(space, buf, len(cadata), ca_file_type)

        # load cafile or capath
        if cafile is not None or capath is not None:
            ret = libssl_SSL_CTX_load_verify_locations(
                self.ctx, cafile, capath)
            if ret != 1:
                errno = get_saved_errno()
                if errno:
                    libssl_ERR_clear_error()
                    raise wrap_oserror(space, OSError(errno, ''),
                                       exception_name = 'w_IOError')
                else:
                    raise _ssl_seterror(space, None, -1)

    def _add_ca_certs(self, space, data, size, ca_file_type):
        biobuf = libssl_BIO_new_mem_buf(data, size)
        if not biobuf:
            raise ssl_error(space, "Can't allocate buffer")
        try:
            store = libssl_SSL_CTX_get_cert_store(self.ctx)
            loaded = 0
            while True:
                if ca_file_type == SSL_FILETYPE_ASN1:
                    cert = libssl_d2i_X509_bio(
                        biobuf, None)
                else:
                    cert = libssl_PEM_read_bio_X509(
                        biobuf, None, None, None)
                if not cert:
                    break
                try:
                    r = libssl_X509_STORE_add_cert(store, cert)
                finally:
                    libssl_X509_free(cert)
                if not r:
                    err = libssl_ERR_peek_last_error()
                    if (libssl_ERR_GET_LIB(err) == ERR_LIB_X509 and
                        libssl_ERR_GET_REASON(err) ==
                        X509_R_CERT_ALREADY_IN_HASH_TABLE):
                        # cert already in hash table, not an error
                        libssl_ERR_clear_error()
                    else:
                        break
                loaded += 1

            err = libssl_ERR_peek_last_error()
            if (ca_file_type == SSL_FILETYPE_ASN1 and
                loaded > 0 and
                libssl_ERR_GET_LIB(err) == ERR_LIB_ASN1 and
                libssl_ERR_GET_REASON(err) == ASN1_R_HEADER_TOO_LONG):
                # EOF ASN1 file, not an error
                libssl_ERR_clear_error()
            elif (ca_file_type == SSL_FILETYPE_PEM and
                  loaded > 0 and
                  libssl_ERR_GET_LIB(err) == ERR_LIB_PEM and
                  libssl_ERR_GET_REASON(err) == PEM_R_NO_START_LINE):
                # EOF PEM file, not an error
                libssl_ERR_clear_error()
            else:
                raise _ssl_seterror(space, None, 0)
        finally:
            libssl_BIO_free(biobuf)

    def cert_store_stats_w(self, space):
        store = libssl_SSL_CTX_get_cert_store(self.ctx)
        x509 = 0
        x509_ca = 0
        crl = 0
        for i in range(libssl_sk_X509_OBJECT_num(store[0].c_objs)):
            obj = libssl_sk_X509_OBJECT_value(store[0].c_objs, i)
            if intmask(obj.c_type) == X509_LU_X509:
                x509 += 1
                if libssl_X509_check_ca(
                        libssl_pypy_X509_OBJECT_data_x509(obj)):
                    x509_ca += 1
            elif intmask(obj.c_type) == X509_LU_CRL:
                crl += 1
            else:
                # Ignore X509_LU_FAIL, X509_LU_RETRY, X509_LU_PKEY.
                # As far as I can tell they are internal states and never
                # stored in a cert store
                pass
        w_result = space.newdict()
        space.setitem(w_result,
                      space.wrap('x509'), space.wrap(x509))
        space.setitem(w_result,
                      space.wrap('x509_ca'), space.wrap(x509_ca))
        space.setitem(w_result,
                      space.wrap('crl'), space.wrap(crl))
        return w_result

    @unwrap_spec(protos='bufferstr')
    def set_npn_protocols_w(self, space, protos):
        if not HAS_NPN:
            raise oefmt(space.w_NotImplementedError,
                        "The NPN extension requires OpenSSL 1.0.1 or later.")

        self.npn_protocols = SSLNpnProtocols(self.ctx, protos)

    @unwrap_spec(protos='bufferstr')
    def set_alpn_protocols_w(self, space, protos):
        if not HAS_ALPN:
            raise oefmt(space.w_NotImplementedError,
                        "The ALPN extension requires OpenSSL 1.0.2 or later.")

        self.alpn_protocols = SSLAlpnProtocols(self.ctx, protos)

    def get_ca_certs_w(self, space, w_binary_form=None):
        if w_binary_form and space.is_true(w_binary_form):
            binary_mode = True
        else:
            binary_mode = False
        rlist = []
        store = libssl_SSL_CTX_get_cert_store(self.ctx)
        for i in range(libssl_sk_X509_OBJECT_num(store[0].c_objs)):
            obj = libssl_sk_X509_OBJECT_value(store[0].c_objs, i)
            if intmask(obj.c_type) != X509_LU_X509:
                # not a x509 cert
                continue
            # CA for any purpose
            cert = libssl_pypy_X509_OBJECT_data_x509(obj)
            if not libssl_X509_check_ca(cert):
                continue
            if binary_mode:
                rlist.append(_certificate_to_der(space, cert))
            else:
                rlist.append(_decode_certificate(space, cert))
        return space.newlist(rlist)

    @unwrap_spec(name=str)
    def set_ecdh_curve_w(self, space, name):
        nid = libssl_OBJ_sn2nid(name)
        if nid == 0:
            raise oefmt(space.w_ValueError,
                        "unknown elliptic curve name '%s'", name)
        key = libssl_EC_KEY_new_by_curve_name(nid)
        if not key:
            raise _ssl_seterror(space, None, 0)
        try:
            libssl_SSL_CTX_set_tmp_ecdh(self.ctx, key)
        finally:
            libssl_EC_KEY_free(key)

    def set_servername_callback_w(self, space, w_callback):
        if space.is_none(w_callback):
            libssl_SSL_CTX_set_tlsext_servername_callback(
                self.ctx, lltype.nullptr(servername_cb.TO))
            self.servername_callback = None
            return
        if not space.is_true(space.callable(w_callback)):
            raise oefmt(space.w_TypeError, "not a callable object")
        callback_struct = ServernameCallback()
        callback_struct.space = space
        callback_struct.w_ctx = self
        callback_struct.w_set_hostname = w_callback
        self.servername_callback = callback_struct
        index = compute_unique_id(self)
        SERVERNAME_CALLBACKS.set(index, callback_struct)
        libssl_SSL_CTX_set_tlsext_servername_callback(
            self.ctx, _servername_callback)
        libssl_SSL_CTX_set_tlsext_servername_arg(self.ctx,
                                                 rffi.cast(rffi.VOIDP, index))

SSLContext.typedef = TypeDef(
    "_ssl._SSLContext",
    __new__ = interp2app(SSLContext.descr_new),
    _wrap_socket = interp2app(SSLContext.wrap_socket_w),
    set_ciphers = interp2app(SSLContext.set_ciphers_w),
    load_cert_chain = interp2app(SSLContext.load_cert_chain_w),
    load_verify_locations = interp2app(SSLContext.load_verify_locations_w),
    session_stats = interp2app(SSLContext.session_stats_w),
    cert_store_stats=interp2app(SSLContext.cert_store_stats_w),
    load_dh_params=interp2app(SSLContext.load_dh_params_w),
    set_default_verify_paths=interp2app(SSLContext.descr_set_default_verify_paths),
    _set_npn_protocols=interp2app(SSLContext.set_npn_protocols_w),
    _set_alpn_protocols=interp2app(SSLContext.set_alpn_protocols_w),
    get_ca_certs=interp2app(SSLContext.get_ca_certs_w),
    set_ecdh_curve=interp2app(SSLContext.set_ecdh_curve_w),
    set_servername_callback=interp2app(SSLContext.set_servername_callback_w),

    options=GetSetProperty(SSLContext.descr_get_options,
                           SSLContext.descr_set_options),
    verify_mode=GetSetProperty(SSLContext.descr_get_verify_mode,
                               SSLContext.descr_set_verify_mode),
    verify_flags=GetSetProperty(SSLContext.descr_get_verify_flags,
                                SSLContext.descr_set_verify_flags),
    # XXX: For use by 3.4 ssl.py only
    #check_hostname=GetSetProperty(SSLContext.descr_get_check_hostname,
    #                              SSLContext.descr_set_check_hostname),
)


def _asn1obj2py(space, obj):
    nid = libssl_OBJ_obj2nid(obj)
    if nid == NID_undef:
        raise oefmt(space.w_ValueError, "Unknown object")
    with rffi.scoped_alloc_buffer(100) as buf:
        buflen = libssl_OBJ_obj2txt(buf.raw, 100, obj, 1)
        if buflen < 0:
            raise _ssl_seterror(space, None, 0)
        if buflen:
            w_buf = space.wrap(buf.str(buflen))
        else:
            w_buf = space.w_None
    w_sn = space.wrap(rffi.charp2str(libssl_OBJ_nid2sn(nid)))
    w_ln = space.wrap(rffi.charp2str(libssl_OBJ_nid2ln(nid)))
    return space.newtuple([space.wrap(nid), w_sn, w_ln, w_buf])


@unwrap_spec(txt=str, name=bool)
def txt2obj(space, txt, name=False):
    obj = libssl_OBJ_txt2obj(txt, not name)
    if not obj:
        raise oefmt(space.w_ValueError, "unknown object '%s'", txt)
    try:
        w_result = _asn1obj2py(space, obj)
    finally:
        libssl_ASN1_OBJECT_free(obj)
    return w_result


@unwrap_spec(nid=int)
def nid2obj(space, nid):
    if nid < NID_undef:
        raise oefmt(space.w_ValueError, "NID must be positive")
    obj = libssl_OBJ_nid2obj(nid)
    if not obj:
        raise oefmt(space.w_ValueError, "unknown NID %d", nid)
    try:
        w_result = _asn1obj2py(space, obj)
    finally:
        libssl_ASN1_OBJECT_free(obj)
    return w_result


def w_convert_path(space, path):
    if not path:
        return space.w_None
    else:
        return fsdecode(space, space.newbytes(rffi.charp2str(path)))

def get_default_verify_paths(space):
    return space.newtuple([
        w_convert_path(space, libssl_X509_get_default_cert_file_env()),
        w_convert_path(space, libssl_X509_get_default_cert_file()),
        w_convert_path(space, libssl_X509_get_default_cert_dir_env()),
        w_convert_path(space, libssl_X509_get_default_cert_dir()),
        ])

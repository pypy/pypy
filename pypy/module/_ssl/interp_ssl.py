from rpython.rlib import rpoll, rsocket
from rpython.rlib.rarithmetic import intmask, widen, r_uint
from rpython.rlib.ropenssl import *
from rpython.rlib.rposix import get_errno, set_errno
from rpython.rlib.rweakref import RWeakValueDictionary
from rpython.rlib.objectmodel import specialize
from rpython.rtyper.lltypesystem import lltype, rffi

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt, wrap_oserror
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.module._ssl.ssl_data import (
    LIBRARY_CODES_TO_NAMES, ERROR_CODES_TO_NAMES)
from pypy.module._socket import interp_socket


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
 PY_SSL_VERSION_SSL23, PY_SSL_VERSION_TLS1) = range(4)

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
constants["HAS_NPN"] = OPENSSL_NPN_NEGOTIATED

if not OPENSSL_NO_SSL2:
    constants["PROTOCOL_SSLv2"]  = PY_SSL_VERSION_SSL2
if not OPENSSL_NO_SSL3:
    constants["PROTOCOL_SSLv3"]  = PY_SSL_VERSION_SSL3
constants["PROTOCOL_SSLv23"] = PY_SSL_VERSION_SSL23
constants["PROTOCOL_TLSv1"]  = PY_SSL_VERSION_TLS1

constants["OP_ALL"] = SSL_OP_ALL &~SSL_OP_DONT_INSERT_EMPTY_FRAGMENTS
constants["OP_NO_SSLv2"] = SSL_OP_NO_SSLv2
constants["OP_NO_SSLv3"] = SSL_OP_NO_SSLv3
constants["OP_NO_TLSv1"] = SSL_OP_NO_TLSv1
constants["OP_NO_COMPRESSION"] = SSL_OP_NO_COMPRESSION
constants["HAS_SNI"] = HAS_SNI
constants["HAS_ECDH"] = True  # To break the test suite
constants["HAS_NPN"] = HAS_NPN
constants["HAS_TLS_UNIQUE"] = True  # To break the test suite

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

    w_exception_class = w_errtype or get_exception_class(space, 'w_sslerror')
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

class SSLNpnProtocols(object):

    def __init__(self, ctx, protos):
        self.protos = protos
        self.buf, self.pinned, self.is_raw = rffi.get_nonmovingbuffer(protos)
        NPN_STORAGE.set(r_uint(rffi.cast(rffi.UINT, self.buf)), self)

        # set both server and client callbacks, because the context
        # can be used to create both types of sockets
        libssl_SSL_CTX_set_next_protos_advertised_cb(
            ctx, self.advertiseNPN_cb, self.buf)
        libssl_SSL_CTX_set_next_proto_select_cb(
            ctx, self.selectNPN_cb, self.buf)

    def __del__(self):
        rffi.free_nonmovingbuffer(
            self.protos, self.buf, self.pinned, self.is_raw)    

    @staticmethod
    def advertiseNPN_cb(s, data_ptr, len_ptr, args):
        npn = NPN_STORAGE.get(r_uint(rffi.cast(rffi.UINT, args)))
        if npn and npn.protos:
            data_ptr[0] = npn.buf
            len_ptr[0] = rffi.cast(rffi.UINT, len(npn.protos))
        else:
            data_ptr[0] = lltype.nullptr(rffi.CCHARP.TO)
            len_ptr[0] = rffi.cast(rffi.UINT, 0)

        return rffi.cast(rffi.INT, SSL_TLSEXT_ERR_OK)

    @staticmethod
    def selectNPN_cb(s, out_ptr, outlen_ptr, server, server_len, args):
        npn = NPN_STORAGE.get(r_uint(rffi.cast(rffi.UINT, args)))
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

NPN_STORAGE = RWeakValueDictionary(r_uint, SSLNpnProtocols)


if HAVE_OPENSSL_RAND:
    # helper routines for seeding the SSL PRNG
    @unwrap_spec(string=str, entropy=float)
    def RAND_add(space, string, entropy):
        """RAND_add(string, entropy)


        Mix string into the OpenSSL PRNG state.  entropy (a float) is a lower
        bound on the entropy contained in string."""
        with rffi.scoped_str2charp(string) as buf:
            libssl_RAND_add(buf, len(string), entropy)

    def RAND_status(space):
        """RAND_status() -> 0 or 1

        Returns 1 if the OpenSSL PRNG has been seeded with enough data
        and 0 if not.  It is necessary to seed the PRNG with RAND_add()
        on some platforms before using the ssl() function."""

        res = libssl_RAND_status()
        return space.wrap(res)

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


class _SSLSocket(W_Root):
    @staticmethod
    def descr_new(space, sslctx, w_sock, socket_type, hostname, w_ssl_sock):
        self = _SSLSocket()

        self.space = space
        self.ctx = sslctx
        self.peer_cert = lltype.nullptr(X509.TO)
        self.shutdown_seen_zero = False
        self.handshake_done = False

        sock_fd = space.int_w(space.call_method(w_sock, "fileno"))
        self.ssl = libssl_SSL_new(sslctx.ctx)  # new ssl struct
        libssl_SSL_set_fd(self.ssl, sock_fd)  # set the socket for SSL
        # The ACCEPT_MOVING_WRITE_BUFFER flag is necessary because the address
        # of a str object may be changed by the garbage collector.
        libssl_SSL_set_mode(
            self.ssl, SSL_MODE_AUTO_RETRY | SSL_MODE_ACCEPT_MOVING_WRITE_BUFFER)

        # If the socket is in non-blocking mode or timeout mode, set the BIO
        # to non-blocking mode (blocking is the default)
        w_timeout = space.call_method(w_sock, "gettimeout")
        has_timeout = not space.is_none(w_timeout)
        if has_timeout:
            # Set both the read and write BIO's to non-blocking mode
            libssl_BIO_set_nbio(libssl_SSL_get_rbio(self.ssl), 1)
            libssl_BIO_set_nbio(libssl_SSL_get_wbio(self.ssl), 1)

        if socket_type == PY_SSL_CLIENT:
            libssl_SSL_set_connect_state(self.ssl)
        else:
            libssl_SSL_set_accept_state(self.ssl)

        self.socket_type = socket_type
        self.w_socket = w_sock
        self.w_ssl_sock = None
        return self

    def __del__(self):
        self.enqueue_for_destruction(self.space, _SSLSocket.destructor,
                                     '__del__() method of ')

    def destructor(self):
        assert isinstance(self, _SSLSocket)
        if self.peer_cert:
            libssl_X509_free(self.peer_cert)
        if self.ssl:
            libssl_SSL_free(self.ssl)

    @unwrap_spec(data='bufferstr')
    def write(self, space, data):
        """write(s) -> len

        Writes the string s into the SSL object.  Returns the number
        of bytes written."""
        self._refresh_nonblocking(space)

        sockstate = checkwait(space, self.w_socket, True)
        if sockstate == SOCKET_HAS_TIMED_OUT:
            raise ssl_error(space, "The write operation timed out")
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
                sockstate = checkwait(space, self.w_socket, False)
            elif err == SSL_ERROR_WANT_WRITE:
                sockstate = checkwait(space, self.w_socket, True)
            else:
                sockstate = SOCKET_OPERATION_OK

            if sockstate == SOCKET_HAS_TIMED_OUT:
                raise ssl_error(space, "The write operation timed out")
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
    def read(self, space, num_bytes):
        """read([len]) -> string

        Read up to len bytes from the SSL socket."""
        count = libssl_SSL_pending(self.ssl)
        if not count:
            sockstate = checkwait(space, self.w_socket, False)
            if sockstate == SOCKET_HAS_TIMED_OUT:
                raise ssl_error(space, "The read operation timed out")
            elif sockstate == SOCKET_TOO_LARGE_FOR_SELECT:
                raise ssl_error(space,
                                "Underlying socket too large for select().")
            elif sockstate == SOCKET_HAS_BEEN_CLOSED:
                if libssl_SSL_get_shutdown(self.ssl) == SSL_RECEIVED_SHUTDOWN:
                    return space.wrap('')
                raise ssl_error(space,
                                "Socket closed without SSL shutdown handshake")

        with rffi.scoped_alloc_buffer(num_bytes) as buf:
            while True:
                err = 0

                count = libssl_SSL_read(self.ssl, buf.raw, num_bytes)
                err = libssl_SSL_get_error(self.ssl, count)

                if err == SSL_ERROR_WANT_READ:
                    sockstate = checkwait(space, self.w_socket, False)
                elif err == SSL_ERROR_WANT_WRITE:
                    sockstate = checkwait(space, self.w_socket, True)
                elif (err == SSL_ERROR_ZERO_RETURN and
                        libssl_SSL_get_shutdown(self.ssl) == SSL_RECEIVED_SHUTDOWN):
                    return space.wrap("")
                else:
                    sockstate = SOCKET_OPERATION_OK

                if sockstate == SOCKET_HAS_TIMED_OUT:
                    raise ssl_error(space, "The read operation timed out")
                elif sockstate == SOCKET_IS_NONBLOCKING:
                    break

                if err == SSL_ERROR_WANT_READ or err == SSL_ERROR_WANT_WRITE:
                    continue
                else:
                    break

            if count <= 0:
                raise _ssl_seterror(space, self, count)

            result = buf.str(count)

        return space.wrap(result)

    def _refresh_nonblocking(self, space):
        # just in case the blocking state of the socket has been changed
        w_timeout = space.call_method(self.w_socket, "gettimeout")
        nonblocking = not space.is_w(w_timeout, space.w_None)
        libssl_BIO_set_nbio(libssl_SSL_get_rbio(self.ssl), nonblocking)
        libssl_BIO_set_nbio(libssl_SSL_get_wbio(self.ssl), nonblocking)

    def do_handshake(self, space):
        self._refresh_nonblocking(space)

        # Actually negotiate SSL connection
        # XXX If SSL_do_handshake() returns 0, it's also a failure.
        while True:
            ret = libssl_SSL_do_handshake(self.ssl)
            err = libssl_SSL_get_error(self.ssl, ret)
            # XXX PyErr_CheckSignals()
            if err == SSL_ERROR_WANT_READ:
                sockstate = checkwait(space, self.w_socket, False)
            elif err == SSL_ERROR_WANT_WRITE:
                sockstate = checkwait(space, self.w_socket, True)
            else:
                sockstate = SOCKET_OPERATION_OK
            if sockstate == SOCKET_HAS_TIMED_OUT:
                raise ssl_error(space, "The handshake operation timed out")
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
        # Guard against closed socket
        w_fileno = space.call_method(self.w_socket, "fileno")
        if space.int_w(w_fileno) < 0:
            raise ssl_error(space, "Underlying socket has been closed")

        self._refresh_nonblocking(space)

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
                sockstate = checkwait(space, self.w_socket, False)
            elif ssl_err == SSL_ERROR_WANT_WRITE:
                sockstate = checkwait(space, self.w_socket, True)
            else:
                break

            if sockstate == SOCKET_HAS_TIMED_OUT:
                if ssl_err == SSL_ERROR_WANT_READ:
                    raise ssl_error(space, "The read operation timed out")
                else:
                    raise ssl_error(space, "The write operation timed out")
            elif sockstate == SOCKET_TOO_LARGE_FOR_SELECT:
                raise ssl_error(space,
                                "Underlying socket too large for select().")
            elif sockstate != SOCKET_OPERATION_OK:
                # Retain the SSL error code
                break

        if ret < 0:
            raise _ssl_seterror(space, self, ret)

        return self.w_socket

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
            with lltype.scoped_alloc(rffi.CCHARPP.TO, 1) as buf_ptr:
                buf_ptr[0] = lltype.nullptr(rffi.CCHARP.TO)
                length = libssl_i2d_X509(self.peer_cert, buf_ptr)
                if length < 0:
                    raise _ssl_seterror(space, self, length)
                try:
                    # this is actually an immutable bytes sequence
                    return space.wrap(rffi.charpsize2str(buf_ptr[0], length))
                finally:
                    libssl_OPENSSL_free(buf_ptr[0])
        else:
            verification = libssl_SSL_CTX_get_verify_mode(
                libssl_SSL_get_SSL_CTX(self.ssl))
            if not verification & SSL_VERIFY_PEER:
                return space.newdict()
            else:
                return _decode_certificate(space, self.peer_cert)

    def selected_npn_protocol(self, space):
        with lltype.scoped_alloc(rffi.CCHARPP.TO, 1) as out_ptr:
            with lltype.scoped_alloc(rffi.UINTP.TO, 1) as len_ptr:
                libssl_SSL_get0_next_proto_negotiated(self.ssl,
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

_SSLSocket.typedef = TypeDef(
    "_ssl._SSLSocket",

    do_handshake=interp2app(_SSLSocket.do_handshake),
    write=interp2app(_SSLSocket.write),
    read=interp2app(_SSLSocket.read),
    pending=interp2app(_SSLSocket.pending),
    peer_certificate=interp2app(_SSLSocket.peer_certificate),
    cipher=interp2app(_SSLSocket.cipher),
    shutdown=interp2app(_SSLSocket.shutdown),
    selected_npn_protocol = interp2app(_SSLSocket.selected_npn_protocol),
    compression = interp2app(_SSLSocket.compression_w),
    version = interp2app(_SSLSocket.version_w),
)


def _decode_certificate(space, certificate, verbose=False):
    w_retval = space.newdict()

    w_peer = _create_tuple_for_X509_NAME(
        space, libssl_X509_get_subject_name(certificate))
    space.setitem(w_retval, space.wrap("subject"), w_peer)

    if verbose:
        w_issuer = _create_tuple_for_X509_NAME(
            space, libssl_X509_get_issuer_name(certificate))
        space.setitem(w_retval, space.wrap("issuer"), w_issuer)

        space.setitem(w_retval, space.wrap("version"),
                      space.wrap(libssl_X509_get_version(certificate)))

    biobuf = libssl_BIO_new(libssl_BIO_s_mem())
    try:

        if verbose:
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

            for j in range(libssl_sk_GENERAL_NAME_num(names)):
                # Get a rendering of each name in the set of names

                name = libssl_sk_GENERAL_NAME_value(names, j)
                gntype = intmask(name[0].c_type)
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
        w_value = space.wrap(rffi.charpsize2str(buf_ptr[0], length))
        w_value = space.call_method(w_value, "decode", space.wrap("utf-8"))

    return space.newtuple([w_name, w_value])


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
        except rpoll.PollError, e:
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

    if ss is None:
        errval = libssl_ERR_peek_last_error()
        return ssl_error(space, None, errcode=errval)
    elif ss.ssl:
        err = libssl_SSL_get_error(ss.ssl, ret)
    else:
        err = SSL_ERROR_SSL
    w_errtype = None
    errstr = ""
    errval = 0

    if err == SSL_ERROR_ZERO_RETURN:
        w_errtype = get_exception_class(space, 'w_sslzeroreturnerror')
        errstr = "TLS/SSL connection has been closed"
        errval = PY_SSL_ERROR_ZERO_RETURN
    elif err == SSL_ERROR_WANT_READ:
        w_errtype = get_exception_class(space, 'w_sslwantreaderror')
        errstr = "The operation did not complete (read)"
        errval = PY_SSL_ERROR_WANT_READ
    elif err == SSL_ERROR_WANT_WRITE:
        w_errtype = get_exception_class(space, 'w_sslwantwriteerror')
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
            if ret == 0 or space.is_w(ss.w_socket, space.w_None):
                errstr = "EOF occurred in violation of protocol"
                errval = PY_SSL_ERROR_EOF
            elif ret == -1:
                # the underlying BIO reported an I/0 error
                error = rsocket.last_error()
                return interp_socket.converted_error(space, error)
            else:
                w_errtype = get_exception_class(space, 'w_sslsyscallerror')
                errstr = "Some I/O error occurred"
                errval = PY_SSL_ERROR_SYSCALL
        else:
            errstr = rffi.charp2str(libssl_ERR_error_string(e, None))
            errval = PY_SSL_ERROR_SYSCALL
    elif err == SSL_ERROR_SSL:
        e = libssl_ERR_get_error()
        errval = PY_SSL_ERROR_SSL
        if e != 0:
            errstr = rffi.charp2str(libssl_ERR_error_string(e, None))
        else:
            errstr = "A failure in the SSL library occurred"
    else:
        errstr = "Invalid error code"
        errval = PY_SSL_ERROR_INVALID_ERROR_CODE

    return ssl_error(space, errstr, errval, w_errtype=w_errtype)

def SSLError_descr_str(space, w_exc):
    w_strerror = space.getattr(w_exc, space.wrap("strerror"))
    if not space.is_none(w_strerror):
        return w_strerror
    return space.str(space.getattr(w_exc, space.wrap("args")))


class Cache:
    def __init__(self, space):
        w_socketerror = interp_socket.get_error(space, "error")
        self.w_sslerror = space.new_exception_class(
            "_ssl.SSLError", w_socketerror)
        space.setattr(self.w_sslerror, space.wrap('__str__'),
                      space.wrap(interp2app(SSLError_descr_str)))
        self.w_sslzeroreturnerror = space.new_exception_class(
            "_ssl.SSLZeroReturnError", self.w_sslerror)
        self.w_sslwantreaderror = space.new_exception_class(
            "_ssl.SSLWantReadError", self.w_sslerror)
        self.w_sslwantwriteerror = space.new_exception_class(
            "_ssl.SSLWantWriteError", self.w_sslerror)
        self.w_sslsyscallerror = space.new_exception_class(
            "_ssl.SSLSyscallError", self.w_sslerror)
        self.w_ssleoferror = space.new_exception_class(
            "_ssl.SSLEOFError", self.w_sslerror)


@specialize.memo()
def get_exception_class(space, name):
    return getattr(space.fromcache(Cache), name)


@unwrap_spec(filename=str, verbose=bool)
def _test_decode_cert(space, filename, verbose=True):
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
            return _decode_certificate(space, x, verbose)
        finally:
            libssl_X509_free(x)
    finally:
        libssl_BIO_free(cert)


class _SSLContext(W_Root):
    @staticmethod
    @unwrap_spec(protocol=int)
    def descr_new(space, w_subtype, protocol):
        if protocol == PY_SSL_VERSION_TLS1:
            method = libssl_TLSv1_method()
        elif protocol == PY_SSL_VERSION_SSL3 and not OPENSSL_NO_SSL3:
            method = libssl_SSLv3_method()
        elif protocol == PY_SSL_VERSION_SSL2 and not OPENSSL_NO_SSL2:
            method = libssl_SSLv2_method()
        elif protocol == PY_SSL_VERSION_SSL23:
            method = libssl_SSLv23_method()
        else:
            raise ssl_error(space, "invalid protocol version")
        ctx = libssl_SSL_CTX_new(method)
        if not ctx:
            raise ssl_error(space, "failed to allocate SSL context")

        self = space.allocate_instance(_SSLContext, w_subtype)
        self.ctx = ctx
        self.check_hostname = False
        options = SSL_OP_ALL & ~SSL_OP_DONT_INSERT_EMPTY_FRAGMENTS
        if protocol != PY_SSL_VERSION_SSL2:
            options |= SSL_OP_NO_SSLv2
        libssl_SSL_CTX_set_options(ctx, options)
        return self

    @unwrap_spec(server_side=int)
    def descr_wrap_socket(self, space, w_sock, server_side, w_server_hostname=None, w_ssl_sock=None):
        return _SSLSocket.descr_new(space, self, w_sock, server_side, w_server_hostname, w_ssl_sock)

    @unwrap_spec(cipherlist=str)
    def descr_set_ciphers(self, space, cipherlist):
        ret = libssl_SSL_CTX_set_cipher_list(self.ctx, cipherlist)
        if ret == 0:
            libssl_ERR_clear_error()
            raise ssl_error(space, "No cipher can be selected.")

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

    def descr_get_check_hostname(self, space):
        return space.newbool(self.check_hostname)

    def descr_set_check_hostname(self, space, w_obj):
        check_hostname = space.is_true(w_obj)
        if check_hostname and libssl_SSL_CTX_get_verify_mode(self.ctx) == SSL_VERIFY_NONE:
            raise oefmt(space.w_ValueError,
                        "check_hostname needs a SSL context with either "
                        "CERT_OPTIONAL or CERT_REQUIRED")
        self.check_hostname = check_hostname

    def load_cert_chain_w(self, space, w_certfile, w_keyfile=None):
        if space.is_none(w_certfile):
            certfile = None
        else:
            certfile = space.str_w(w_certfile)
        if space.is_none(w_keyfile):
            keyfile = certfile
        else:
            keyfile = space.str_w(w_keyfile)

        set_errno(0)

        ret = libssl_SSL_CTX_use_certificate_chain_file(self.ctx, certfile)
        if ret != 1:
            errno = get_errno()
            if errno:
                libssl_ERR_clear_error()
                raise wrap_oserror(space, OSError(errno, ''),
                                   exception_name = 'w_IOError')
            else:
                raise _ssl_seterror(space, None, -1)

        ret = libssl_SSL_CTX_use_PrivateKey_file(self.ctx, keyfile,
                                                 SSL_FILETYPE_PEM)
        if ret != 1:
            errno = get_errno()
            if errno:
                libssl_ERR_clear_error()
                raise wrap_oserror(space, OSError(errno, ''),
                                   exception_name = 'w_IOError')
            else:
                raise _ssl_seterror(space, None, -1)

        ret = libssl_SSL_CTX_check_private_key(self.ctx)
        if ret != 1:
            raise _ssl_seterror(space, None, -1)

    @unwrap_spec(filepath=str)
    def load_dh_params_w(self, space, filepath):
        bio = libssl_BIO_new_file(filepath, "r")
        if not bio:
            libssl_ERR_clear_error()
            errno = get_errno()
            raise wrap_oserror(space, OSError(errno, ''))
        try:
            set_errno(0)
            dh = libssl_PEM_read_bio_DHparams(bio, None, None, None)
        finally:
            libssl_BIO_free(bio)
        if not dh:
            errno = get_errno()
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
            raise OperationError(space.w_TypeError, space.wrap(
                    "cafile and capath cannot be both omitted"))
        # load from cadata
        if cadata:
            biobuf = libssl_BIO_new_mem_buf(cadata, len(cadata))
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
                    libssl_ERR_clear_error
                else:
                    _ssl_seterror(space, None, 0)
            finally:
                libssl_BIO_free(biobuf)
            
        # load cafile or capath
        if cafile or capath:
            set_errno(0)
            ret = libssl_SSL_CTX_load_verify_locations(
                self.ctx, cafile, capath)
            if ret != 1:
                errno = get_errno()
                if errno:
                    libssl_ERR_clear_error()
                    raise wrap_oserror(space, OSError(errno, ''),
                                       exception_name = 'w_IOError')
                else:
                    raise _ssl_seterror(space, None, -1)

    def cert_store_stats_w(self, space):
        store = libssl_SSL_CTX_get_cert_store(self.ctx)
        counters = {'x509': 0, 'x509_ca': 0, 'crl': 0}
        for i in range(libssl_sk_X509_OBJECT_num(store[0].c_objs)):
            obj = libssl_sk_X509_OBJECT_value(store[0].c_objs, i)
            if intmask(obj.c_type) == X509_LU_X509:
                counters['x509'] += 1
                if libssl_pypy_X509_OBJECT_data_x509(obj):
                    counters['x509_ca'] += 1
            elif intmask(obj.c_type) == X509_LU_CRL:
                counters['crl'] += 1
            else:
                # Ignore X509_LU_FAIL, X509_LU_RETRY, X509_LU_PKEY.
                # As far as I can tell they are internal states and never
                # stored in a cert store
                pass
        w_result = space.newdict()
        space.setitem(w_result,
                      space.wrap('x509'), space.wrap(counters['x509']))
        space.setitem(w_result,
                      space.wrap('x509_ca'), space.wrap(counters['x509_ca']))
        space.setitem(w_result,
                      space.wrap('crl'), space.wrap(counters['crl']))
        return w_result

    @unwrap_spec(protos='bufferstr')
    def set_npn_protocols_w(self, space, protos):
        if not HAS_NPN:
            raise oefmt(space.w_NotImplementedError,
                        "The NPN extension requires OpenSSL 1.0.1 or later.")

        self.npn_protocols = SSLNpnProtocols(self.ctx, protos)


_SSLContext.typedef = TypeDef(
    "_ssl._SSLContext",
    __new__=interp2app(_SSLContext.descr_new),
    _wrap_socket=interp2app(_SSLContext.descr_wrap_socket),
    set_ciphers=interp2app(_SSLContext.descr_set_ciphers),
    cert_store_stats=interp2app(_SSLContext.cert_store_stats_w),
    load_cert_chain=interp2app(_SSLContext.load_cert_chain_w),
    load_dh_params=interp2app(_SSLContext.load_dh_params_w),
    load_verify_locations=interp2app(_SSLContext.load_verify_locations_w),
    set_default_verify_paths=interp2app(_SSLContext.descr_set_default_verify_paths),
    _set_npn_protocols=interp2app(_SSLContext.set_npn_protocols_w),

    options=GetSetProperty(_SSLContext.descr_get_options,
                           _SSLContext.descr_set_options),
    verify_mode=GetSetProperty(_SSLContext.descr_get_verify_mode,
                               _SSLContext.descr_set_verify_mode),
    check_hostname=GetSetProperty(_SSLContext.descr_get_check_hostname,
                                  _SSLContext.descr_set_check_hostname),
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
    obj = libssl_OBJ_txt2obj(txt, name)
    if not obj:
        raise oefmt(space.w_ValueError, "unknown object '%s'", txt)
    result = _asn1obj2py(space, obj)
    libssl_ASN1_OBJECT_free(obj)
    return result


@unwrap_spec(nid=int)
def nid2obj(space, nid):
    return space.newtuple([])

from pypy.rpython.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, unwrap_spec

from pypy.rlib import rpoll, rsocket
from pypy.rlib.ropenssl import *

from pypy.module._socket import interp_socket

import sys

## user defined constants
X509_NAME_MAXLEN = 256
## # these mirror ssl.h
PY_SSL_ERROR_NONE, PY_SSL_ERROR_SSL = 0, 1
PY_SSL_ERROR_WANT_READ, PY_SSL_ERROR_WANT_WRITE = 2, 3
PY_SSL_ERROR_WANT_X509_LOOKUP = 4
PY_SSL_ERROR_SYSCALL = 5 # look at error stack/return value/errno
PY_SSL_ERROR_ZERO_RETURN, PY_SSL_ERROR_WANT_CONNECT = 6, 7
# start of non ssl.h errorcodes
PY_SSL_ERROR_EOF = 8 # special case of SSL_ERROR_SYSCALL
PY_SSL_ERROR_INVALID_ERROR_CODE = 9

PY_SSL_CERT_NONE, PY_SSL_CERT_OPTIONAL, PY_SSL_CERT_REQUIRED = 0, 1, 2

PY_SSL_CLIENT, PY_SSL_SERVER = 0, 1

(PY_SSL_VERSION_SSL2, PY_SSL_VERSION_SSL3,
 PY_SSL_VERSION_SSL23, PY_SSL_VERSION_TLS1) = range(4)

SOCKET_IS_NONBLOCKING, SOCKET_IS_BLOCKING = 0, 1
SOCKET_HAS_TIMED_OUT, SOCKET_HAS_BEEN_CLOSED = 2, 3
SOCKET_TOO_LARGE_FOR_SELECT, SOCKET_OPERATION_OK = 4, 5

HAVE_RPOLL = True  # Even win32 has rpoll.poll

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

constants["PROTOCOL_SSLv2"]  = PY_SSL_VERSION_SSL2
constants["PROTOCOL_SSLv3"]  = PY_SSL_VERSION_SSL3
constants["PROTOCOL_SSLv23"] = PY_SSL_VERSION_SSL23
constants["PROTOCOL_TLSv1"]  = PY_SSL_VERSION_TLS1

constants["OPENSSL_VERSION_NUMBER"] = OPENSSL_VERSION_NUMBER
ver = OPENSSL_VERSION_NUMBER
ver, status = divmod(ver, 16)
ver, patch  = divmod(ver, 256)
ver, fix    = divmod(ver, 256)
ver, minor  = divmod(ver, 256)
ver, major  = divmod(ver, 256)
constants["OPENSSL_VERSION_INFO"] = (major, minor, fix, patch, status)
constants["OPENSSL_VERSION"] = SSLEAY_VERSION

def ssl_error(space, msg, errno=0):
    w_exception_class = get_error(space)
    if errno:
        w_exception = space.call_function(w_exception_class,
                                          space.wrap(errno), space.wrap(msg))
    else:
        w_exception = space.call_function(w_exception_class, space.wrap(msg))
    return OperationError(w_exception_class, w_exception)

if HAVE_OPENSSL_RAND:
    # helper routines for seeding the SSL PRNG
    @unwrap_spec(string=str, entropy=float)
    def RAND_add(space, string, entropy):
        """RAND_add(string, entropy)


        Mix string into the OpenSSL PRNG state.  entropy (a float) is a lower
        bound on the entropy contained in string."""

        buf = rffi.str2charp(string)
        try:
            libssl_RAND_add(buf, len(string), entropy)
        finally:
            rffi.free_charp(buf)

    def RAND_status(space):
        """RAND_status() -> 0 or 1

        Returns 1 if the OpenSSL PRNG has been seeded with enough data and 0 if not.
        It is necessary to seed the PRNG with RAND_add() on some platforms before
        using the ssl() function."""

        res = libssl_RAND_status()
        return space.wrap(res)

    @unwrap_spec(path=str)
    def RAND_egd(space, path):
        """RAND_egd(path) -> bytes

        Queries the entropy gather daemon (EGD) on socket path.  Returns number
        of bytes read.  Raises socket.sslerror if connection to EGD fails or
        if it does provide enough data to seed PRNG."""

        socket_path = rffi.str2charp(path)
        try:
            bytes = libssl_RAND_egd(socket_path)
        finally:
            rffi.free_charp(socket_path)
        if bytes == -1:
            msg = "EGD connection failed or EGD did not return"
            msg += " enough data to seed the PRNG"
            raise ssl_error(space, msg)
        return space.wrap(bytes)

class SSLObject(Wrappable):
    def __init__(self, space):
        self.space = space
        self.w_socket = None
        self.ctx = lltype.nullptr(SSL_CTX.TO)
        self.ssl = lltype.nullptr(SSL.TO)
        self.peer_cert = lltype.nullptr(X509.TO)
        self._server = lltype.malloc(rffi.CCHARP.TO, X509_NAME_MAXLEN, flavor='raw')
        self._server[0] = '\0'
        self._issuer = lltype.malloc(rffi.CCHARP.TO, X509_NAME_MAXLEN, flavor='raw')
        self._issuer[0] = '\0'
        self.shutdown_seen_zero = False
    
    def server(self):
        return self.space.wrap(rffi.charp2str(self._server))
    
    def issuer(self):
        return self.space.wrap(rffi.charp2str(self._issuer))
    
    def __del__(self):
        if self.peer_cert:
            libssl_X509_free(self.peer_cert)
        if self.ssl:
            libssl_SSL_free(self.ssl)
        if self.ctx:
            libssl_SSL_CTX_free(self.ctx)
        lltype.free(self._server, flavor='raw')
        lltype.free(self._issuer, flavor='raw')
    
    @unwrap_spec(data='bufferstr')
    def write(self, data):
        """write(s) -> len

        Writes the string s into the SSL object.  Returns the number
        of bytes written."""
        self._refresh_nonblocking(self.space)

        sockstate = check_socket_and_wait_for_timeout(self.space,
            self.w_socket, True)
        if sockstate == SOCKET_HAS_TIMED_OUT:
            raise ssl_error(self.space, "The write operation timed out")
        elif sockstate == SOCKET_HAS_BEEN_CLOSED:
            raise ssl_error(self.space, "Underlying socket has been closed.")
        elif sockstate == SOCKET_TOO_LARGE_FOR_SELECT:
            raise ssl_error(self.space, "Underlying socket too large for select().")

        num_bytes = 0
        while True:
            err = 0
            
            num_bytes = libssl_SSL_write(self.ssl, data, len(data))
            err = libssl_SSL_get_error(self.ssl, num_bytes)
        
            if err == SSL_ERROR_WANT_READ:
                sockstate = check_socket_and_wait_for_timeout(self.space,
                    self.w_socket, False)
            elif err == SSL_ERROR_WANT_WRITE:
                sockstate = check_socket_and_wait_for_timeout(self.space,
                    self.w_socket, True)
            else:
                sockstate = SOCKET_OPERATION_OK
        
            if sockstate == SOCKET_HAS_TIMED_OUT:
                raise ssl_error(self.space, "The write operation timed out")
            elif sockstate == SOCKET_HAS_BEEN_CLOSED:
                raise ssl_error(self.space, "Underlying socket has been closed.")
            elif sockstate == SOCKET_IS_NONBLOCKING:
                break
        
            if err == SSL_ERROR_WANT_READ or err == SSL_ERROR_WANT_WRITE:
                continue
            else:
                break
        
        if num_bytes > 0:
            return self.space.wrap(num_bytes)
        else:
            raise _ssl_seterror(self.space, self, num_bytes)

    def pending(self):
        """pending() -> count

        Returns the number of already decrypted bytes available for read,
        pending on the connection."""
        count = libssl_SSL_pending(self.ssl)
        if count < 0:
            raise _ssl_seterror(self.space, self, count)
        return self.space.wrap(count)

    @unwrap_spec(num_bytes=int)
    def read(self, num_bytes=1024):
        """read([len]) -> string

        Read up to len bytes from the SSL socket."""

        count = libssl_SSL_pending(self.ssl)
        if not count:
            sockstate = check_socket_and_wait_for_timeout(self.space,
                self.w_socket, False)
            if sockstate == SOCKET_HAS_TIMED_OUT:
                raise ssl_error(self.space, "The read operation timed out")
            elif sockstate == SOCKET_TOO_LARGE_FOR_SELECT:
                raise ssl_error(self.space, "Underlying socket too large for select().")
            elif sockstate == SOCKET_HAS_BEEN_CLOSED:
                if libssl_SSL_get_shutdown(self.ssl) == SSL_RECEIVED_SHUTDOWN:
                    return self.space.wrap('')
                raise ssl_error(self.space, "Socket closed without SSL shutdown handshake")

        raw_buf, gc_buf = rffi.alloc_buffer(num_bytes)
        while True:
            err = 0
            
            count = libssl_SSL_read(self.ssl, raw_buf, num_bytes)
            err = libssl_SSL_get_error(self.ssl, count)
        
            if err == SSL_ERROR_WANT_READ:
                sockstate = check_socket_and_wait_for_timeout(self.space,
                    self.w_socket, False)
            elif err == SSL_ERROR_WANT_WRITE:
                sockstate = check_socket_and_wait_for_timeout(self.space,
                    self.w_socket, True)
            elif (err == SSL_ERROR_ZERO_RETURN and
                  libssl_SSL_get_shutdown(self.ssl) == SSL_RECEIVED_SHUTDOWN):
                return self.space.wrap("")
            else:
                sockstate = SOCKET_OPERATION_OK
        
            if sockstate == SOCKET_HAS_TIMED_OUT:
                raise ssl_error(self.space, "The read operation timed out")
            elif sockstate == SOCKET_IS_NONBLOCKING:
                break
        
            if err == SSL_ERROR_WANT_READ or err == SSL_ERROR_WANT_WRITE:
                continue
            else:
                break
                
        if count <= 0:
            raise _ssl_seterror(self.space, self, count)

        result = rffi.str_from_buffer(raw_buf, gc_buf, num_bytes, count)
        rffi.keep_buffer_alive_until_here(raw_buf, gc_buf)
        return self.space.wrap(result)

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
                sockstate = check_socket_and_wait_for_timeout(
                    space, self.w_socket, False)
            elif err == SSL_ERROR_WANT_WRITE:
                sockstate = check_socket_and_wait_for_timeout(
                    space, self.w_socket, True)
            else:
                sockstate = SOCKET_OPERATION_OK
            if sockstate == SOCKET_HAS_TIMED_OUT:
                raise ssl_error(space, "The handshake operation timed out")
            elif sockstate == SOCKET_HAS_BEEN_CLOSED:
                raise ssl_error(space, "Underlying socket has been closed.")
            elif sockstate == SOCKET_TOO_LARGE_FOR_SELECT:
                raise ssl_error(space, "Underlying socket too large for select().")
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
        if self.peer_cert:
            libssl_X509_NAME_oneline(
                libssl_X509_get_subject_name(self.peer_cert),
                self._server, X509_NAME_MAXLEN)
            libssl_X509_NAME_oneline(
                libssl_X509_get_issuer_name(self.peer_cert),
                self._issuer, X509_NAME_MAXLEN)

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
                sockstate = check_socket_and_wait_for_timeout(
                    self.space, self.w_socket, False)
            elif ssl_err == SSL_ERROR_WANT_WRITE:
                sockstate = check_socket_and_wait_for_timeout(
                    self.space, self.w_socket, True)
            else:
                break

            if sockstate == SOCKET_HAS_TIMED_OUT:
                if ssl_err == SSL_ERROR_WANT_READ:
                    raise ssl_error(self.space, "The read operation timed out")
                else:
                    raise ssl_error(self.space, "The write operation timed out")
            elif sockstate == SOCKET_TOO_LARGE_FOR_SELECT:
                raise ssl_error(space, "Underlying socket too large for select().")
            elif sockstate != SOCKET_OPERATION_OK:
                # Retain the SSL error code
                break

        if ret < 0:
            raise _ssl_seterror(space, self, ret)

        return self.w_socket


SSLObject.typedef = TypeDef("SSLObject",
    server = interp2app(SSLObject.server),
    issuer = interp2app(SSLObject.issuer),
    write = interp2app(SSLObject.write),
    pending = interp2app(SSLObject.pending),
    read = interp2app(SSLObject.read),
    do_handshake=interp2app(SSLObject.do_handshake),
    shutdown=interp2app(SSLObject.shutdown),
)


def new_sslobject(space, w_sock, side, w_key_file, w_cert_file):
    ss = SSLObject(space)

    sock_fd = space.int_w(space.call_method(w_sock, "fileno"))
    w_timeout = space.call_method(w_sock, "gettimeout")
    if space.is_w(w_timeout, space.w_None):
        has_timeout = False
    else:
        has_timeout = True
    if space.is_w(w_key_file, space.w_None):
        key_file = None
    else:
        key_file = space.str_w(w_key_file)
    if space.is_w(w_cert_file, space.w_None):
        cert_file = None
    else:
        cert_file = space.str_w(w_cert_file)

    if side == PY_SSL_SERVER and (not key_file or not cert_file):
        raise ssl_error(space, "Both the key & certificate files "
                        "must be specified for server-side operation")

    ss.ctx = libssl_SSL_CTX_new(libssl_SSLv23_method()) # set up context
    if not ss.ctx:
        raise ssl_error(space, "Invalid SSL protocol variant specified")

    # XXX SSL_CTX_set_cipher_list?

    # XXX SSL_CTX_load_verify_locations?

    if key_file:
        ret = libssl_SSL_CTX_use_PrivateKey_file(ss.ctx, key_file,
                                                 SSL_FILETYPE_PEM)
        if ret < 1:
            raise ssl_error(space, "SSL_CTX_use_PrivateKey_file error")

        ret = libssl_SSL_CTX_use_certificate_chain_file(ss.ctx, cert_file)
        if ret < 1:
            raise ssl_error(space, "SSL_CTX_use_certificate_chain_file error")

    # ssl compatibility
    libssl_SSL_CTX_set_options(ss.ctx, SSL_OP_ALL)

    libssl_SSL_CTX_set_verify(ss.ctx, SSL_VERIFY_NONE, None) # set verify level
    ss.ssl = libssl_SSL_new(ss.ctx) # new ssl struct
    libssl_SSL_set_fd(ss.ssl, sock_fd) # set the socket for SSL
    libssl_SSL_set_mode(ss.ssl, SSL_MODE_AUTO_RETRY)

    # If the socket is in non-blocking mode or timeout mode, set the BIO
    # to non-blocking mode (blocking is the default)
    if has_timeout:
        # Set both the read and write BIO's to non-blocking mode
        libssl_BIO_ctrl(libssl_SSL_get_rbio(ss.ssl), BIO_C_SET_NBIO, 1, None)
        libssl_BIO_ctrl(libssl_SSL_get_wbio(ss.ssl), BIO_C_SET_NBIO, 1, None)
    libssl_SSL_set_connect_state(ss.ssl)

    if side == PY_SSL_CLIENT:
        libssl_SSL_set_connect_state(ss.ssl)
    else:
        libssl_SSL_set_accept_state(ss.ssl)

    ss.w_socket = w_sock
    return ss

def check_socket_and_wait_for_timeout(space, w_sock, writing):
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
        ready = rpoll.poll(fddict, timeout)
    else:
        if MAX_FD_SIZE is not None and sock_fd >= MAX_FD_SIZE:
            return SOCKET_TOO_LARGE_FOR_SELECT

        if writing:
            r, w, e = rpoll.select([], [sock_fd], [], sock_timeout)
            ready = w
        else:
            r, w, e = rpoll.select([sock_fd], [], [], sock_timeout)
            ready = r
    if ready:
        return SOCKET_OPERATION_OK
    else:
        return SOCKET_HAS_TIMED_OUT

def _ssl_seterror(space, ss, ret):
    assert ret <= 0

    err = libssl_SSL_get_error(ss.ssl, ret)
    errstr = ""
    errval = 0

    if err == SSL_ERROR_ZERO_RETURN:
        errstr = "TLS/SSL connection has been closed"
        errval = PY_SSL_ERROR_ZERO_RETURN
    elif err == SSL_ERROR_WANT_READ:
        errstr = "The operation did not complete (read)"
        errval = PY_SSL_ERROR_WANT_READ
    elif err == SSL_ERROR_WANT_WRITE:
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

    return ssl_error(space, errstr, errval)


@unwrap_spec(side=int, cert_mode=int, protocol=int)
def sslwrap(space, w_socket, side, w_key_file=None, w_cert_file=None,
            cert_mode=PY_SSL_CERT_NONE, protocol=PY_SSL_VERSION_SSL23,
            w_cacerts_file=None, w_cipher=None):
    """sslwrap(socket, side, [keyfile, certfile]) -> sslobject"""
    return space.wrap(new_sslobject(
        space, w_socket, side, w_key_file, w_cert_file))

class Cache:
    def __init__(self, space):
        w_socketerror = interp_socket.get_error(space, "error")
        self.w_error = space.new_exception_class(
            "_ssl.SSLError", w_socketerror)

def get_error(space):
    return space.fromcache(Cache).w_error

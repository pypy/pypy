from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.rctypes.tool.libc import libc
import pypy.rpython.rctypes.implementation # this defines rctypes magic
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app
from ctypes import *
import ctypes.util
import sys
import socket
import select

from ssl import SSL_CTX, SSL, X509, SSL_METHOD, X509_NAME
from bio import BIO

c_void = None
libssl = cdll.LoadLibrary(ctypes.util.find_library("ssl"))

## user defined constants
X509_NAME_MAXLEN = 256
# these mirror ssl.h
PY_SSL_ERROR_NONE, PY_SSL_ERROR_SSL = 0, 1
PY_SSL_ERROR_WANT_READ, PY_SSL_ERROR_WANT_WRITE = 2, 3
PY_SSL_ERROR_WANT_X509_LOOKUP = 4
PY_SSL_ERROR_SYSCALL = 5 # look at error stack/return value/errno
PY_SSL_ERROR_ZERO_RETURN, PY_SSL_ERROR_WANT_CONNECT = 6, 7
# start of non ssl.h errorcodes
PY_SSL_ERROR_EOF = 8 # special case of SSL_ERROR_SYSCALL
PY_SSL_ERROR_INVALID_ERROR_CODE = 9

SOCKET_IS_NONBLOCKING, SOCKET_IS_BLOCKING = 0, 1
SOCKET_HAS_TIMED_OUT, SOCKET_HAS_BEEN_CLOSED = 2, 3
SOCKET_TOO_LARGE_FOR_SELECT, SOCKET_OPERATION_OK = 4, 5


class CConfig:
    _header_ = """
    #include <openssl/ssl.h>
    #include <openssl/opensslv.h>
    #include <openssl/bio.h>
    #include <sys/types.h>
    #include <sys/time.h>
    #include <sys/poll.h>
    """
    OPENSSL_VERSION_NUMBER = ctypes_platform.ConstantInteger(
        "OPENSSL_VERSION_NUMBER")
    SSL_FILETYPE_PEM = ctypes_platform.ConstantInteger("SSL_FILETYPE_PEM")
    SSL_OP_ALL = ctypes_platform.ConstantInteger("SSL_OP_ALL")
    SSL_VERIFY_NONE = ctypes_platform.ConstantInteger("SSL_VERIFY_NONE")
    SSL_ERROR_WANT_READ = ctypes_platform.ConstantInteger(
        "SSL_ERROR_WANT_READ")
    SSL_ERROR_WANT_WRITE = ctypes_platform.ConstantInteger(
        "SSL_ERROR_WANT_WRITE")
    SSL_ERROR_ZERO_RETURN = ctypes_platform.ConstantInteger(
        "SSL_ERROR_ZERO_RETURN")
    SSL_ERROR_WANT_X509_LOOKUP = ctypes_platform.ConstantInteger(
        "SSL_ERROR_WANT_X509_LOOKUP")
    SSL_ERROR_WANT_CONNECT = ctypes_platform.ConstantInteger(
        "SSL_ERROR_WANT_CONNECT")
    SSL_ERROR_SYSCALL = ctypes_platform.ConstantInteger("SSL_ERROR_SYSCALL")
    SSL_ERROR_SSL = ctypes_platform.ConstantInteger("SSL_ERROR_SSL")
    FD_SETSIZE = ctypes_platform.ConstantInteger("FD_SETSIZE")
    SSL_CTRL_OPTIONS = ctypes_platform.ConstantInteger("SSL_CTRL_OPTIONS")
    BIO_C_SET_NBIO = ctypes_platform.ConstantInteger("BIO_C_SET_NBIO")
    pollfd = ctypes_platform.Struct("struct pollfd",
        [("fd", c_int), ("events", c_short), ("revents", c_short)])
    nfds_t = ctypes_platform.SimpleType("nfds_t", c_uint)
    POLLOUT = ctypes_platform.ConstantInteger("POLLOUT")
    POLLIN = ctypes_platform.ConstantInteger("POLLIN")

class cConfig:
    pass

cConfig.__dict__.update(ctypes_platform.configure(CConfig))

OPENSSL_VERSION_NUMBER = cConfig.OPENSSL_VERSION_NUMBER
HAVE_OPENSSL_RAND = OPENSSL_VERSION_NUMBER >= 0x0090500fL
SSL_FILETYPE_PEM = cConfig.SSL_FILETYPE_PEM
SSL_OP_ALL = cConfig.SSL_OP_ALL
SSL_VERIFY_NONE = cConfig.SSL_VERIFY_NONE
SSL_ERROR_WANT_READ = cConfig.SSL_ERROR_WANT_READ
SSL_ERROR_WANT_WRITE = cConfig.SSL_ERROR_WANT_WRITE
SSL_ERROR_ZERO_RETURN = cConfig.SSL_ERROR_ZERO_RETURN
SSL_ERROR_WANT_X509_LOOKUP = cConfig.SSL_ERROR_WANT_X509_LOOKUP
SSL_ERROR_WANT_CONNECT = cConfig.SSL_ERROR_WANT_CONNECT
SSL_ERROR_SYSCALL = cConfig.SSL_ERROR_SYSCALL
SSL_ERROR_SSL = cConfig.SSL_ERROR_SSL
FD_SETSIZE = cConfig.FD_SETSIZE
SSL_CTRL_OPTIONS = cConfig.SSL_CTRL_OPTIONS
BIO_C_SET_NBIO = cConfig.BIO_C_SET_NBIO
POLLOUT = cConfig.POLLOUT
POLLIN = cConfig.POLLIN

pollfd = cConfig.pollfd
nfds_t = cConfig.nfds_t

arr_x509 = c_char * X509_NAME_MAXLEN

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

libssl.SSL_load_error_strings.restype = c_void
libssl.SSL_library_init.restype = c_int
if HAVE_OPENSSL_RAND:
    libssl.RAND_add.argtypes = [c_char_p, c_int, c_double]
    libssl.RAND_add.restype = c_void
    libssl.RAND_status.restype = c_int
    libssl.RAND_egd.argtypes = [c_char_p]
    libssl.RAND_egd.restype = c_int
libssl.SSL_CTX_new.argtypes = [POINTER(SSL_METHOD)]
libssl.SSL_CTX_new.restype = POINTER(SSL_CTX)
libssl.SSLv23_method.restype = POINTER(SSL_METHOD)
libssl.SSL_CTX_use_PrivateKey_file.argtypes = [POINTER(SSL_CTX), c_char_p, c_int]
libssl.SSL_CTX_use_PrivateKey_file.restype = c_int
libssl.SSL_CTX_use_certificate_chain_file.argtypes = [POINTER(SSL_CTX), c_char_p]
libssl.SSL_CTX_use_certificate_chain_file.restype = c_int
libssl.SSL_CTX_ctrl.argtypes = [POINTER(SSL_CTX), c_int, c_int, c_void_p]
libssl.SSL_CTX_ctrl.restype = c_int
libssl.SSL_CTX_set_verify.argtypes = [POINTER(SSL_CTX), c_int, c_void_p]
libssl.SSL_CTX_set_verify.restype = c_void
libssl.SSL_new.argtypes = [POINTER(SSL_CTX)]
libssl.SSL_new.restype = POINTER(SSL)
libssl.SSL_set_fd.argtypes = [POINTER(SSL), c_int]
libssl.SSL_set_fd.restype = c_int
libssl.BIO_ctrl.argtypes = [POINTER(BIO), c_int, c_int, c_void_p]
libssl.BIO_ctrl.restype = c_int
libssl.SSL_get_rbio.argtypes = [POINTER(SSL)]
libssl.SSL_get_rbio.restype = POINTER(BIO)
libssl.SSL_get_wbio.argtypes = [POINTER(SSL)]
libssl.SSL_get_wbio.restype = POINTER(BIO)
libssl.SSL_set_connect_state.argtypes = [POINTER(SSL)]
libssl.SSL_set_connect_state.restype = c_void
libssl.SSL_connect.argtypes = [POINTER(SSL)]
libssl.SSL_connect.restype = c_int
libssl.SSL_get_error.argtypes = [POINTER(SSL), c_int]
libssl.SSL_get_error.restype = c_int
have_poll = False
if hasattr(libc, "poll"):
    have_poll = True
    libc.poll.argtypes = [POINTER(pollfd), nfds_t, c_int]
    libc.poll.restype = c_int
libssl.ERR_get_error.restype = c_int
libssl.ERR_error_string.argtypes = [c_int, c_char_p]
libssl.ERR_error_string.restype = c_char_p
libssl.SSL_get_peer_certificate.argtypes = [POINTER(SSL)]
libssl.SSL_get_peer_certificate.restype = POINTER(X509)
libssl.X509_get_subject_name.argtypes = [POINTER(X509)]
libssl.X509_get_subject_name.restype = POINTER(X509_NAME)
libssl.X509_get_issuer_name.argtypes = [POINTER(X509)]
libssl.X509_get_issuer_name.restype = POINTER(X509_NAME)
libssl.X509_NAME_oneline.argtypes = [POINTER(X509_NAME), arr_x509, c_int]
libssl.X509_NAME_oneline.restype = c_char_p
libssl.X509_free.argtypes = [POINTER(X509)]
libssl.X509_free.restype = c_void
libssl.SSL_free.argtypes = [POINTER(SSL)]
libssl.SSL_free.restype = c_void
libssl.SSL_CTX_free.argtypes = [POINTER(SSL_CTX)]
libssl.SSL_CTX_free.restype = c_void
libssl.SSL_write.argtypes = [POINTER(SSL), c_char_p, c_int]
libssl.SSL_write.restype = c_int
libssl.SSL_pending.argtypes = [POINTER(SSL)]
libssl.SSL_pending.restype = c_int
libssl.SSL_read.argtypes = [POINTER(SSL), c_char_p, c_int]
libssl.SSL_read.restype = c_int

def _init_ssl():
    libssl.SSL_load_error_strings()
    libssl.SSL_library_init()

if HAVE_OPENSSL_RAND:
    # helper routines for seeding the SSL PRNG
    def RAND_add(space, string, entropy):
        """RAND_add(string, entropy)


        Mix string into the OpenSSL PRNG state.  entropy (a float) is a lower
        bound on the entropy contained in string."""

        buf = c_char_p(string)

        libssl.RAND_add(buf, len(string), entropy)
    RAND_add.unwrap_spec = [ObjSpace, str, float]

    def RAND_status(space):
        """RAND_status() -> 0 or 1

        Returns 1 if the OpenSSL PRNG has been seeded with enough data and 0 if not.
        It is necessary to seed the PRNG with RAND_add() on some platforms before
        using the ssl() function."""

        res = libssl.RAND_status()
        return space.wrap(res)
    RAND_status.unwrap_spec = [ObjSpace]

    def RAND_egd(space, path):
        """RAND_egd(path) -> bytes

        Queries the entropy gather daemon (EGD) on socket path.  Returns number
        of bytes read.  Raises socket.sslerror if connection to EGD fails or
        if it does provide enough data to seed PRNG."""

        socket_path = c_char_p(path)
        bytes = libssl.RAND_egd(socket_path)
        if bytes == -1:
            msg = "EGD connection failed or EGD did not return"
            msg += " enough data to seed the PRNG"
            raise OperationError(space.w_Exception, space.wrap(msg))
        return space.wrap(bytes)
    RAND_egd.unwrap_spec = [ObjSpace, str]

class SSLObject(Wrappable):
    def __init__(self, space):
        self.space = space
        self.w_socket = None
        self.ctx = POINTER(SSL_CTX)()
        self.ssl = POINTER(SSL)()
        self.server_cert = POINTER(X509)()
        self._server = arr_x509()
        self._issuer = arr_x509()
    
    def server(self):
        return self.space.wrap(self._server.value)
    server.unwrap_spec = ['self']
    
    def issuer(self):
        return self.space.wrap(self._issuer.value)
    issuer.unwrap_spec = ['self']
    
    def __del__(self):
        if self.server_cert:
            libssl.X509_free(self.server_cert)
        if self.ssl:
            libssl.SSL_free(self.ssl)
        if self.ctx:
            libssl.SSL_CTX_free(self.ctx)
    
    def write(self, data):
        """write(s) -> len

        Writes the string s into the SSL object.  Returns the number
        of bytes written."""
        
        sockstate = check_socket_and_wait_for_timeout(self.space,
            self.w_socket, True)
        if sockstate == SOCKET_HAS_TIMED_OUT:
            raise OperationError(self.space.w_Exception,
                self.space.wrap("The write operation timed out"))
        elif sockstate == SOCKET_HAS_BEEN_CLOSED:
            raise OperationError(self.space.w_Exception,
                self.space.wrap("Underlying socket has been closed."))
        elif sockstate == SOCKET_TOO_LARGE_FOR_SELECT:
            raise OperationError(self.space.w_Exception,
                self.space.wrap("Underlying socket too large for select()."))

        num_bytes = 0
        while True:
            err = 0
            
            num_bytes = libssl.SSL_write(self.ssl, data, len(data))
            err = libssl.SSL_get_error(self.ssl, num_bytes)
        
            if err == SSL_ERROR_WANT_READ:
                sockstate = check_socket_and_wait_for_timeout(self.space,
                    self.w_socket, False)
            elif err == SSL_ERROR_WANT_WRITE:
                sockstate = check_socket_and_wait_for_timeout(self.space,
                    self.w_socket, True)
            else:
                sockstate = SOCKET_OPERATION_OK
        
            if sockstate == SOCKET_HAS_TIMED_OUT:
                raise OperationError(self.space.w_Exception,
                    self.space.wrap("The connect operation timed out"))
            elif sockstate == SOCKET_HAS_BEEN_CLOSED:
                raise OperationError(self.space.w_Exception,
                    self.space.wrap("Underlying socket has been closed."))
            elif sockstate == SOCKET_IS_NONBLOCKING:
                break
        
            if err == SSL_ERROR_WANT_READ or err == SSL_ERROR_WANT_WRITE:
                continue
            else:
                break
        
        if num_bytes > 0:
            return self.space.wrap(num_bytes)
        else:
            errstr, errval = _ssl_seterror(self.space, self, num_bytes)
            raise OperationError(self.space.w_Exception,
                self.space.wrap("%s: %d" % (errstr, errval)))
    write.unwrap_spec = ['self', 'bufferstr']
    
    def read(self, num_bytes=1024):
        """read([len]) -> string

        Read up to len bytes from the SSL socket."""

        count = libssl.SSL_pending(self.ssl)
        if not count:
            sockstate = check_socket_and_wait_for_timeout(self.space,
                self.w_socket, False)
            if sockstate == SOCKET_HAS_TIMED_OUT:
                raise OperationError(self.space.w_Exception,
                    self.space.wrap("The read operation timed out"))
            elif sockstate == SOCKET_TOO_LARGE_FOR_SELECT:
                raise OperationError(self.space.w_Exception,
                    self.space.wrap("Underlying socket too large for select()."))
        
        buf = create_string_buffer(num_bytes)
        while True:
            err = 0
            
            count = libssl.SSL_read(self.ssl, buf, num_bytes)
            err = libssl.SSL_get_error(self.ssl, count)
        
            if err == SSL_ERROR_WANT_READ:
                sockstate = check_socket_and_wait_for_timeout(self.space,
                    self.w_socket, False)
            elif err == SSL_ERROR_WANT_WRITE:
                sockstate = check_socket_and_wait_for_timeout(self.space,
                    self.w_socket, True)
            else:
                sockstate = SOCKET_OPERATION_OK
        
            if sockstate == SOCKET_HAS_TIMED_OUT:
                raise OperationError(self.space.w_Exception,
                    self.space.wrap("The read operation timed out"))
            elif sockstate == SOCKET_IS_NONBLOCKING:
                break
        
            if err == SSL_ERROR_WANT_READ or err == SSL_ERROR_WANT_WRITE:
                continue
            else:
                break
                
        if count <= 0:
            errstr, errval = _ssl_seterror(self.space, self, count)
            raise OperationError(self.space.w_Exception,
                self.space.wrap("%s: %d" % (errstr, errval)))
        
        if count != num_bytes:
            # resize
            data = buf.raw
            assert count >= 0
            try:
                new_data = data[0:count]
            except:
                raise OperationError(self.space.w_MemoryException,
                    self.space.wrap("error in resizing of the buffer."))
            buf = create_string_buffer(count)
            buf.raw = new_data
            
        return self.space.wrap(buf.value)
    read.unwrap_spec = ['self', int]


SSLObject.typedef = TypeDef("SSLObject",
    server = interp2app(SSLObject.server,
        unwrap_spec=SSLObject.server.unwrap_spec),
    issuer = interp2app(SSLObject.issuer,
        unwrap_spec=SSLObject.issuer.unwrap_spec),
    write = interp2app(SSLObject.write,
        unwrap_spec=SSLObject.write.unwrap_spec),
    read = interp2app(SSLObject.read, unwrap_spec=SSLObject.read.unwrap_spec)
)


def new_sslobject(space, w_sock, w_key_file, w_cert_file):
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
    

    if ((key_file and not cert_file) or (not key_file and cert_file)):
        raise OperationError(space.w_Exception,
            space.wrap("Both the key & certificate files must be specified"))

    ss.ctx = libssl.SSL_CTX_new(libssl.SSLv23_method()) # set up context
    if not ss.ctx:
        raise OperationError(space.w_Exception, space.wrap("SSL_CTX_new error"))

    if key_file:
        ret = libssl.SSL_CTX_use_PrivateKey_file(ss.ctx, key_file,
            SSL_FILETYPE_PEM)
        if ret < 1:
            raise OperationError(space.w_Exception,
                space.wrap("SSL_CTX_use_PrivateKey_file error"))

        ret = libssl.SSL_CTX_use_certificate_chain_file(ss.ctx, cert_file)
        libssl.SSL_CTX_ctrl(ss.ctx, SSL_CTRL_OPTIONS, SSL_OP_ALL, c_void_p())
        if ret < 1:
            raise OperationError(space.w_Exception,
                space.wrap("SSL_CTX_use_certificate_chain_file error"))

    libssl.SSL_CTX_set_verify(ss.ctx, SSL_VERIFY_NONE, c_void_p()) # set verify level
    ss.ssl = libssl.SSL_new(ss.ctx) # new ssl struct
    libssl.SSL_set_fd(ss.ssl, sock_fd) # set the socket for SSL

    # If the socket is in non-blocking mode or timeout mode, set the BIO
    # to non-blocking mode (blocking is the default)
    if has_timeout:
        # Set both the read and write BIO's to non-blocking mode
        libssl.BIO_ctrl(libssl.SSL_get_rbio(ss.ssl), BIO_C_SET_NBIO, 1, c_void_p())
        libssl.BIO_ctrl(libssl.SSL_get_wbio(ss.ssl), BIO_C_SET_NBIO, 1, c_void_p())
    libssl.SSL_set_connect_state(ss.ssl)

    # Actually negotiate SSL connection
    # XXX If SSL_connect() returns 0, it's also a failure.
    sockstate = 0
    while True:
        ret = libssl.SSL_connect(ss.ssl)
        err = libssl.SSL_get_error(ss.ssl, ret)
        
        if err == SSL_ERROR_WANT_READ:
            sockstate = check_socket_and_wait_for_timeout(space, w_sock, False)
        elif err == SSL_ERROR_WANT_WRITE:
            sockstate = check_socket_and_wait_for_timeout(space, w_sock, True)
        else:
            sockstate = SOCKET_OPERATION_OK
        
        if sockstate == SOCKET_HAS_TIMED_OUT:
            raise OperationError(space.w_Exception,
                space.wrap("The connect operation timed out"))
        elif sockstate == SOCKET_HAS_BEEN_CLOSED:
            raise OperationError(space.w_Exception,
                space.wrap("Underlying socket has been closed."))
        elif sockstate == SOCKET_TOO_LARGE_FOR_SELECT:
            raise OperationError(space.w_Exception,
                space.wrap("Underlying socket too large for select()."))
        elif sockstate == SOCKET_IS_NONBLOCKING:
            break
        
        if err == SSL_ERROR_WANT_READ or err == SSL_ERROR_WANT_WRITE:
            continue
        else:
            break
    
    if ret < 0:
        errstr, errval = _ssl_seterror(space, ss, ret)
        raise OperationError(space.w_Exception,
            space.wrap("%s: %d" % (errstr, errval)))
    
    ss.server_cert = libssl.SSL_get_peer_certificate(ss.ssl)
    if ss.server_cert:
        libssl.X509_NAME_oneline(libssl.X509_get_subject_name(ss.server_cert),
            ss._server, X509_NAME_MAXLEN)
        libssl.X509_NAME_oneline(libssl.X509_get_issuer_name(ss.server_cert),
            ss._issuer, X509_NAME_MAXLEN)

    ss.w_socket = w_sock
    return ss
new_sslobject.unwrap_spec = [ObjSpace, W_Root, str, str]

def check_socket_and_wait_for_timeout(space, w_sock, writing):
    """If the socket has a timeout, do a select()/poll() on the socket.
    The argument writing indicates the direction.
    Returns one of the possibilities in the timeout_state enum (above)."""

    w_timeout = space.call_method(w_sock, "gettimeout")
    if space.is_w(w_timeout, space.w_None):
        return SOCKET_IS_BLOCKING
    elif space.int_w(w_timeout) == 0.0:
        return SOCKET_IS_NONBLOCKING
    sock_timeout = space.int_w(w_timeout)

    # guard against closed socket
    try:
        space.call_method(w_sock, "fileno")
    except:
        return SOCKET_HAS_BEEN_CLOSED
        
    sock_fd = space.int_w(space.call_method(w_sock, "fileno"))

    # Prefer poll, if available, since you can poll() any fd
    # which can't be done with select().
    if have_poll:
        _pollfd = pollfd()
        _pollfd.fd = sock_fd
        if writing:
            _pollfd.events = POLLOUT
        else:
            _pollfd.events = POLLIN
        # socket's timeout is in seconds, poll's timeout in ms
        timeout = int(sock_timeout * 1000 + 0.5)
        rc = libc.poll(byref(_pollfd), 1, timeout)
        if rc == 0:
            return SOCKET_HAS_TIMED_OUT
        else:
            return SOCKET_OPERATION_OK
    
    if sock_fd >= FD_SETSIZE:
        return SOCKET_TOO_LARGE_FOR_SELECT

    # construct the arguments for select
    sec = int(sock_timeout)
    usec = int((sock_timeout - sec) * 1e6)
    timeout = sec + usec * 0.000001
    # see if the socket is ready
    if writing:
        ret = select.select([], [sock_fd], [], timeout)
        r, w, e = ret
        if not w:
            return SOCKET_HAS_TIMED_OUT
        else:
            return SOCKET_OPERATION_OK
    else:
        ret = select.select([sock_fd], [], [], timeout)
        r, w, e = ret
        if not r:
            return SOCKET_HAS_TIMED_OUT
        else:
            return SOCKET_OPERATION_OK

def _ssl_seterror(space, ss, ret):
    assert ret <= 0

    err = libssl.SSL_get_error(ss.ssl, ret)
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
        e = libssl.ERR_get_error()
        if e == 0:
            if ret == 0 or space.is_w(ss.w_socket, space.w_None):
                errstr = "EOF occurred in violation of protocol"
                errval = PY_SSL_ERROR_EOF
            elif ret == -1:
                # the underlying BIO reported an I/0 error
                return errstr, errval # sock.errorhandler()?
            else:
                errstr = "Some I/O error occurred"
                errval = PY_SSL_ERROR_SYSCALL
        else:
            errstr = libssl.ERR_error_string(e, None)
            errval = PY_SSL_ERROR_SYSCALL
    elif err == SSL_ERROR_SSL:
        e = libssl.ERR_get_error()
        errval = PY_SSL_ERROR_SSL
        if e != 0:
            errstr = libssl.ERR_error_string(e, None)
        else:
            errstr = "A failure in the SSL library occurred"
    else:
        errstr = "Invalid error code"
        errval = PY_SSL_ERROR_INVALID_ERROR_CODE
        
    return errstr, errval


def ssl(space, w_socket, w_key_file=None, w_cert_file=None):
    """ssl(socket, [keyfile, certfile]) -> sslobject"""
    return space.wrap(new_sslobject(space, w_socket, w_key_file, w_cert_file))
ssl.unwrap_spec = [ObjSpace, W_Root, W_Root, W_Root]


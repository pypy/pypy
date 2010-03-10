from pypy.rpython.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app
from pypy.rpython.tool import rffi_platform
from pypy.translator.platform import platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo

from pypy.rlib import rpoll

import sys

if sys.platform == 'win32' and platform.name != 'mingw32':
    libraries = ['libeay32', 'ssleay32', 'user32', 'advapi32', 'gdi32']
else:
    libraries = ['ssl', 'crypto']

eci = ExternalCompilationInfo(
    libraries = libraries,
    includes = ['openssl/ssl.h',
                ],
    export_symbols = ['SSL_load_error_strings'],
    )

eci = rffi_platform.configure_external_library(
    'openssl', eci,
    [dict(prefix='openssl-',
          include_dir='inc32', library_dir='out32'),
     ])

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

SOCKET_IS_NONBLOCKING, SOCKET_IS_BLOCKING = 0, 1
SOCKET_HAS_TIMED_OUT, SOCKET_HAS_BEEN_CLOSED = 2, 3
SOCKET_TOO_LARGE_FOR_SELECT, SOCKET_OPERATION_OK = 4, 5

# WinSock does not use a bitmask in select, and uses
# socket handles greater than FD_SETSIZE
if sys.platform == 'win32':
    MAX_FD_SIZE = None
else:
    from pypy.rlib._rsocket_rffi import FD_SETSIZE as MAX_FD_SIZE

HAVE_RPOLL = True  # Even win32 has rpoll.poll

class CConfig:
    _compilation_info_ = eci

    OPENSSL_VERSION_NUMBER = rffi_platform.ConstantInteger(
        "OPENSSL_VERSION_NUMBER")
    SSL_FILETYPE_PEM = rffi_platform.ConstantInteger("SSL_FILETYPE_PEM")
    SSL_OP_ALL = rffi_platform.ConstantInteger("SSL_OP_ALL")
    SSL_VERIFY_NONE = rffi_platform.ConstantInteger("SSL_VERIFY_NONE")
    SSL_ERROR_WANT_READ = rffi_platform.ConstantInteger(
        "SSL_ERROR_WANT_READ")
    SSL_ERROR_WANT_WRITE = rffi_platform.ConstantInteger(
        "SSL_ERROR_WANT_WRITE")
    SSL_ERROR_ZERO_RETURN = rffi_platform.ConstantInteger(
        "SSL_ERROR_ZERO_RETURN")
    SSL_ERROR_WANT_X509_LOOKUP = rffi_platform.ConstantInteger(
        "SSL_ERROR_WANT_X509_LOOKUP")
    SSL_ERROR_WANT_CONNECT = rffi_platform.ConstantInteger(
        "SSL_ERROR_WANT_CONNECT")
    SSL_ERROR_SYSCALL = rffi_platform.ConstantInteger("SSL_ERROR_SYSCALL")
    SSL_ERROR_SSL = rffi_platform.ConstantInteger("SSL_ERROR_SSL")
    SSL_CTRL_OPTIONS = rffi_platform.ConstantInteger("SSL_CTRL_OPTIONS")
    BIO_C_SET_NBIO = rffi_platform.ConstantInteger("BIO_C_SET_NBIO")

for k, v in rffi_platform.configure(CConfig).items():
    globals()[k] = v

# opaque structures
SSL_METHOD = rffi.VOIDP
SSL_CTX = rffi.VOIDP
SSL = rffi.VOIDP
BIO = rffi.VOIDP
X509 = rffi.VOIDP
X509_NAME = rffi.VOIDP

SSL_CTX_P = rffi.CArrayPtr(SSL_CTX)
BIO_P = rffi.CArrayPtr(BIO)
SSL_P = rffi.CArrayPtr(SSL)
X509_P = rffi.CArrayPtr(X509)
X509_NAME_P = rffi.CArrayPtr(X509_NAME)

HAVE_OPENSSL_RAND = OPENSSL_VERSION_NUMBER >= 0x0090500f

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

def ssl_external(name, argtypes, restype, **kw):
    kw['compilation_info'] = eci
    globals()['libssl_' + name] = rffi.llexternal(
        name, argtypes, restype, **kw)

ssl_external('SSL_load_error_strings', [], lltype.Void)
ssl_external('SSL_library_init', [], rffi.INT)
if HAVE_OPENSSL_RAND:
    ssl_external('RAND_add', [rffi.CCHARP, rffi.INT, rffi.DOUBLE], lltype.Void)
    ssl_external('RAND_status', [], rffi.INT)
    ssl_external('RAND_egd', [rffi.CCHARP], rffi.INT)
ssl_external('SSL_CTX_new', [rffi.CArrayPtr(SSL_METHOD)], SSL_CTX_P)
ssl_external('SSLv23_method', [], rffi.CArrayPtr(SSL_METHOD))
ssl_external('SSL_CTX_use_PrivateKey_file', [SSL_CTX_P, rffi.CCHARP, rffi.INT], rffi.INT)
ssl_external('SSL_CTX_use_certificate_chain_file', [SSL_CTX_P, rffi.CCHARP], rffi.INT)
ssl_external('SSL_CTX_ctrl', [SSL_CTX_P, rffi.INT, rffi.INT, rffi.VOIDP], rffi.INT)
ssl_external('SSL_CTX_set_verify', [SSL_CTX_P, rffi.INT, rffi.VOIDP], lltype.Void)
ssl_external('SSL_new', [SSL_CTX_P], SSL_P)
ssl_external('SSL_set_fd', [SSL_P, rffi.INT], rffi.INT)
ssl_external('BIO_ctrl', [BIO_P, rffi.INT, rffi.INT, rffi.VOIDP], rffi.INT)
ssl_external('SSL_get_rbio', [SSL_P], BIO_P)
ssl_external('SSL_get_wbio', [SSL_P], BIO_P)
ssl_external('SSL_set_connect_state', [SSL_P], lltype.Void)
ssl_external('SSL_connect', [SSL_P], rffi.INT)
ssl_external('SSL_get_error', [SSL_P, rffi.INT], rffi.INT)

ssl_external('ERR_get_error', [], rffi.INT)
ssl_external('ERR_error_string', [rffi.INT, rffi.CCHARP], rffi.CCHARP)
ssl_external('SSL_get_peer_certificate', [SSL_P], X509_P)
ssl_external('X509_get_subject_name', [X509_P], X509_NAME_P)
ssl_external('X509_get_issuer_name', [X509_P], X509_NAME_P)
ssl_external('X509_NAME_oneline', [X509_NAME_P, rffi.CCHARP, rffi.INT], rffi.CCHARP)
ssl_external('X509_free', [X509_P], lltype.Void)
ssl_external('SSL_free', [SSL_P], lltype.Void)
ssl_external('SSL_CTX_free', [SSL_CTX_P], lltype.Void)
ssl_external('SSL_write', [SSL_P, rffi.CCHARP, rffi.INT], rffi.INT)
ssl_external('SSL_pending', [SSL_P], rffi.INT)
ssl_external('SSL_read', [SSL_P, rffi.CCHARP, rffi.INT], rffi.INT)

def ssl_error(space, msg):
    w_module = space.getbuiltinmodule('_ssl')
    w_exception = space.getattr(w_module, space.wrap('sslerror'))
    return OperationError(w_exception, space.wrap(msg))

def _init_ssl():
    libssl_SSL_load_error_strings()
    libssl_SSL_library_init()

if HAVE_OPENSSL_RAND:
    # helper routines for seeding the SSL PRNG
    def RAND_add(space, string, entropy):
        """RAND_add(string, entropy)


        Mix string into the OpenSSL PRNG state.  entropy (a float) is a lower
        bound on the entropy contained in string."""

        buf = rffi.str2charp(string)
        try:
            libssl_RAND_add(buf, len(string), entropy)
        finally:
            rffi.free_charp(buf)
    RAND_add.unwrap_spec = [ObjSpace, str, float]

    def RAND_status(space):
        """RAND_status() -> 0 or 1

        Returns 1 if the OpenSSL PRNG has been seeded with enough data and 0 if not.
        It is necessary to seed the PRNG with RAND_add() on some platforms before
        using the ssl() function."""

        res = libssl_RAND_status()
        return space.wrap(res)
    RAND_status.unwrap_spec = [ObjSpace]

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
    RAND_egd.unwrap_spec = [ObjSpace, str]

class SSLObject(Wrappable):
    def __init__(self, space):
        self.space = space
        self.w_socket = None
        self.ctx = lltype.nullptr(SSL_CTX_P.TO)
        self.ssl = lltype.nullptr(SSL_P.TO)
        self.server_cert = lltype.nullptr(X509_P.TO)
        self._server = lltype.malloc(rffi.CCHARP.TO, X509_NAME_MAXLEN, flavor='raw')
        self._server[0] = '\0'
        self._issuer = lltype.malloc(rffi.CCHARP.TO, X509_NAME_MAXLEN, flavor='raw')
        self._issuer[0] = '\0'
    
    def server(self):
        return self.space.wrap(rffi.charp2str(self._server))
    server.unwrap_spec = ['self']
    
    def issuer(self):
        return self.space.wrap(rffi.charp2str(self._issuer))
    issuer.unwrap_spec = ['self']
    
    def __del__(self):
        if self.server_cert:
            libssl_X509_free(self.server_cert)
        if self.ssl:
            libssl_SSL_free(self.ssl)
        if self.ctx:
            libssl_SSL_CTX_free(self.ctx)
        lltype.free(self._server, flavor='raw')
        lltype.free(self._issuer, flavor='raw')
    
    def write(self, data):
        """write(s) -> len

        Writes the string s into the SSL object.  Returns the number
        of bytes written."""
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
            errstr, errval = _ssl_seterror(self.space, self, num_bytes)
            raise ssl_error(self.space, "%s: %d" % (errstr, errval))
    write.unwrap_spec = ['self', 'bufferstr']
    
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
            errstr, errval = _ssl_seterror(self.space, self, count)
            raise ssl_error(self.space, "%s: %d" % (errstr, errval))

        result = rffi.str_from_buffer(raw_buf, gc_buf, num_bytes, count)
        rffi.keep_buffer_alive_until_here(raw_buf, gc_buf)
        return self.space.wrap(result)
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
        raise ssl_error(space, "Both the key & certificate files must be specified")

    ss.ctx = libssl_SSL_CTX_new(libssl_SSLv23_method()) # set up context
    if not ss.ctx:
        raise ssl_error(space, "SSL_CTX_new error")

    if key_file:
        ret = libssl_SSL_CTX_use_PrivateKey_file(ss.ctx, key_file,
            SSL_FILETYPE_PEM)
        if ret < 1:
            raise ssl_error(space, "SSL_CTX_use_PrivateKey_file error")

        ret = libssl_SSL_CTX_use_certificate_chain_file(ss.ctx, cert_file)
        libssl_SSL_CTX_ctrl(ss.ctx, SSL_CTRL_OPTIONS, SSL_OP_ALL, None)
        if ret < 1:
            raise ssl_error(space, "SSL_CTX_use_certificate_chain_file error")

    libssl_SSL_CTX_set_verify(ss.ctx, SSL_VERIFY_NONE, None) # set verify level
    ss.ssl = libssl_SSL_new(ss.ctx) # new ssl struct
    libssl_SSL_set_fd(ss.ssl, sock_fd) # set the socket for SSL

    # If the socket is in non-blocking mode or timeout mode, set the BIO
    # to non-blocking mode (blocking is the default)
    if has_timeout:
        # Set both the read and write BIO's to non-blocking mode
        libssl_BIO_ctrl(libssl_SSL_get_rbio(ss.ssl), BIO_C_SET_NBIO, 1, None)
        libssl_BIO_ctrl(libssl_SSL_get_wbio(ss.ssl), BIO_C_SET_NBIO, 1, None)
    libssl_SSL_set_connect_state(ss.ssl)

    # Actually negotiate SSL connection
    # XXX If SSL_connect() returns 0, it's also a failure.
    sockstate = 0
    while True:
        ret = libssl_SSL_connect(ss.ssl)
        err = libssl_SSL_get_error(ss.ssl, ret)
        
        if err == SSL_ERROR_WANT_READ:
            sockstate = check_socket_and_wait_for_timeout(space, w_sock, False)
        elif err == SSL_ERROR_WANT_WRITE:
            sockstate = check_socket_and_wait_for_timeout(space, w_sock, True)
        else:
            sockstate = SOCKET_OPERATION_OK
        
        if sockstate == SOCKET_HAS_TIMED_OUT:
            raise ssl_error(space, "The connect operation timed out")
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
        errstr, errval = _ssl_seterror(space, ss, ret)
        raise ssl_error(space, "%s: %d" % (errstr, errval))
    
    ss.server_cert = libssl_SSL_get_peer_certificate(ss.ssl)
    if ss.server_cert:
        libssl_X509_NAME_oneline(libssl_X509_get_subject_name(ss.server_cert),
            ss._server, X509_NAME_MAXLEN)
        libssl_X509_NAME_oneline(libssl_X509_get_issuer_name(ss.server_cert),
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
    elif space.float_w(w_timeout) == 0.0:
        return SOCKET_IS_NONBLOCKING
    sock_timeout = space.float_w(w_timeout)

    # guard against closed socket
    try:
        space.call_method(w_sock, "fileno")
    except:
        return SOCKET_HAS_BEEN_CLOSED

    sock_fd = space.int_w(space.call_method(w_sock, "fileno"))

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
                return errstr, errval # sock.errorhandler()?
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

    return errstr, errval


def ssl(space, w_socket, w_key_file=None, w_cert_file=None):
    """ssl(socket, [keyfile, certfile]) -> sslobject"""
    return space.wrap(new_sslobject(space, w_socket, w_key_file, w_cert_file))
ssl.unwrap_spec = [ObjSpace, W_Root, W_Root, W_Root]


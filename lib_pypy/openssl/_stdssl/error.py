from _openssl import ffi
from _openssl import lib

from openssl._stdssl.utility import _string_from_asn1, _str_to_ffi_buffer

SSL_ERROR_NONE = 0
SSL_ERROR_SSL = 1
SSL_ERROR_WANT_READ = 2
SSL_ERROR_WANT_WRITE = 3
SSL_ERROR_WANT_X509_LOOKUP = 4
SSL_ERROR_SYSCALL = 5
SSL_ERROR_ZERO_RETURN = 6
SSL_ERROR_WANT_CONNECT = 7
# start of non ssl.h errorcodes
SSL_ERROR_EOF = 8 # special case of SSL_ERROR_SYSCALL
SSL_ERROR_NO_SOCKET = 9 # socket has been GC'd
SSL_ERROR_INVALID_ERROR_CODE = 10

class SSLError(OSError):
    """ An error occurred in the SSL implementation. """
    def __str__(self):
        if self.strerror and isinstance(self.strerror, str):
            return self.strerror
        return str(self.args)

class SSLZeroReturnError(SSLError):
    """ SSL/TLS session closed cleanly. """

class SSLWantReadError(SSLError):
    """ Non-blocking SSL socket needs to read more data
        before the requested operation can be completed.
    """

class SSLWantWriteError(SSLError):
    """Non-blocking SSL socket needs to write more data
       before the requested operation can be completed.
    """

class SSLSyscallError(SSLError):
    """ System error when attempting SSL operation. """

class SSLEOFError(SSLError):
    """ SSL/TLS connection terminated abruptly. """

def ssl_lib_error():
    errcode = lib.ERR_peek_last_error()
    lib.ERR_clear_error()
    return ssl_error(None, 0, None, errcode)

def ssl_error(msg, errno=0, errtype=None, errcode=0):
    reason_str = None
    lib_str = None
    if errcode:
        err_lib = lib.ERR_GET_LIB(errcode)
        err_reason = lib.ERR_GET_REASON(errcode)
        reason_str = ERR_CODES_TO_NAMES.get((err_lib, err_reason), None)
        lib_str = LIB_CODES_TO_NAMES.get(err_lib, None)
        msg = ffi.string(lib.ERR_reason_error_string(errcode)).decode('utf-8')
    if not msg:
        msg = "unknown error"
    if reason_str and lib_str:
        msg = "[%s: %s] %s" % (lib_str, reason_str, msg)
    elif lib_str:
        msg = "[%s] %s" % (lib_str, msg)

    if errno or errcode:
        error = SSLError(errno, msg)
    else:
        error = SSLError(msg)
    error.reason = reason_str if reason_str else None
    error.library = lib_str if lib_str else None
    return error

ERR_CODES_TO_NAMES = {}
ERR_NAMES_TO_CODES = {}
LIB_CODES_TO_NAMES = {}

from openssl._stdssl.errorcodes import _error_codes, _lib_codes

for mnemo, library, reason in _error_codes:
    key = (library, reason)
    assert mnemo is not None and key is not None
    ERR_CODES_TO_NAMES[key] = mnemo
    ERR_NAMES_TO_CODES[mnemo] = key


for mnemo, number in _lib_codes:
    LIB_CODES_TO_NAMES[number] = mnemo

def _fill_and_raise_ssl_error(error, errcode):
    pass
    if errcode != 0:
        library = lib.ERR_GET_LIB(errcode);
        reason = lib.ERR_GET_REASON(errcode);
        key = (library, reason)
        reason_obj = ERR_CODES_TO_NAMES[key]
        lib_obj = LIB_CODES_TO_NAMES[library]
        raise error("[%S: %S]" % (lib_obj, reason_obj))

def _last_error():
    errcode = lib.ERR_peek_last_error()
    _fill_and_raise_ssl_error(SSLError, errcode)
    #buf = ffi.new("char[4096]")
    #length = lib.ERR_error_string(errcode, buf)
    #return ffi.string(buf).decode()


# the PySSL_SetError equivalent
def ssl_socket_error(ss, ret):
    errcode = lib.ERR_peek_last_error()

    if ss is None:
        return ssl_error(None, errcode=errcode)
    elif ss.ssl:
        err = lib.SSL_get_error(ss.ssl, ret)
    else:
        err = SSL_ERROR_SSL
    errstr = ""
    errval = 0
    errtype = SSLError

    if err == SSL_ERROR_ZERO_RETURN:
        errtype = ZeroReturnError
        errstr = "TLS/SSL connection has been closed"
        errval = SSL_ERROR_ZERO_RETURN
    elif err == SSL_ERROR_WANT_READ:
        errtype = WantReadError
        errstr = "The operation did not complete (read)"
        errval = SSL_ERROR_WANT_READ
    elif err == SSL_ERROR_WANT_WRITE:
        errtype = WantWriteError
        errstr = "The operation did not complete (write)"
        errval = SSL_ERROR_WANT_WRITE
    elif err == SSL_ERROR_WANT_X509_LOOKUP:
        errstr = "The operation did not complete (X509 lookup)"
        errval = SSL_ERROR_WANT_X509_LOOKUP
    elif err == SSL_ERROR_WANT_CONNECT:
        errstr = "The operation did not complete (connect)"
        errval = SSL_ERROR_WANT_CONNECT
    elif err == SSL_ERROR_SYSCALL:
        xxx
        e = lib.ERR_get_error()
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
        errval = SSL_ERROR_SSL
        if errcode != 0:
            errstr = _str_to_ffi_buffer(lib.ERR_error_string(errcode, ffi.NULL))
        else:
            errstr = "A failure in the SSL library occurred"
    else:
        errstr = "Invalid error code"
        errval = SSL_ERROR_INVALID_ERROR_CODE

    return errtype(errstr, errval)


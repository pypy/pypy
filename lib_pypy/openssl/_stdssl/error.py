from _openssl import ffi
from _openssl import lib

from openssl._stdssl.utility import _string_from_asn1, _str_to_ffi_buffer, _str_from_buf

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

def ssl_error(errstr, errcode=0):
    if errstr is None:
        errcode = lib.ERR_peek_last_error()
    try:
        return fill_sslerror(SSLError, errcode, errstr)
    finally:
        lib.ERR_clear_error()

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


# the PySSL_SetError equivalent
def pyssl_error(obj, ret):
    errcode = lib.ERR_peek_last_error()

    errstr = ""
    errval = 0
    errtype = SSLError
    e = lib.ERR_peek_last_error()

    if obj.ssl != ffi.NULL:
        err = lib.SSL_get_error(obj.ssl, ret)

        if err == SSL_ERROR_ZERO_RETURN:
            errtype = SSLZeroReturnError
            errstr = "TLS/SSL connection has been closed"
            errval = SSL_ERROR_ZERO_RETURN
        elif err == SSL_ERROR_WANT_READ:
            errtype = SSLWantReadError
            errstr = "The operation did not complete (read)"
            errval = SSL_ERROR_WANT_READ
        elif err == SSL_ERROR_WANT_WRITE:
            errtype = SSLWantWriteError
            errstr = "The operation did not complete (write)"
            errval = SSL_ERROR_WANT_WRITE
        elif err == SSL_ERROR_WANT_X509_LOOKUP:
            errstr = "The operation did not complete (X509 lookup)"
            errval = SSL_ERROR_WANT_X509_LOOKUP
        elif err == SSL_ERROR_WANT_CONNECT:
            errstr = "The operation did not complete (connect)"
            errval = SSL_ERROR_WANT_CONNECT
        elif err == SSL_ERROR_SYSCALL:
            if e == 0:
                if ret == 0 or obj.get_socket_or_None() is None:
                    errtype = EOFError
                    errstr = "EOF occurred in violation of protocol"
                    errval = SSL_ERROR_EOF
                elif ret == -1:
                    # the underlying BIO reported an I/0 error
                    errno = ffi.errno
                    return IOError(errno)
                else:
                    errtype = SSLSyscallError
                    errstr = "Some I/O error occurred"
                    errval = SSL_ERROR_SYSCALL
            else:
                errstr = _str_from_buf(lib.ERR_error_string(e, ffi.NULL))
                errval = SSL_ERROR_SYSCALL
        elif err == SSL_ERROR_SSL:
            errval = SSL_ERROR_SSL
            if errcode != 0:
                errstr = _str_from_buf(lib.ERR_error_string(errcode, ffi.NULL))
            else:
                errstr = "A failure in the SSL library occurred"
        else:
            errstr = "Invalid error code"
            errval = SSL_ERROR_INVALID_ERROR_CODE
    return fill_sslerror(errtype, errval, errstr, e)


def fill_sslerror(errtype, ssl_errno, errstr, errcode):
    reason_str = None
    lib_str = None
    if errcode != 0:
        err_lib = lib.ERR_GET_LIB(errcode)
        err_reason = lib.ERR_GET_REASON(errcode)
        reason_str = ERR_CODES_TO_NAMES.get((err_lib, err_reason), None)
        lib_str = LIB_CODES_TO_NAMES.get(err_lib, None)
        if errstr is None:
            errstr = _str_from_buf(lib.ERR_reason_error_string(errcode))
    if not errstr:
        msg = "unknown error"
    if reason_str and lib_str:
        msg = "[%s: %s] %s" % (lib_str, reason_str, errstr)
    elif lib_str:
        msg = "[%s] %s" % (lib_str, errstr)

    err_value = errtype(ssl_errno, msg)
    err_value.reason = reason_str if reason_str else None
    err_value.library = lib_str if lib_str else None
    return err_value


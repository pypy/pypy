from _openssl import ffi
from _openssl import lib

class SSLError(OSError):
    """ An error occurred in the SSL implementation. """

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


def ssl_error(msg, errno=0, errtype=None, errcode=0):
    reason_str = None
    lib_str = None
    if errcode:
        err_lib = lib.ERR_GET_LIB(errcode)
        err_reason = lib.ERR_GET_REASON(errcode)
        reason_str = ERROR_CODES_TO_NAMES.get((err_lib, err_reason), None)
        lib_str = LIBRARY_CODES_TO_NAMES.get(err_lib, None)
        msg = ffi.string(lib.ERR_reason_error_string(errcode)).decode('utf-8')
    if not msg:
        msg = "unknown error"
    if reason_str and lib_str:
        msg = "[%s: %s] %s" % (lib_str, reason_str, msg)
    elif lib_str:
        msg = "[%s] %s" % (lib_str, msg)

    raise SSLError(msg)
    #w_exception_class = w_errtype or get_error(space).w_error
    #if errno or errcode:
    #    w_exception = space.call_function(w_exception_class,
    #                                      space.wrap(errno), space.wrap(msg))
    #else:
    #    w_exception = space.call_function(w_exception_class, space.wrap(msg))
    #space.setattr(w_exception, space.wrap("reason"),
    #              space.wrap(reason_str) if reason_str else space.w_None)
    #space.setattr(w_exception, space.wrap("library"),
    #              space.wrap(lib_str) if lib_str else space.w_None)
    #return OperationError(w_exception_class, w_exception)

ERR_CODES_TO_NAMES = {}
LIB_CODES_TO_NAMES = {}

# TODO errcode = error_codes;
# TODO while (errcode->mnemonic != NULL) {
# TODO     mnemo = PyUnicode_FromString(errcode->mnemonic);
# TODO     key = Py_BuildValue("ii", errcode->library, errcode->reason);
# TODO     if (mnemo == NULL || key == NULL)
# TODO         return NULL;
# TODO     if (PyDict_SetItem(err_codes_to_names, key, mnemo))
# TODO         return NULL;
# TODO     if (PyDict_SetItem(err_names_to_codes, mnemo, key))
# TODO         return NULL;
# TODO     Py_DECREF(key);
# TODO     Py_DECREF(mnemo);
# TODO     errcode++;
# TODO }

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


def _ssl_seterror(ss, ret):
    assert ret <= 0

    errcode = lib.ERR_peek_last_error()

    if ss is None:
        return ssl_error(None, errcode=errcode)
    elif ss.ssl:
        err = lib.SSL_get_error(ss.ssl, ret)
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


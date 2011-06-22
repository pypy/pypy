from __future__ import with_statement
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, unwrap_spec

from pypy.rlib.rarithmetic import intmask
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
    w_exception = space.call_function(w_exception_class,
                                      space.wrap(errno), space.wrap(msg))
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

    def cipher(self, space):
        if not self.ssl:
            return space.w_None
        current = libssl_SSL_get_current_cipher(self.ssl)
        if not current:
            return space.w_None

        name = libssl_SSL_CIPHER_get_name(current)
        if name:
            w_name = space.wrap(rffi.charp2str(name))
        else:
            w_name = space.w_None

        proto = libssl_SSL_CIPHER_get_version(current)
        if proto:
            w_proto = space.wrap(rffi.charp2str(name))
        else:
            w_proto = space.w_None

        bits = libssl_SSL_CIPHER_get_bits(current, 
                                          lltype.nullptr(rffi.INTP.TO))
        w_bits = space.newint(bits)

        return space.newtuple([w_name, w_proto, w_bits])

    @unwrap_spec(der=bool)
    def peer_certificate(self, der=False):
        """peer_certificate([der=False]) -> certificate

        Returns the certificate for the peer.  If no certificate was provided,
        returns None.  If a certificate was provided, but not validated, returns
        an empty dictionary.  Otherwise returns a dict containing information
        about the peer certificate.

        If the optional argument is True, returns a DER-encoded copy of the
        peer certificate, or None if no certificate was provided.  This will
        return the certificate even if it wasn't validated."""
        if not self.peer_cert:
            return self.space.w_None

        if der:
            # return cert in DER-encoded format
            with lltype.scoped_alloc(rffi.CCHARPP.TO, 1) as buf_ptr:
                buf_ptr[0] = lltype.nullptr(rffi.CCHARP.TO)
                length = libssl_i2d_X509(self.peer_cert, buf_ptr)
                if length < 0:
                    raise _ssl_seterror(self.space, self, length)
                try:
                    # this is actually an immutable bytes sequence
                    return self.space.wrap(rffi.charp2str(buf_ptr[0]))
                finally:
                    libssl_OPENSSL_free(buf_ptr[0])
        else:
            verification = libssl_SSL_CTX_get_verify_mode(
                libssl_SSL_get_SSL_CTX(self.ssl))
            if not verification & SSL_VERIFY_PEER:
                return self.space.newdict()
            else:
                return _decode_certificate(self.space, self.peer_cert)

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
        i = 0
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
                if intmask(name[0].c_type) == GEN_DIRNAME:

                    # we special-case DirName as a tuple of tuples of attributes
                    dirname = libssl_pypy_GENERAL_NAME_dirn(name)
                    w_t = space.newtuple([
                            space.wrap("DirName"),
                            _create_tuple_for_X509_NAME(space, dirname)
                            ])
                else:

                    # for everything else, we use the OpenSSL print form

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

SSLObject.typedef = TypeDef("SSLObject",
    server = interp2app(SSLObject.server),
    issuer = interp2app(SSLObject.issuer),
    write = interp2app(SSLObject.write),
    pending = interp2app(SSLObject.pending),
    read = interp2app(SSLObject.read),
    do_handshake = interp2app(SSLObject.do_handshake),
    shutdown = interp2app(SSLObject.shutdown),
    cipher = interp2app(SSLObject.cipher),
    peer_certificate = interp2app(SSLObject.peer_certificate),
)


def new_sslobject(space, w_sock, side, w_key_file, w_cert_file,
                  cert_mode, protocol, w_cacerts_file, w_ciphers):
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
    if space.is_w(w_cacerts_file, space.w_None):
        cacerts_file = None
    else:
        cacerts_file = space.str_w(w_cacerts_file)
    if space.is_w(w_ciphers, space.w_None):
        ciphers = None
    else:
        ciphers = space.str_w(w_ciphers)

    if side == PY_SSL_SERVER and (not key_file or not cert_file):
        raise ssl_error(space, "Both the key & certificate files "
                        "must be specified for server-side operation")

    # set up context
    if protocol == PY_SSL_VERSION_TLS1:
        method = libssl_TLSv1_method()
    elif protocol == PY_SSL_VERSION_SSL3:
        method = libssl_SSLv3_method()
    elif protocol == PY_SSL_VERSION_SSL2:
        method = libssl_SSLv2_method()
    elif protocol == PY_SSL_VERSION_SSL23:
        method = libssl_SSLv23_method()
    else:
        raise ssl_error(space, "Invalid SSL protocol variant specified")
    ss.ctx = libssl_SSL_CTX_new(method)
    if not ss.ctx:
        raise ssl_error(space, "Could not create SSL context")

    if ciphers:
        ret = libssl_SSL_CTX_set_cipher_list(ss.ctx, ciphers)
        if ret == 0:
            raise ssl_error(space, "No cipher can be selected.")

    if cert_mode != PY_SSL_CERT_NONE:
        if not cacerts_file:
            raise ssl_error(space,
                            "No root certificates specified for "
                            "verification of other-side certificates.")
        ret = libssl_SSL_CTX_load_verify_locations(ss.ctx, cacerts_file, None)
        if ret != 1:
            raise _ssl_seterror(space, None, 0)

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

    verification_mode = SSL_VERIFY_NONE
    if cert_mode == PY_SSL_CERT_OPTIONAL:
        verification_mode = SSL_VERIFY_PEER
    elif cert_mode == PY_SSL_CERT_REQUIRED:
        verification_mode = SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT
    libssl_SSL_CTX_set_verify(ss.ctx, verification_mode, None)
    ss.ssl = libssl_SSL_new(ss.ctx) # new ssl struct
    libssl_SSL_set_fd(ss.ssl, sock_fd) # set the socket for SSL
    libssl_SSL_set_mode(ss.ssl, SSL_MODE_AUTO_RETRY)

    # If the socket is in non-blocking mode or timeout mode, set the BIO
    # to non-blocking mode (blocking is the default)
    if has_timeout:
        # Set both the read and write BIO's to non-blocking mode
        libssl_BIO_set_nbio(libssl_SSL_get_rbio(ss.ssl), 1)
        libssl_BIO_set_nbio(libssl_SSL_get_wbio(ss.ssl), 1)
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

    if ss and ss.ssl:
        err = libssl_SSL_get_error(ss.ssl, ret)
    else:
        err = SSL_ERROR_SSL
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
            w_cacerts_file=None, w_ciphers=None):
    """sslwrap(socket, side, [keyfile, certfile]) -> sslobject"""
    return space.wrap(new_sslobject(
        space, w_socket, side, w_key_file, w_cert_file,
        cert_mode, protocol,
        w_cacerts_file, w_ciphers))

class Cache:
    def __init__(self, space):
        w_socketerror = interp_socket.get_error(space, "error")
        self.w_error = space.new_exception_class(
            "_ssl.SSLError", w_socketerror)

def get_error(space):
    return space.fromcache(Cache).w_error

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
    
# this function is needed to perform locking on shared data
# structures. (Note that OpenSSL uses a number of global data
# structures that will be implicitly shared whenever multiple threads
# use OpenSSL.) Multi-threaded applications will crash at random if
# it is not set.
#
# locking_function() must be able to handle up to CRYPTO_num_locks()
# different mutex locks. It sets the n-th lock if mode & CRYPTO_LOCK, and
# releases it otherwise.
#
# filename and line are the file number of the function setting the
# lock. They can be useful for debugging.
_ssl_locks = []

def _ssl_thread_locking_function(mode, n, filename, line):
    n = intmask(n)
    if n < 0 or n >= len(_ssl_locks):
        return

    if intmask(mode) & CRYPTO_LOCK:
        _ssl_locks[n].acquire(True)
    else:
        _ssl_locks[n].release()

def _ssl_thread_id_function():
    from pypy.module.thread import ll_thread
    return rffi.cast(rffi.INT, ll_thread.get_ident())

def setup_ssl_threads():
    from pypy.module.thread import ll_thread
    for i in range(libssl_CRYPTO_num_locks()):
        _ssl_locks.append(ll_thread.allocate_lock())
    libssl_CRYPTO_set_locking_callback(_ssl_thread_locking_function)
    libssl_CRYPTO_set_id_callback(_ssl_thread_id_function)

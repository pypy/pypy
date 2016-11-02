from _openssl import ffi
from _openssl import lib
from _ssl._stdssl.certificate import *
from _ssl._stdssl.certificate import _test_decode_cert
from _ssl._stdssl.utility import _str_with_len

from _ssl._stdssl.error import *
from _ssl._stdssl.error import _last_error

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

CERT_NONE = 0
CERT_OPTIONAL = 1
CERT_REQUIRED = 2

for name in dir(lib):
    if name.startswith('SSL_OP'):
        globals()[name[4:]] = getattr(lib, name)


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
    w_callable = None
    password = None
    operationerror = None
PWINFO_STORAGE = {}


class _SSLContext(object):
    __slots__ = ('ctx', 'check_hostname', 'verify_mode')

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
        elif protocol == PROTOCOL_SSLv2 and lib.Cryptography_HAS_SSL2_METHOD:
            method = lib.SSLv2_method()
        elif protocol == PROTOCOL_SSLv23:
            method = lib.SSLv23_method()
        else:
            raise ValueError("invalid protocol version")

        self.ctx = lib.SSL_CTX_new(method)
        if self.ctx == ffi.NULL: 
            raise ssl_error("failed to allocate SSL context")

        self.check_hostname = False
        # TODO self.register_finalizer(space)

        # Defaults
        lib.SSL_CTX_set_verify(self.ctx, lib.SSL_VERIFY_NONE, ffi.NULL)
        options = lib.SSL_OP_ALL & ~lib.SSL_OP_DONT_INSERT_EMPTY_FRAGMENTS
        if protocol != PROTOCOL_SSLv2:
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
                    # TODO copy from ropenssl?
                    raise _ssl_seterror(None, 0)
                try:
                    lib.SSL_CTX_set_tmp_ecdh(self.ctx, key)
                finally:
                    lib.EC_KEY_free(key)
        return self

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
        if password is None:
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

            lib.SSL_CTX_set_default_passwd_cb(self.ctx, _password_callback)
            lib.SSL_CTX_set_default_passwd_cb_userdata(
                self.ctx, rffi.cast(rffi.VOIDP, index))

        try:
            ret = lib.SSL_CTX_use_certificate_chain_file(self.ctx, certfile)
            if ret != 1:
                if pw_info.operationerror:
                    libssl_ERR_clear_error()
                    raise pw_info.operationerror
                errno = get_saved_errno()
                if errno:
                    lib.ERR_clear_error()
                    raise OSError(OSError(errno, ''))
                else:
                    raise _ssl_seterror(space, None, -1)

            ret = lib.SSL_CTX_use_PrivateKey_file(self.ctx, keyfile,
                                                  lib.SSL_FILETYPE_PEM)
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
            lib.SSL_CTX_set_default_passwd_cb(
                self.ctx, lltype.nullptr(pem_password_cb.TO))
            lib.SSL_CTX_set_default_passwd_cb_userdata(
                self.ctx, None)


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
#
#    @unwrap_spec(server_side=int)
#    def wrap_socket_w(self, space, w_sock, server_side,
#                      w_server_hostname=None):
#        assert w_sock is not None
#        # server_hostname is either None (or absent), or to be encoded
#        # using the idna encoding.
#        if space.is_none(w_server_hostname):
#            hostname = None
#        else:
#            hostname = space.bytes_w(
#                space.call_method(w_server_hostname,
#                                  "encode", space.wrap("idna")))
#
#        if hostname and not HAS_SNI:
#            raise oefmt(space.w_ValueError,
#                        "server_hostname is not supported by your OpenSSL "
#                        "library")
#
#        return new_sslobject(space, self, w_sock, server_side, hostname)
#
#    def session_stats_w(self, space):
#        w_stats = space.newdict()
#        for name, ssl_func in SSL_CTX_STATS:
#            w_value = space.wrap(ssl_func(self.ctx))
#            space.setitem_str(w_stats, name, w_value)
#        return w_stats
#
#    def descr_set_default_verify_paths(self, space):
#        if not libssl_SSL_CTX_set_default_verify_paths(self.ctx):
#            raise ssl_error(space, "")
#
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
#    def descr_get_verify_mode(self, space):
#        mode = libssl_SSL_CTX_get_verify_mode(self.ctx)
#        if mode == SSL_VERIFY_NONE:
#            return space.newlong(PY_SSL_CERT_NONE)
#        elif mode == SSL_VERIFY_PEER:
#            return space.newlong(PY_SSL_CERT_OPTIONAL)
#        elif mode == SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT:
#            return space.newlong(PY_SSL_CERT_REQUIRED)
#        raise ssl_error(space, "invalid return value from SSL_CTX_get_verify_mode")
#
#    def descr_set_verify_mode(self, space, w_mode):
#        n = space.int_w(w_mode)
#        if n == PY_SSL_CERT_NONE:
#            mode = SSL_VERIFY_NONE
#        elif n == PY_SSL_CERT_OPTIONAL:
#            mode = SSL_VERIFY_PEER
#        elif n == PY_SSL_CERT_REQUIRED:
#            mode = SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT
#        else:
#            raise oefmt(space.w_ValueError,
#                        "invalid value for verify_mode")
#        if mode == SSL_VERIFY_NONE and self.check_hostname:
#            raise oefmt(space.w_ValueError,
#                        "Cannot set verify_mode to CERT_NONE when "
#                        "check_hostname is enabled.")
#        libssl_SSL_CTX_set_verify(self.ctx, mode, None)
#
#    def descr_get_verify_flags(self, space):
#        store = libssl_SSL_CTX_get_cert_store(self.ctx)
#        flags = libssl_X509_VERIFY_PARAM_get_flags(store[0].c_param)
#        return space.wrap(flags)
#
#    def descr_set_verify_flags(self, space, w_obj):
#        new_flags = space.int_w(w_obj)
#        store = libssl_SSL_CTX_get_cert_store(self.ctx)
#        flags = libssl_X509_VERIFY_PARAM_get_flags(store[0].c_param)
#        flags_clear = flags & ~new_flags
#        flags_set = ~flags & new_flags
#        if flags_clear and not libssl_X509_VERIFY_PARAM_clear_flags(
#                store[0].c_param, flags_clear):
#            raise _ssl_seterror(space, None, 0)
#        if flags_set and not libssl_X509_VERIFY_PARAM_set_flags(
#                store[0].c_param, flags_set):
#            raise _ssl_seterror(space, None, 0)
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
#    @unwrap_spec(filepath=str)
#    def load_dh_params_w(self, space, filepath):
#        bio = libssl_BIO_new_file(filepath, "r")
#        if not bio:
#            errno = get_saved_errno()
#            libssl_ERR_clear_error()
#            raise wrap_oserror(space, OSError(errno, ''),
#                               exception_name = 'w_IOError')
#        try:
#            dh = libssl_PEM_read_bio_DHparams(bio, None, None, None)
#        finally:
#            libssl_BIO_free(bio)
#        if not dh:
#            errno = get_saved_errno()
#            if errno != 0:
#                libssl_ERR_clear_error()
#                raise wrap_oserror(space, OSError(errno, ''))
#            else:
#                raise _ssl_seterror(space, None, 0)
#        try:
#            if libssl_SSL_CTX_set_tmp_dh(self.ctx, dh) == 0:
#                raise _ssl_seterror(space, None, 0)
#        finally:
#            libssl_DH_free(dh)
#
#    def load_verify_locations_w(self, space, w_cafile=None, w_capath=None,
#                                w_cadata=None):
#        if space.is_none(w_cafile):
#            cafile = None
#        else:
#            cafile = space.str_w(w_cafile)
#        if space.is_none(w_capath):
#            capath = None
#        else:
#            capath = space.str_w(w_capath)
#        if space.is_none(w_cadata):
#            cadata = None
#            ca_file_type = -1
#        else:
#            if not space.isinstance_w(w_cadata, space.w_unicode):
#                ca_file_type = SSL_FILETYPE_ASN1
#                cadata = space.bufferstr_w(w_cadata)
#            else:
#                ca_file_type = SSL_FILETYPE_PEM
#                try:
#                    cadata = space.unicode_w(w_cadata).encode('ascii')
#                except UnicodeEncodeError:
#                    raise oefmt(space.w_TypeError,
#                                "cadata should be a ASCII string or a "
#                                "bytes-like object")
#        if cafile is None and capath is None and cadata is None:
#            raise oefmt(space.w_TypeError,
#                        "cafile and capath cannot be both omitted")
#        # load from cadata
#        if cadata is not None:
#            with rffi.scoped_nonmovingbuffer(cadata) as buf:
#                self._add_ca_certs(space, buf, len(cadata), ca_file_type)
#
#        # load cafile or capath
#        if cafile is not None or capath is not None:
#            ret = libssl_SSL_CTX_load_verify_locations(
#                self.ctx, cafile, capath)
#            if ret != 1:
#                errno = get_saved_errno()
#                if errno:
#                    libssl_ERR_clear_error()
#                    raise wrap_oserror(space, OSError(errno, ''),
#                                       exception_name = 'w_IOError')
#                else:
#                    raise _ssl_seterror(space, None, -1)
#
#    def _add_ca_certs(self, space, data, size, ca_file_type):
#        biobuf = libssl_BIO_new_mem_buf(data, size)
#        if not biobuf:
#            raise ssl_error(space, "Can't allocate buffer")
#        try:
#            store = libssl_SSL_CTX_get_cert_store(self.ctx)
#            loaded = 0
#            while True:
#                if ca_file_type == SSL_FILETYPE_ASN1:
#                    cert = libssl_d2i_X509_bio(
#                        biobuf, None)
#                else:
#                    cert = libssl_PEM_read_bio_X509(
#                        biobuf, None, None, None)
#                if not cert:
#                    break
#                try:
#                    r = libssl_X509_STORE_add_cert(store, cert)
#                finally:
#                    libssl_X509_free(cert)
#                if not r:
#                    err = libssl_ERR_peek_last_error()
#                    if (libssl_ERR_GET_LIB(err) == ERR_LIB_X509 and
#                        libssl_ERR_GET_REASON(err) ==
#                        X509_R_CERT_ALREADY_IN_HASH_TABLE):
#                        # cert already in hash table, not an error
#                        libssl_ERR_clear_error()
#                    else:
#                        break
#                loaded += 1
#
#            err = libssl_ERR_peek_last_error()
#            if (ca_file_type == SSL_FILETYPE_ASN1 and
#                loaded > 0 and
#                libssl_ERR_GET_LIB(err) == ERR_LIB_ASN1 and
#                libssl_ERR_GET_REASON(err) == ASN1_R_HEADER_TOO_LONG):
#                # EOF ASN1 file, not an error
#                libssl_ERR_clear_error()
#            elif (ca_file_type == SSL_FILETYPE_PEM and
#                  loaded > 0 and
#                  libssl_ERR_GET_LIB(err) == ERR_LIB_PEM and
#                  libssl_ERR_GET_REASON(err) == PEM_R_NO_START_LINE):
#                # EOF PEM file, not an error
#                libssl_ERR_clear_error()
#            else:
#                raise _ssl_seterror(space, None, 0)
#        finally:
#            libssl_BIO_free(biobuf)
#
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
#    def get_ca_certs_w(self, space, w_binary_form=None):
#        if w_binary_form and space.is_true(w_binary_form):
#            binary_mode = True
#        else:
#            binary_mode = False
#        rlist = []
#        store = libssl_SSL_CTX_get_cert_store(self.ctx)
#        for i in range(libssl_sk_X509_OBJECT_num(store[0].c_objs)):
#            obj = libssl_sk_X509_OBJECT_value(store[0].c_objs, i)
#            if intmask(obj.c_type) != X509_LU_X509:
#                # not a x509 cert
#                continue
#            # CA for any purpose
#            cert = libssl_pypy_X509_OBJECT_data_x509(obj)
#            if not libssl_X509_check_ca(cert):
#                continue
#            if binary_mode:
#                rlist.append(_certificate_to_der(space, cert))
#            else:
#                rlist.append(_decode_certificate(space, cert))
#        return space.newlist(rlist)
#
#    @unwrap_spec(name=str)
#    def set_ecdh_curve_w(self, space, name):
#        nid = libssl_OBJ_sn2nid(name)
#        if nid == 0:
#            raise oefmt(space.w_ValueError,
#                        "unknown elliptic curve name '%s'", name)
#        key = libssl_EC_KEY_new_by_curve_name(nid)
#        if not key:
#            raise _ssl_seterror(space, None, 0)
#        try:
#            libssl_SSL_CTX_set_tmp_ecdh(self.ctx, key)
#        finally:
#            libssl_EC_KEY_free(key)
#
#    def set_servername_callback_w(self, space, w_callback):
#        if space.is_none(w_callback):
#            libssl_SSL_CTX_set_tlsext_servername_callback(
#                self.ctx, lltype.nullptr(servername_cb.TO))
#            self.servername_callback = None
#            return
#        if not space.is_true(space.callable(w_callback)):
#            raise oefmt(space.w_TypeError, "not a callable object")
#        callback_struct = ServernameCallback()
#        callback_struct.space = space
#        callback_struct.w_ctx = self
#        callback_struct.w_set_hostname = w_callback
#        self.servername_callback = callback_struct
#        index = compute_unique_id(self)
#        SERVERNAME_CALLBACKS.set(index, callback_struct)
#        libssl_SSL_CTX_set_tlsext_servername_callback(
#            self.ctx, _servername_callback)
#        libssl_SSL_CTX_set_tlsext_servername_arg(self.ctx,
#                                                 rffi.cast(rffi.VOIDP, index))
#
#

def _asn1obj2py(obj):
    nid = lib.OBJ_obj2nid(obj)
    if nid == lib.NID_undef:
        raise ValueError("Unknown object")
    sn = lib.OBJ_nid2sn(nid)
    ln = lib.OBJ_nid2ln(nid)
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
    obj = lib.OBJ_txt2obj(_bytes, int(name))
    if obj is ffi.NULL:
        raise ValueError("unkown object '%s'", txt)
    result = _asn1obj2py(obj)
    lib.ASN1_OBJECT_free(obj)
    return result

def nid2obj(nid):
    raise NotImplementedError
                                                               

class MemoryBIO(object):
    pass # TODO

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

def _str_to_ffi_buffer(view):
    # REVIEW unsure how to solve this. might be easy:
    # str does not support buffer protocol.
    # I think a user should really encode the string before it is 
    # passed here!
    if isinstance(view, str):
        return ffi.from_buffer(view.encode())
    else:
        return ffi.from_buffer(view)

def RAND_add(view, entropy):
    buf = _str_to_ffi_buffer(view)
    lib.RAND_add(buf, len(buf), entropy)





import sys
from _thread import allocate_lock as Lock
from _pypy_openssl import ffi, lib
from _cffi_ssl._stdssl.utility import (_str_to_ffi_buffer, _bytes_with_len,
        _str_from_buf)

try: from __pypy__ import builtinify
except ImportError: builtinify = lambda f: f

class UnsupportedDigestmodError(ValueError):
    pass


def get_errstr():
    # From CPython's _setException
    errcode = lib.ERR_peek_last_error();
    if not errcode:
        return "unknown reasons"

    errlib = lib.ERR_lib_error_string(errcode)
    func = lib.ERR_func_error_string(errcode)
    reason = lib.ERR_reason_error_string(errcode)

    if errlib and func:
        return "[%s: %s] %s" % (_str_from_buf(errlib), _str_from_buf(func), _str_from_buf(reason))
    elif errlib:
        return "[%s] %s" % (_str_from_buf(errlib), _str_from_buf(reason))
    else:
        return _str_from_buf(reason)


def new(name, string=b'', usedforsecurity=True):
    h = HASH(name, usedforsecurity=usedforsecurity)
    h.update(string)
    return h

class Immutable(type):
    def __init__(cls, name, bases, dct):
        type.__setattr__(cls,"attr",set(dct.keys()))
        type.__init__(cls, name, bases, dct)

    def __setattr__(cls, name, value):
        # Mock Py_TPFLAGS_IMMUTABLETYPE
        qualname = '.'.join([cls.__module__, cls.__name__])
        raise TypeError(f"cannot set '{name}' attribute of immutable type '{qualname}'")


class HASH(object, metaclass=Immutable):

    def __init__(self, name=None, copy_from=None, usedforsecurity=True):
        if name is None:
            qualname = '.'.join([type(self).__module__, type(self).__name__])
            raise TypeError(f"cannot create '{qualname}' instances")
        object.__setattr__(self, 'ctx', ffi.NULL)
        self.ctx = ffi.NULL
        object.__setattr__(self, 'name', str(name).lower())
        digest_type = self.digest_type_by_name()
        object.__setattr__(self, 'digest_size', lib.EVP_MD_size(digest_type))

        # Allocate a lock for each HASH object.
        # An optimization would be to not release the GIL on small requests,
        # and use a custom lock only when needed.
        object.__setattr__(self, 'lock', Lock())

        # Start EVPnew
        ctx = lib.Cryptography_EVP_MD_CTX_new()
        if ctx == ffi.NULL:
            raise MemoryError
        ctx = ffi.gc(ctx, lib.Cryptography_EVP_MD_CTX_free)


        try:
            if copy_from is not None:
                # cpython uses EVP_MD_CTX_copy(...) and calls this from EVP_copy
                if not lib.EVP_MD_CTX_copy_ex(ctx, copy_from):
                    raise ValueError
            else:
                if lib.EVP_DigestInit_ex(ctx, digest_type, ffi.NULL) == 0:
                    raise ValueError(get_errstr())
            object.__setattr__(self, 'ctx', ctx)
        except:
            # no need to gc ctx! 
            raise
        if not usedforsecurity and lib.EVP_MD_CTX_FLAG_NON_FIPS_ALLOW:
            lib.EVP_MD_CTX_set_flags(ctx, lib.EVP_MD_CTX_FLAG_NON_FIPS_ALLOW)
        # End EVPnew

    def digest_type_by_name(self):
        ssl_name = _inverse_name_mapping.get(self.name, self.name)
        c_name = _str_to_ffi_buffer(ssl_name)
        digest_type = lib.EVP_get_digestbyname(c_name)
        if not digest_type:
            raise ValueError("unknown hash function")
        # TODO
        return digest_type

    def __repr__(self):
        return "<%s HASH object at 0x%s>" % (self.name, id(self))

    def update(self, string):
        if isinstance(string, str):
            raise TypeError("Unicode-objects must be encoded before hashing")
        elif isinstance(string, memoryview):
            # issue 2756: ffi.from_buffer() cannot handle memoryviews
            string = string.tobytes()
        buf = ffi.from_buffer(string)
        with self.lock:
            # XXX try to not release the GIL for small requests
            if lib.EVP_DigestUpdate(self.ctx, buf, len(buf)) == 0:
                raise ValueError(get_errstr())

    def copy(self):
        """Return a copy of the hash object."""
        with self.lock:
            return HASH(self.name, copy_from=self.ctx)

    def digest(self):
        """Return the digest value as a string of binary data."""
        return self._digest()

    def hexdigest(self):
        """Return the digest value as a string of hexadecimal digits."""
        digest = self._digest()
        hexdigits = '0123456789abcdef'
        result = []
        for c in digest:
            result.append(hexdigits[(c >> 4) & 0xf])
            result.append(hexdigits[ c       & 0xf])
        return ''.join(result)

    @property
    def block_size(self):
        return lib.EVP_MD_CTX_block_size(self.ctx)

    def _digest(self):
        ctx = lib.Cryptography_EVP_MD_CTX_new()
        if ctx == ffi.NULL:
            raise MemoryError
        try:
            with self.lock:
                if not lib.EVP_MD_CTX_copy_ex(ctx, self.ctx):
                    raise ValueError
            digest_size = self.digest_size
            buf = ffi.new("unsigned char[]", digest_size)
            lib.EVP_DigestFinal_ex(ctx, buf, ffi.NULL)
            return _bytes_with_len(buf, digest_size)
        finally:
            lib.Cryptography_EVP_MD_CTX_free(ctx)


class HASHXOF(HASH):
    pass

class HMAC(HASH):
    pass

_algorithms = ('md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512',
               'sha3_224', 'sha3_256', 'sha3_384', 'sha3_512')

class NameFetcher:
    def __init__(self):
        self.meth_names = []
        self.error = None


def _fetch_names():
    name_fetcher = NameFetcher()
    handle = ffi.new_handle(name_fetcher)
    if lib.OPENSSL_VERSION_NUMBER >= int(0x30000000):
        lib.EVP_MD_do_all_provided(ffi.cast("OSSL_LIB_CTX*", 0),
                                   _openssl_hash_name_mapper, handle)
    else:
        lib.EVP_MD_do_all(_openssl_hash_name_mapper, handle)
    if name_fetcher.error:
        raise name_fetcher.error
    meth_names = name_fetcher.meth_names
    name_fetcher.meth_names = None
    return frozenset(meth_names)

_name_mapping = {
    'blake2s256': 'blake2s',
    'blake2b512': 'blake2b',
    'md5-sha1': 'md5_sha1',
    'sha512-224': 'sha512_224',
    'sha512-256': 'sha512_256',
    }

_inverse_name_mapping = {value: key for key, value in _name_mapping.items()}
    
if lib.OPENSSL_VERSION_NUMBER >= int(0x30000000):
    @ffi.callback("void(EVP_MD*, void*)")
    def _openssl_hash_name_mapper(evp_md, userdata):
        return __openssl_hash_name_mapper(evp_md, userdata)
    
else:
    @ffi.callback("void(EVP_MD*, const char *, const char *, void*)")
    def _openssl_hash_name_mapper(evp_md, from_name, to_name, userdata):
        return __openssl_hash_name_mapper(evp_md, userdata)

def __openssl_hash_name_mapper(evp_md, userdata):
    if not evp_md:
        return
    nid = lib.EVP_MD_nid(evp_md)
    if nid == lib.NID_undef:
        return
    from_name = lib.OBJ_nid2ln(nid)
    lowered = _str_from_buf(from_name).lower().replace('-', '_')
    name = _name_mapping.get(lowered, lowered)
    name_fetcher = ffi.from_handle(userdata)
    name_fetcher.meth_names.append(name)

openssl_md_meth_names = _fetch_names()
del _fetch_names

# shortcut functions
def make_new_hash(name, funcname):
    def new_hash(string=b'', usedforsecurity=True):
        return new(name, string, usedforsecurity=True)
    new_hash.__name__ = funcname
    return builtinify(new_hash)

for _name in _algorithms:
    _newname = 'openssl_%s' % (_name,)
    globals()[_newname] = make_new_hash(_name, _newname)

if hasattr(lib, 'PKCS5_PBKDF2_HMAC'):
    @builtinify
    def pbkdf2_hmac(hash_name, password, salt, iterations, dklen=None):
        if not isinstance(hash_name, str):
            raise TypeError("expected 'str' for name, but got %s" % type(hash_name))
        c_name = _str_to_ffi_buffer(hash_name)
        digest = lib.EVP_get_digestbyname(c_name)
        if digest == ffi.NULL:
            raise ValueError("unsupported hash type")
        if dklen is None:
            dklen = lib.EVP_MD_size(digest)
        if dklen < 1:
            raise ValueError("key length must be greater than 0.")
        if dklen >= sys.maxsize:
            raise OverflowError("key length is too great.")
        if iterations < 1:
            raise ValueError("iteration value must be greater than 0.")
        if iterations >= sys.maxsize:
            raise OverflowError("iteration value is too great.")
        key = ffi.new("unsigned char[]", dklen)
        c_password = ffi.from_buffer(bytes(password))
        c_salt = ffi.from_buffer(bytes(salt))
        r = lib.PKCS5_PBKDF2_HMAC(c_password, len(c_password),
                ffi.cast("unsigned char*",c_salt), len(c_salt),
                iterations, digest, dklen, key)
        if r == 0:
            raise ValueError
        return _bytes_with_len(key, dklen)


def compare_digest(a, b):
    """Return 'a == b'.

This function uses an approach designed to prevent
timing analysis, making it appropriate for cryptography.

a and b must both be of the same type: either str (ASCII only),
or any bytes-like object.

Note: If a and b are of different lengths, or if an error occurs,
a timing attack could theoretically reveal information about the
types and lengths of a and b--but not their values."""
    raise NotImplementedError()


def get_fips_mode():
    """Determine the OpenSSL FIPS mode of operation.

For OpenSSL 3.0.0 and newer it returns the state of the default provider
in the default OSSL context. It's not quite the same as FIPS_mode() but good
enough for unittests.

Effectively any non-zero return value indicates FIPS mode;
values other than 1 may have additional significance."""

    if lib.OPENSSL_VERSION_NUMBER > 0x30000000:
        return lib.EVP_default_properties_is_fips_enabled(ffi.NULL)
    lib.ERR_clear_error()
    result = lib.FIPS_mode()
    if result == 0:
        # If the library was built without support of the FIPS Object Module,
        # then the function will return 0 with an error code of
        # CRYPTO_R_FIPS_MODE_NOT_SUPPORTED (0x0f06d065).
        # But 0 is also a valid result value.
        errcode = lib.ERR_peek_last_error();
        if errcode:
            raise ValueError("could not call FIPS_mode")
    return result

def hmac_digest(key, msg, digest):
    """Single-shot HMAC"""
    raise NotImplementedError()


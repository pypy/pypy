import sys
from _thread import allocate_lock as Lock
from enum import IntEnum as _IntEnum
from functools import cache
from _pypy_openssl import ffi, lib
from _cffi_ssl._stdssl.utility import (_str_to_ffi_buffer, _bytes_with_len,
        _str_from_buf)

try: from __pypy__ import builtinify
except ImportError: builtinify = lambda f: f

class UnsupportedDigestmodError(ValueError):
    pass

class _Py_hash_type(_IntEnum):
    Py_ht_evp = 0            # usedforsecurity=True (default)
    Py_ht_evp_nosecurity = 1 # usedforsecurity=False
    Py_ht_mac = 2           # HMAC
    Py_ht_pbkdf2 = 3        # PKBDF2
globals().update(_Py_hash_type.__members__)

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
        self.ctx = ffi.NULL
        self.ctx = ffi.NULL
        self.name = str(name).lower()
        digest_type = py_digest_by_name(self.name,
                         Py_ht_evp if usedforsecurity else Py_ht_evp_nosecurity)
        self.digest_size = lib.EVP_MD_size(digest_type)

        # Allocate a lock for each HASH object.
        # An optimization would be to not release the GIL on small requests,
        # and use a custom lock only when needed.
        self.lock = Lock()

        self._init_ctx(copy_from, digest_type)
        if not usedforsecurity and lib.EVP_MD_CTX_FLAG_NON_FIPS_ALLOW:
            lib.EVP_MD_CTX_set_flags(self.ctx, lib.EVP_MD_CTX_FLAG_NON_FIPS_ALLOW)

    def _init_ctx(self, copy_from, digest_type):
        # this is EVPnew in _hashopenssl.c

        ctx = lib.EVP_MD_CTX_new()
        if ctx == ffi.NULL:
            raise MemoryError
        ctx = ffi.gc(ctx, lib.EVP_MD_CTX_free)

        try:
            if copy_from is not None:
                # cpython uses EVP_MD_CTX_copy(...) and calls this from EVP_copy
                if not lib.EVP_MD_CTX_copy_ex(ctx, copy_from):
                    raise ValueError
            else:
                if lib.EVP_DigestInit_ex(ctx, digest_type, ffi.NULL) == 0:
                    raise ValueError(get_errstr())
            self.ctx = ctx
        except:
            # no need to gc ctx! 
            raise

    def digest_type_by_name(self):
        ssl_name = _inverse_name_mapping.get(self.name, self.name)
        c_name = _str_to_ffi_buffer(ssl_name)
        digest_type = lib.EVP_get_digestbyname(c_name)
        if not digest_type:
            raise ValueError("unknown hash function")
        # TODO
        return digest_type

    def __repr__(self):
        return "<%s %s object at 0x%s>" % (self.name, type(self), id(self))

    def update(self, string):
        if isinstance(string, str):
            raise TypeError("Unicode-objects must be encoded before hashing")
        elif isinstance(string, memoryview):
            # issue 2756: ffi.from_buffer() cannot handle memoryviews
            string = string.tobytes()
        buf = ffi.from_buffer(string)
        self._update(buf)

    def _update(self, buf):
        with self.lock:
            # XXX try to not release the GIL for small requests
            if lib.EVP_DigestUpdate(self.ctx, buf, len(buf)) == 0:
                raise ValueError(get_errstr())

    def copy(self):
        """Return a copy of the hash object."""
        with self.lock:
            return type(self)(self.name, copy_from=self.ctx)

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
        # in _hashopenss.c this is EVP_hexdigest_impl
        ctx = lib.EVP_MD_CTX_new()
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
            lib.EVP_MD_CTX_free(ctx)


class HASHXOF(HASH):
    pass


class HMAC(HASH):
    def __init__(self, name=None, copy_from=None, usedforsecurity=True):
        HASH.__init__(self, name=name, copy_from=copy_from, usedforsecurity=usedforsecurity)
        digest_type = py_digest_by_name(self.name,
                         Py_ht_evp if usedforsecurity else Py_ht_evp_nosecurity)
        self.digest_size = lib.EVP_MD_size(digest_type)
        self._name = name
        self.name = f"hmac-{name}"

    @property
    def block_size(self):
        md = lib.HMAC_CTX_get_md(self.ctx)
        if not md:
            raise ValueError("could not get EVP_MD from HMAC_CTX")
        return lib.EVP_MD_block_size(md)

    def _digest(self):
        # _hmac_digest in _hashopenssl.c
        temp_ctx = lib.HMAC_CTX_new()
        if temp_ctx == ffi.NULL:
            raise MemoryError
        try:
            with self.lock:
                if not lib.HMAC_CTX_copy(temp_ctx, self.ctx):
                    raise ValueError
            digest_size = self.digest_size
            buf = ffi.new("unsigned char[]", digest_size)
            lib.HMAC_Final(temp_ctx, buf, ffi.NULL)
            return _bytes_with_len(buf, digest_size)
        finally:
            lib.HMAC_CTX_free(temp_ctx)

    def _init_ctx(self, copy_from, digest_type):
        ctx = lib.HMAC_CTX_new()
        if ctx == ffi.NULL:
            raise MemoryError
        ctx = ffi.gc(ctx, lib.HMAC_CTX_free)

        try:
            if copy_from is not None:
                if not lib.HMAC_CTX_copy(ctx, copy_from):
                    raise ValueError
            else:
                if lib.HMAC_Init_ex(ctx, _str_to_ffi_buffer(""), 0, digest_type, ffi.NULL) == 0:
                    raise ValueError(get_errstr())
            self.ctx = ctx
        except:
            # no need to gc ctx! 
            raise

    def _update(self, buf):
        with self.lock:
            # XXX try to not release the GIL for small requests
            if lib.HMAC_Update(self.ctx, buf, len(buf)) == 0:
                raise ValueError(get_errstr())

    def copy(self):
        """Return a copy of the hash object."""
        with self.lock:
            return type(self)(self._name, copy_from=self.ctx)


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
    'sha3-224': 'sha3_224',
    'sha3-256': 'sha3_256',
    'sha3-384': 'sha3_384',
    'sha3-512': 'sha3_512',
    }

_inverse_name_mapping = {value: key for key, value in _name_mapping.items()}
    
if lib.OPENSSL_VERSION_NUMBER >= int(0x30000000):
    @ffi.callback("void(EVP_MD*, void*)")
    def _openssl_hash_name_mapper(evp_md, userdata):
        return __openssl_hash_name_mapper(evp_md, userdata)

    def PY_EVP_MD_fetch(algorithm, properties):
        return lib.EVP_MD_fetch(ffi.NULL, algorithm, properties) 
    def PY_EVP_MD_free(md):
        lib.EVP_MD_free(md)
else:
    @ffi.callback("void(EVP_MD*, const char *, const char *, void*)")
    def _openssl_hash_name_mapper(evp_md, from_name, to_name, userdata):
        return __openssl_hash_name_mapper(evp_md, userdata)

    def PY_EVP_MD_fetch(algorithm, properties):
        return lib.EVP_get_digestbyname(algorithm) 
    def PY_EVP_MD_free(md):
        pass

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

# Not used internally, exposed in the module
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
            raise UnsupportedDigestmodError("unsupported hash type")
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

@builtinify
def scrypt(password, *, salt, n=None, r=None, p=None, maxmem=0, dklen=64):
    int_max = (2 ** 31) - 1
    if len(password) > int_max:
        raise OverflowError("password is too long")
    if len(salt) > int_max:
        raise OverflowError("salt is too long")
    def asint(val, name):
        try:
            return int(val)
        except TypeError:
            raise TypeError("%s is required and must be a unsigned int" % name)
    n = asint(n, 'n')
    if n < 2 or (n & (n - 1)):
        raise TypeError("n must be a power of 2.")
    r = asint(r, "r")
    p = asint(p, "p")
    if maxmem < 0 or  maxmem > int_max:
        # OpenSSL 1.1.0 restricts maxmem to 32 MiB. It may change in the
        #   future. The maxmem constant is private to OpenSSL.
        raise ValueError("maxmem must be positive and smaller than %d" % int_max)
    if dklen <= 0 or  dklen > int_max:
        raise ValueError("dklen must be greater than 0 and smaller than %d" % int_max)
    # let OpenSSL validate the rest
    void_p = ffi.cast("char *", 0)
    retval = lib.EVP_PBE_scrypt(void_p, 0, void_p, 0, n, r, p, maxmem, void_p, 0)
    if not retval:
        ValueError("Invalid parameter combination for n, r, p, maxmem.")
    key = ffi.new("unsigned char[]", dklen)
    c_password = ffi.from_buffer(password)
    c_salt = ffi.from_buffer(salt)
    reval = lib.EVP_PBE_scrypt(c_password, len(password), c_salt, len(salt),
                               n, r, p, maxmem, key, dklen)
    if not retval:
        raise ValueError()
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

    res = True
    if isinstance(a, str) and isinstance(b, str):
        # ascii unicode str
        try:
            c_a = ffi.from_buffer(a.encode("ascii"))
            c_b = ffi.from_buffer(b.encode("ascii"))
        except Exception:
            raise TypeError("comparing strings with non-ASCII characters is "
                            "not supported")
        length_a = len(a)
        length_b = len(b)
    # fallback to buffer interface for bytes, bytearray and other
    else:
        try:
            b_a = memoryview(a)
            b_b = memoryview(b)
        except Exception:
            raise TypeError("unsupported operand types(s) or combination of "
                            f"types: '{type(a)}' and '{type(b)}'")
        if b_a.ndim > 1:
            raise BufferError("Buffer must be a single dimension")
        if b_b.ndim > 1:
            raise BufferError("Buffer must be a single dimension")
        c_a = ffi.from_buffer(b_a.tobytes())
        c_b = ffi.from_buffer(b_b.tobytes())
        length_a = len(b_a)
        length_b = len(b_b)
    if length_a != length_b:
        res = False
    return (lib.CRYPTO_memcmp(c_a, c_b, length_b) == 0) and res


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


def py_digest_by_name(name, py_ht):
    """Get EVP_MD by HID and purpose"""

    ssl_name = _inverse_name_mapping.get(name, name)
    c_name = _str_to_ffi_buffer(ssl_name)
    if py_ht in (Py_ht_evp, Py_ht_mac, Py_ht_pbkdf2):
        digest = PY_EVP_MD_fetch(c_name, ffi.NULL)
    elif py_ht == Py_ht_evp_nosecurity:
        digest = PY_EVP_MD_fetch(c_name, _str_to_ffi_buffer("-fips"))
    if not digest:
        raise UnsupportedDigestmodError(f"unsupported hash type {name}")
    ffi.gc(digest, PY_EVP_MD_free)
    return digest 
    

def py_digest_by_digestmod(digestmod):
    """Get digest EVP from object"""
    if isinstance(digestmod, str):
        name_obj = digestmod
    else:
        name_obj = digestmod.__name__
        if name_obj.startswith('openssl_'):
            name_obj = name_obj[8:]
    if not name_obj:
        raise UnsupportedDigestmodError(f"Unsupported digestemod {digestmod}")
    return py_digest_by_name(name_obj, Py_ht_mac), name_obj


def hmac_digest(key, msg, digest):
    """Single-shot HMAC"""
    if len(key) > sys.maxsize:
        raise OverflowError("key is too long")
    if len(msg) > sys.maxsize:
        raise OverflowError("msg is too long")
    evp, _ = py_digest_by_digestmod(digest)
    md = ffi.new("unsigned char[]", lib.EVP_MAX_MD_SIZE)
    md_len = ffi.new("unsigned int[1]", [0])
    result = lib.HMAC(evp, _str_to_ffi_buffer(key), len(key),
                      msg, len(msg), md, md_len)
    
    if not result:
        raise ValueError("could not call lib.HMAC")
    return _bytes_with_len(md, md_len[0])

def hmac_new(key, msg=b"", digestmod=None):
    """Return a new HMAC object"""
    if len(key) > sys.maxsize:
        raise OverflowError("key is too long")
    if not digestmod:
        raise TypeError("Missing required parameter 'digestmod'")
    # in cpython this is called with an enum arg that is always Py_ht_mac
    digest, digestmod =  py_digest_by_digestmod(digestmod)
    ctx = lib.HMAC_CTX_new()
    if not ctx:
        raise ValueError("Could not allocate HMAC_CTX")
    r = lib.HMAC_Init_ex(ctx, _str_to_ffi_buffer(key), len(key), digest, ffi.NULL)
    if r == 0:
        raise ValueError("Could not initialize HMAC_CTX")
    self = HMAC(digestmod)
    self.ctx = ctx
    if msg:
        # _hmac_update
        view = memoryview(msg)
        if len(view) > 2048:  # HASHLIB_GIL_MINSIZE
            with self.lock:
                result = lib.HMAC_Update(ctx, _str_to_ffi_buffer(msg), len(view))
        else:
            result = lib.HMAC_Update(ctx, _str_to_ffi_buffer(msg), len(view))
        if r == 0:
            raise ValueError(f"could not hash msg '{msg}'")
    return self

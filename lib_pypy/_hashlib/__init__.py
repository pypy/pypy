import sys
from threading import Lock
from _pypy_openssl import ffi, lib
from _cffi_ssl._stdssl.utility import (_str_to_ffi_buffer, _bytes_with_len,
        _str_from_buf)

try: from __pypy__ import builtinify
except ImportError: builtinify = lambda f: f

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


def new(name, string=b''):
    h = HASH(name)
    h.update(string)
    return h

class HASH(object):

    def __init__(self, name, copy_from=None):
        self.ctx = ffi.NULL
        try:
            self.name = name.lower().replace('-', '_')
        except AttributeError:
            raise TypeError('In HASH(name), name must be a string')
        digest_type = self.digest_type_by_name()
        self.digest_size = lib.EVP_MD_size(digest_type)

        # Allocate a lock for each HASH object.
        # An optimization would be to not release the GIL on small requests,
        # and use a custom lock only when needed.
        self.lock = Lock()

        ctx = lib.Cryptography_EVP_MD_CTX_new()
        if ctx == ffi.NULL:
            raise MemoryError
        ctx = ffi.gc(ctx, lib.Cryptography_EVP_MD_CTX_free)

        try:
            if copy_from is not None:
                # cpython uses EVP_MD_CTX_copy(...)
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

algorithms = ('md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512')

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
    'shake128': 'shake_128',
    'shake256': 'shake_256',
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
    name_fetcher = ffi.from_handle(userdata)
    from_name = lib.OBJ_nid2ln(nid)
    lowered = _str_from_buf(from_name).lower().replace('-', '_')
    name = _name_mapping.get(lowered, lowered)
    name_fetcher.meth_names.append(name)

openssl_md_meth_names = _fetch_names()
del _fetch_names

# shortcut functions
def make_new_hash(name, funcname):
    def new_hash(string=b''):
        return new(name, string)
    new_hash.__name__ = funcname
    return builtinify(new_hash)

for _name in algorithms:
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
        buf = ffi.new("unsigned char[]", dklen)
        c_password = ffi.from_buffer(bytes(password))
        c_salt = ffi.from_buffer(bytes(salt))
        r = lib.PKCS5_PBKDF2_HMAC(c_password, len(c_password),
                ffi.cast("unsigned char*",c_salt), len(c_salt),
                iterations, digest, dklen, buf)
        if r == 0:
            raise ValueError
        return _bytes_with_len(buf, dklen)

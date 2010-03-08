from ctypes import *
import ctypes.util

# load the platform-specific cache made by running hashlib.ctc.py
from ctypes_config_cache._hashlib_cache import *

# Note: OpenSSL on OS X only provides md5 and sha1
libpath = ctypes.util.find_library('ssl')
if not libpath:
    raise ImportError('could not find OpenSSL library')
lib = CDLL(libpath) # Linux, OS X
lib.EVP_get_digestbyname.restype = c_void_p
lib.EVP_DigestInit.argtypes = [c_void_p, c_void_p]

def bufferstr(x):
    if isinstance(x, basestring):
        return str(x)
    else:
        return buffer(x)[:]

def patch_fields(fields):
    res = []
    for k, v in fields:
        if k == 'digest':
            res.append((k, POINTER(EVP_MD)))
        else:
            res.append((k, v))
    return res

class EVP_MD_CTX(Structure):
    _fields_ = patch_fields(EVP_MD_CTX._fields_)

# OpenSSL initialization
lib.OpenSSL_add_all_digests()

# taken from evp.h, max size is 512 bit, 64 chars
lib.EVP_MAX_MD_SIZE = 64

class hash(object):
    """
    A hash represents the object used to calculate a checksum of a
    string of information.
    
    Methods:
    
    update() -- updates the current digest with an additional string
    digest() -- return the current digest value
    hexdigest() -- return the current digest as a string of hexadecimal digits
    copy() -- return a copy of the current hash object
    
    Attributes:
    
    name -- the hash algorithm being used by this object
    digest_size -- number of bytes in this hashes output
    """
    def __init__(self, obj, name):
        self.name = name # part of API
        #print 'obj is ', obj
        if isinstance(obj, EVP_MD_CTX):
            self._obj = obj.digest
        else:
            self._obj = obj
    
    def __repr__(self):
        # format is not the same as in C module
        return "<%s HASH object>" % (self.name)
    
    def copy(self):
        "Return a copy of the hash object."
        ctxnew = EVP_MD_CTX()
        lib.EVP_MD_CTX_copy(byref(ctxnew), byref(self._obj))
        return hash(ctxnew, self.name)
    
    def hexdigest(self):
        "Return the digest value as a string of hexadecimal digits."
        dig = self.digest()
        a = []
        for x in dig:
            a.append('%.2x' % ord(x))
        #print '\n--- %r \n' % ''.join(a)
        return ''.join(a)
    
    def digest(self):
        "Return the digest value as a string of binary data."
        tmpctx = self.copy()
        digest_size = tmpctx.digest_size
        dig = create_string_buffer(lib.EVP_MAX_MD_SIZE)
        lib.EVP_DigestFinal(byref(tmpctx._obj), dig, None)
        lib.EVP_MD_CTX_cleanup(byref(tmpctx._obj))
        return dig.raw[:digest_size]
    
    def digest_size(self):
        # XXX This isn't the nicest way, but the EVP_MD_size OpenSSL function
        # XXX is defined as a C macro on OS X and would be significantly 
        # XXX harder to implement in another way.
        # Values are digest sizes in bytes
        return {
            'md5': 16,
            'sha1': 20,
            'sha224': 28,
            'sha256': 32,
            'sha384': 48,
            'sha512': 64,
            }.get(self.name, 0)
    digest_size = property(digest_size, None, None) # PEP 247
    digestsize = digest_size # deprecated, was once defined by sha module
    
    def block_size(self):
        # XXX This isn't the nicest way, but the EVP_MD_CTX_block_size OpenSSL function
        # XXX is defined as a C macro on some systems and would be significantly 
        # XXX harder to implement in another way.
        return {
            'md5':     64,
            'sha1':    64,
            'sha224':  64,
            'sha256':  64,
            'sha384': 128,
            'sha512': 128,
            }.get(self.name, 0)
    block_size = property(block_size, None, None)
    
    def update(self, string):
        "Update this hash object's state with the provided string."
        string = bufferstr(string)
        lib.EVP_DigestUpdate(byref(self._obj), c_char_p(string), c_uint(len(string)))

def new(name, string=''):
    """
    Return a new hash object using the named algorithm.
    An optional string argument may be provided and will be
    automatically hashed.
    
    The MD5 and SHA1 algorithms are always supported.
    """
    digest = lib.EVP_get_digestbyname(c_char_p(name))
    
    if not isinstance(name, str):
        raise TypeError("name must be a string")
    if not digest:
        raise ValueError("unknown hash function")
    
    ctx = EVP_MD_CTX()
    lib.EVP_DigestInit(pointer(ctx), digest)

    h = hash(ctx.digest, name)
    if string:
        h.update(string)
    return hash(ctx, name)

# shortcut functions
def openssl_md5(string=''):
    return new('md5', string)

def openssl_sha1(string=''):
    return new('sha1', string)

def openssl_sha224(string=''):
    return new('sha224', string)

def openssl_sha256(string=''):
    return new('sha256', string)

def openssl_sha384(string=''):
    return new('sha384', string)

def openssl_sha512(string=''):
    return new('sha512', string)


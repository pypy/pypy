# $Id: hashlib.py 52533 2006-10-29 18:01:12Z georg.brandl $
#
#  Copyright (C) 2005   Gregory P. Smith (greg@electricrain.com)
#  Licensed to PSF under a Contributor Agreement.
#

__doc__ = """hashlib module - A common interface to many hash functions.

new(name, string='') - returns a new hash object implementing the
                       given hash function; initializing the hash
                       using the given string data.

Named constructor functions are also available, these are much faster
than using new():

md5(), sha1(), sha224(), sha256(), sha384(), and sha512()

More algorithms may be available on your platform but the above are
guaranteed to exist.

Choose your hash function wisely.  Some have known collision weaknesses.
sha384 and sha512 will be slow on 32 bit platforms.

Hash objects have these methods:
 - update(arg): Update the hash object with the string arg. Repeated calls
                are equivalent to a single call with the concatenation of all
                the arguments.
 - digest():    Return the digest of the strings passed to the update() method
                so far. This may contain non-ASCII characters, including
                NUL bytes.
 - hexdigest(): Like digest() except the digest is returned as a string of
                double length, containing only hexadecimal digits.
 - copy():      Return a copy (clone) of the hash object. This can be used to
                efficiently compute the digests of strings that share a common
                initial substring.

For example, to obtain the digest of the string 'Nobody inspects the
spammish repetition':

    >>> import hashlib
    >>> m = hashlib.md5()
    >>> m.update("Nobody inspects")
    >>> m.update(" the spammish repetition")
    >>> m.digest()
    '\xbbd\x9c\x83\xdd\x1e\xa5\xc9\xd9\xde\xc9\xa1\x8d\xf0\xff\xe9'

More condensed:

    >>> hashlib.sha224("Nobody inspects the spammish repetition").hexdigest()
    'a4337bc45a8fc544c03f52dc550cd6e1e87021bc896588bd79e901e2'

"""
import sys
try:
    import _hashlib
except ImportError:
    _hashlib = None

def __hash_new(name, string=''):
    """new(name, string='') - Return a new hashing object using the named algorithm;
    optionally initialized with a string.
    """
    try:
        new = __byname[name]
    except KeyError:
        raise ValueError("unsupported hash type")
    return new(string)

new = __hash_new

# ____________________________________________________________

__byname = {}

def __use_openssl_funcs():
    # use the wrapper of the C implementation
    sslprefix = 'openssl_'
    for opensslfuncname, func in vars(_hashlib).items():
        if not opensslfuncname.startswith(sslprefix):
            continue
        funcname = opensslfuncname[len(sslprefix):]
        try:
            # try them all, some may not work due to the OpenSSL
            # version not supporting that algorithm.
            func() 
            # Use the C function directly (very fast, but with ctypes overhead)
            __byname[funcname] = func
        except ValueError:
            pass

def __use_builtin_funcs():
    # look up the built-in versions (written in Python or RPython),
    # and use the fastest one:
    #  1. the one in RPython
    #  2. the one from openssl (slower due to ctypes calling overhead)
    #  3. the one in pure Python
    if 'sha1' not in __byname or 'sha' in sys.builtin_module_names:
        import sha
        __byname['sha1'] = sha.new
    if 'md5' not in __byname or 'md5' in sys.builtin_module_names:
        import md5
        __byname['md5'] = md5.new
    if 'sha256' not in __byname:
        import _sha256
        __byname['sha256'] = _sha256.sha256
    if 'sha224' not in __byname:
        import _sha256
        __byname['sha224'] = _sha256.sha224
    if 'sha512' not in __byname:
        import _sha512
        __byname['sha512'] = _sha512.sha512
    if 'sha384' not in __byname:
        import _sha512
        __byname['sha384'] = _sha512.sha384

def __export_funcs():
    for key, value in __byname.items():
        globals()[key] = __byname[key.upper()] = value

if _hashlib:
    __use_openssl_funcs()
__use_builtin_funcs()
__export_funcs()

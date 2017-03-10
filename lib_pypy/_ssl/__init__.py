from _cffi_ssl._stdssl import (_PROTOCOL_NAMES, _OPENSSL_API_VERSION,
        _test_decode_cert, _SSLContext)
from _cffi_ssl._stdssl import *


try: from __pypy__ import builtinify
except ImportError: builtinify = lambda f: f

RAND_add          = builtinify(RAND_add)
RAND_bytes        = builtinify(RAND_bytes)
RAND_egd          = builtinify(RAND_egd)
RAND_pseudo_bytes = builtinify(RAND_pseudo_bytes)

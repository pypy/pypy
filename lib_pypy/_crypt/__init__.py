"""
CFFI based implementation of the _crypt module
"""

import sys
import cffi
import thread
_lock = thread.allocate_lock()

try: from __pypy__ import builtinify
except ImportError: builtinify = lambda f: f


ffi = cffi.FFI()
ffi.cdef('char *crypt(char *word, char *salt);')

try:
    lib = ffi.dlopen('crypt')
except OSError:
    raise ImportError('crypt not available')


@builtinify
def crypt(word, salt):
    with _lock:
        if isinstance(word, str):
            word = word.encode('ascii')
        if isinstance(salt, str):
            salt = salt.encode('ascii')
        res = lib.crypt(word, salt)
        if not res:
            return None
        return ffi.string(res)

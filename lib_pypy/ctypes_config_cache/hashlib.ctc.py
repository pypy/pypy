"""
'ctypes_configure' source for _hashlib.py.
Run this to rebuild _hashlib_cache.py.
"""

import autopath
from ctypes import *
from ctypes_configure import configure, dumpcache


class CConfig:
    _compilation_info_ = configure.ExternalCompilationInfo(
        includes=['openssl/evp.h'],
        )
    EVP_MD = configure.Struct('EVP_MD',
                              [])
    EVP_MD_CTX = configure.Struct('EVP_MD_CTX',
                                  [('digest', c_void_p)])

config = configure.configure(CConfig)
dumpcache.dumpcache(__file__, '_hashlib_cache.py', config)

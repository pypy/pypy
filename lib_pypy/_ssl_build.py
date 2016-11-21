import sys
from _cffi_ssl import _cffi_src
sys.modules['_cffi_src'] = _cffi_src
#
from _cffi_ssl._cffi_src.build_openssl import (build_ffi_for_binding,
        _get_openssl_libraries, extra_link_args, compiler_type)

ffi = build_ffi_for_binding(
    module_name="_pypy_openssl",
    module_prefix="_cffi_src.openssl.",
    modules=[
        # This goes first so we can define some cryptography-wide symbols.
        "cryptography",

        "aes",
        "asn1",
        "bignum",
        "bio",
        "cmac",
        "cms",
        "conf",
        "crypto",
        "dh",
        "dsa",
        "ec",
        "ecdh",
        "ecdsa",
        "engine",
        "err",
        "evp",
        "hmac",
        "nid",
        "objects",
        "ocsp",
        "opensslv",
        "pem",
        "pkcs12",
        "rand",
        "rsa",
        "ssl",
        "x509",
        "x509name",
        "x509v3",
        "x509_vfy",
        "pkcs7",
        "callbacks",
    ],
    libraries=_get_openssl_libraries(sys.platform),
    extra_link_args=extra_link_args(compiler_type()),
)

if __name__ == '__main__':
    ffi.compile()

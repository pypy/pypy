import os
import sys
from _cffi_ssl import _cffi_src
sys.modules['_cffi_src'] = _cffi_src
#
from _cffi_ssl._cffi_src.build_openssl import (build_ffi_for_binding,
        _get_openssl_libraries, extra_link_args, compiler_type)

if sys.platform == "win32":
    pypy_win32_extra = ["pypy_win32_extra"]
else:
    pypy_win32_extra = []

libraries=_get_openssl_libraries(sys.platform)
ffi = build_ffi_for_binding(
    module_name="_pypy_openssl",
    module_prefix="_cffi_src.openssl.",
    modules=[
        # This goes first so we can define some cryptography-wide symbols.
        "cryptography",

        # Provider comes early as well so we define OSSL_LIB_CTX
        "provider",
        "asn1",
        "bignum",
        "bio",
        "cmac",
        "crypto",
        "ct",
        "dh",
        "dsa",
        "ec",
        "ecdh",
        "ecdsa",
        "engine",
        "err",
        "evp",
        "fips",
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
    ] + pypy_win32_extra,
    libraries=libraries,
    extra_link_args=extra_link_args(compiler_type()),
)

if __name__ == '__main__':
    ffi.compile(verbose=True)
    if sys.platform == 'win32' and "PYPY_PACKAGE_NO_DLLS" not in os.environ:
        # copy dlls from externals to the pwd
        # maybe we should link to libraries instead of the dlls
        # to avoid this mess
        import os, glob, shutil
        path_parts = os.environ['PATH'].split(';')
        candidates = [x for x in path_parts if 'externals' in x]

        def copy_from_path(dll):
            for c in candidates:
                files = glob.glob(os.path.join(c, dll + '*.dll'))
                if files:
                    for fname in files:
                        print('copying', fname)
                        shutil.copy(fname, '.')
                    break
                else:
                    print("not copying %s from %s", (dll, c))

        if candidates:
            for lib in libraries:
                copy_from_path(lib)
        else:
            print('no "externals" on PATH, not copying %s, expect trouble', libraries)

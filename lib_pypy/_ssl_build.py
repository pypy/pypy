import sys
from openssl import _cffi_src
sys.modules['_cffi_src'] = _cffi_src
#
from openssl._cffi_src.build_openssl import ffi

if __name__ == '__main__':
    ffi.compile()

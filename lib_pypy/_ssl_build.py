import sys
from _cffi_ssl import _cffi_src
sys.modules['_cffi_src'] = _cffi_src
#
from _cffi_ssl._cffi_src.build_openssl import ffi

if __name__ == '__main__':
    ffi.compile()

import os
import platform

from cffi import FFI
ffi = FFI()

def main():
    if platform.system() != 'Darwin':
        return

    release, _, _ = platform.mac_ver()
    release = tuple(map(int, release.split('.')))
    if release < (10, 16):
        return

    ffi.cdef('bool _dyld_shared_cache_contains_path(const char* path);')
    ffi.set_source('_ctypes_cffi', '#include <mach-o/dyld.h>')

    os.chdir(os.path.dirname(__file__))
    ffi.compile()

if __name__ == '__main__':
    main()

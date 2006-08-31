import mmap
from pypy.module.mmap import interp_mmap
from ctypes import c_void_p

libcmmap   = interp_mmap.libc.mmap
libcmunmap = interp_mmap.libc.munmap

def alloc(map_size):
    flags = mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS
    prot = mmap.PROT_EXEC | mmap.PROT_READ | mmap.PROT_WRITE
    res = libcmmap(c_void_p(), map_size, prot, flags, -1, 0)
    if not res:
        raise MemoryError
    return res

free = libcmunmap

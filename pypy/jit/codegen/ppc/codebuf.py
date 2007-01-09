import pypy.rpython.rctypes.implementation  # register rctypes types
from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.rctypes.tool.libc import libc
from ctypes import POINTER, cast, c_void_p, c_int, c_char

class CConfig:
    _includes_ = ("sys/types.h", "sys/mman.h")
    size_t = ctypes_platform.SimpleType("size_t", c_int)
    off_t = ctypes_platform.SimpleType("off_t", c_int)

    MAP_PRIVATE   = ctypes_platform.DefinedConstantInteger("MAP_PRIVATE")
    MAP_ANON      = ctypes_platform.DefinedConstantInteger("MAP_ANON")
    MAP_ANONYMOUS = ctypes_platform.DefinedConstantInteger("MAP_ANONYMOUS")
    PROT_READ     = ctypes_platform.DefinedConstantInteger("PROT_READ")
    PROT_WRITE    = ctypes_platform.DefinedConstantInteger("PROT_WRITE")
    PROT_EXEC     = ctypes_platform.DefinedConstantInteger("PROT_EXEC")

globals().update(ctypes_platform.configure(CConfig))
if MAP_ANONYMOUS is None:
    MAP_ANONYMOUS = MAP_ANON
    assert MAP_ANONYMOUS is not None
del MAP_ANON

# ____________________________________________________________

PTR = POINTER(c_char)    # cannot use c_void_p as return value of functions :-(

mmap_ = libc.mmap
mmap_.argtypes = [PTR, size_t, c_int, c_int, c_int, off_t]
mmap_.restype = PTR
mmap_.includes = ("sys/mman.h",)
munmap_ = libc.munmap
munmap_.argtypes = [PTR, size_t]
munmap_.restype = c_int
munmap_.includes = ("sys/mman.h",)

def alloc(map_size):
    flags = MAP_PRIVATE | MAP_ANONYMOUS
    prot = PROT_EXEC | PROT_READ | PROT_WRITE
    res = mmap_(PTR(), map_size, prot, flags, -1, 0)
    if not res:
        raise MemoryError
    return res

free = munmap_

class CodeBlockOverflow(Exception):
    pass

class MachineCodeBlock:

    def __init__(self, _data, _size, _pos):
        self._data = _data
        self._size = _size
        self._pos = _pos

    def write(self, data):
        p = self._pos
        if p >= self._size:
            raise CodeBlockOverflow
        self._data.contents[p] = data
        self._pos = p + 1

    def getpos(self):
        return self._pos

    def setpos(self, _pos):
        self._pos = _pos

    def tell(self):
        baseaddr = cast(self._data, c_void_p).value
        return baseaddr + self._pos * 4

    def reserve(self, _size):
        r = MachineCodeBlock(self._data, self._pos + _size, self._pos)
        for i in range(_size):
            self.write(0)
        return r

class ExistingCodeBlock(MachineCodeBlock):
    def __init__(self, start, end):
        self._size = (end-start)/4
        p = c_void_p(start)
        self._data = cast(p, POINTER(c_int * self._size))
        self._pos = 0

class OwningMachineCodeBlock(MachineCodeBlock):
    def __del__(self):
        free(cast(self._data, PTR), self._size * 4)

def new_block(size_in_bytes):
    assert size_in_bytes % 4 == 0
    res = alloc(size_in_bytes)
    return OwningMachineCodeBlock(
        cast(res, POINTER(c_int * (size_in_bytes / 4))),
        size_in_bytes/4,
        0)

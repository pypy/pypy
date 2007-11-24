from ctypes import POINTER, cast, c_void_p, c_int, c_char
from pypy.jit.codegen.i386 import codebuf_posix

def alloc(map_size):
    flags = codebuf_posix.MAP_PRIVATE | codebuf_posix.MAP_ANONYMOUS
    prot = codebuf_posix.PROT_EXEC | codebuf_posix.PROT_READ | codebuf_posix.PROT_WRITE
    res = codebuf_posix.mmap_(PTR(), map_size, prot, flags, -1, 0)
    if not res:
        raise MemoryError
    return res

free = codebuf_posix.munmap_

class CodeBlockOverflow(Exception):
    pass

class MachineCodeBlock:

    def __init__(self, _data, _size, _pos):
        self._size = _size
        self._data = _data
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
        assert _pos >=0
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
        _size = (end-start)/4
        _data = cast(c_void_p(start), POINTER(c_int * _size))
        MachineCodeBlock.__init__(self, _data, _size, 0)

class OwningMachineCodeBlock(MachineCodeBlock):
    def __init__(self, size_in_bytes):
        assert size_in_bytes % 4 == 0
        res = alloc(size_in_bytes)
        _size = size_in_bytes/4
        _data = cast(res, POINTER(c_int * _size))
        MachineCodeBlock.__init__(self, _data, _size, 0)

    def __del__(self):
        free(cast(self._data, PTR), self._size * 4)

# ------------------------------------------------------------

class LLTypeMachineCodeBlock(MachineCodeBlock):
    class State:
        pass
    state = State()
    state.base = 1

    def __init__(self, map_size):
        self._size = map_size/4
        self._pos = 0
        self._base = LLTypeMachineCodeBlock.state.base
        LLTypeMachineCodeBlock.state.base += 2 * map_size

    def write(self, data):
        if self._pos + 1 > self._size:
            raise CodeBlockOverflow
        self._pos += 1

    def tell(self):
        return self._base + 4 * self._pos

    def reserve(self, _size):
        return LLTypeMachineCodeBlock(_size)

class LLTypeExistingCodeBlock(LLTypeMachineCodeBlock):
    def __init__(self, start, end):
        _size = (end-start)
        LLTypeMachineCodeBlock.__init__(self, _size)

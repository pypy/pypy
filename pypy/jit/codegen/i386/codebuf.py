import os
from ctypes import *
from ri386 import AbstractCodeBuilder


modname = 'pypy.jit.codegen.i386.codebuf_' + os.name
memhandler = __import__(modname, globals(), locals(), ['__doc__'])


class CodeBlockOverflow(Exception):
    pass

class MachineCodeBlock(AbstractCodeBuilder):

    def __init__(self, map_size):
        res = memhandler.alloc(map_size)
        self._data = cast(res, POINTER(c_char * map_size))
        self._size = map_size
        self._pos = 0

    def write(self, data):
         p = self._pos
         if p + len(data) > self._size:
             raise CodeBlockOverflow
         for c in data:
             self._data.contents[p] = c
             p += 1
         self._pos = p

    def tell(self):
        baseaddr = cast(self._data, c_void_p).value
        return baseaddr + self._pos

    def __del__(self):
        memhandler.free(cast(self._data, c_void_p), self._size)

    def execute(self, arg1, arg2):
        fnptr = cast(self._data, binaryfn)
        return fnptr(arg1, arg2)

binaryfn = CFUNCTYPE(c_int, c_int, c_int)    # for testing

# ____________________________________________________________

from pypy.rpython.lltypesystem import lltype

BUF = lltype.GcArray(lltype.Char)

class LLTypeMachineCodeBlock(AbstractCodeBuilder):
    # for testing only

    class State:
        pass
    state = State()
    state.base = 1

    def __init__(self, map_size):
        self._size = map_size
        self._pos = 0
        self._data = lltype.malloc(BUF, map_size)
        self._base = LLTypeMachineCodeBlock.state.base
        LLTypeMachineCodeBlock.state.base += 2 * map_size

    def write(self, data):
        p = self._pos
        if p + len(data) > self._size:
            raise CodeBlockOverflow
        for c in data:
            self._data[p] = c
            p += 1
        self._pos = p

    def tell(self):
        return self._base + 2 * self._pos

import os
from ctypes import POINTER, cast, c_char, c_void_p, CFUNCTYPE, c_int
from ri386 import I386CodeBuilder

# Set this to enable/disable the CODE_DUMP stdout lines
CODE_DUMP = False

# ____________________________________________________________


modname = 'pypy.jit.codegen.i386.codebuf_' + os.name
memhandler = __import__(modname, globals(), locals(), ['__doc__'])

PTR = memhandler.PTR


class CodeBlockOverflow(Exception):
    pass

class InMemoryCodeBuilder(I386CodeBuilder):
    _last_dump_start = 0

    def __init__(self, start, end):
        map_size = end - start
        res = c_void_p(start)
        data = cast(res, POINTER(c_char * map_size))
        self._init(data, map_size)

    def _init(self, data, map_size):
        self._data = data
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

    def execute(self, arg1, arg2):
        # XXX old testing stuff
        fnptr = cast(self._data, binaryfn)
        return fnptr(arg1, arg2)

    def done(self):
        # normally, no special action is needed here
        if CODE_DUMP:
            self.dump_range(self._last_dump_start, self._pos)
            self._last_dump_start = self._pos

    def dump_range(self, start, end):
        HEX = '0123456789ABCDEF'
        dump = []
        for p in range(start, end):
            o = ord(self._data.contents[p])
            dump.append(HEX[o >> 4])
            dump.append(HEX[o & 15])
            if (p & 3) == 3:
                dump.append(':')
        os.write(2, 'CODE_DUMP @%x +%d  %s\n' % (self.tell() - self._pos,
                                                 start, ''.join(dump)))


class MachineCodeBlock(InMemoryCodeBuilder):

    def __init__(self, map_size):
        res = memhandler.alloc(map_size)
        data = cast(res, POINTER(c_char * map_size))
        self._init(data, map_size)

    def __del__(self):
        memhandler.free(cast(self._data, PTR), self._size)

binaryfn = CFUNCTYPE(c_int, c_int, c_int)    # for testing

# ____________________________________________________________

from pypy.rpython.lltypesystem import lltype

BUF = lltype.GcArray(lltype.Char)

class LLTypeMachineCodeBlock(I386CodeBuilder):
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

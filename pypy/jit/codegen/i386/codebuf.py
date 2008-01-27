import os
from pypy.rpython.lltypesystem import lltype, rffi
from ri386 import I386CodeBuilder

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
        data = rffi.cast(PTR, start)
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
            self._data[p] = c
            p += 1
        self._pos = p

    def tell(self):
        baseaddr = rffi.cast(lltype.Signed, self._data)
        return baseaddr + self._pos

    def seekback(self, count):
        pos = self._pos - count
        self._pos = pos
        self._last_dump_start = pos

    def execute(self, arg1, arg2):
        # XXX old testing stuff
        fnptr = rffi.cast(lltype.Ptr(BINARYFN), self._data)
        return fnptr(arg1, arg2)

    def done(self):
        # normally, no special action is needed here
        if machine_code_dumper.enabled:
            machine_code_dumper.dump_range(self, self._last_dump_start,
                                           self._pos)
            self._last_dump_start = self._pos

    def log(self, msg):
        if machine_code_dumper.enabled:
            machine_code_dumper.dump(self, 'LOG', self._pos, msg)


BINARYFN = lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed)


class MachineCodeDumper:
    enabled = True
    log_fd = -1
    sys_executable = None

    def _freeze_(self):
        # reset the machine_code_dumper global instance to its default state
        if self.log_fd >= 0:
            os.close(self.log_fd)
        self.__dict__.clear()
        return False

    def open(self):
        if self.log_fd < 0:
            # check the environment for a file name
            s = os.environ.get('PYPYJITLOG')
            if not s:
                self.enabled = False
                return False
            try:
                flags = os.O_WRONLY|os.O_CREAT|os.O_TRUNC
                self.log_fd = os.open(s, flags, 0666)
            except OSError:
                os.write(2, "could not create log file\n")
                self.enabled = False
                return False
            # log the executable name
            from pypy.jit.codegen.hlinfo import highleveljitinfo
            os.write(self.log_fd, 'BACKEND i386\n')
            if highleveljitinfo.sys_executable:
                os.write(self.log_fd, 'SYS_EXECUTABLE %s\n' % (
                    highleveljitinfo.sys_executable,))
        return True

    def dump(self, cb, tag, pos, msg):
        if not self.open():
            return
        line = '%s @%x +%d  %s\n' % (tag, cb.tell() - cb._pos, pos, msg)
        os.write(self.log_fd, line)

    def dump_range(self, cb, start, end):
        HEX = '0123456789ABCDEF'
        dump = []
        for p in range(start, end):
            o = ord(cb._data[p])
            dump.append(HEX[o >> 4])
            dump.append(HEX[o & 15])
            if (p & 3) == 3:
                dump.append(':')
        self.dump(cb, 'CODE_DUMP', start, ''.join(dump))

machine_code_dumper = MachineCodeDumper()


class MachineCodeBlock(InMemoryCodeBuilder):

    def __init__(self, map_size):
        data = memhandler.alloc(map_size)
        self._init(data, map_size)

    def __del__(self):
        memhandler.free(self._data, self._size)

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
        self._base = LLTypeMachineCodeBlock.state.base
        LLTypeMachineCodeBlock.state.base += map_size

    def write(self, data):
        p = self._pos
        if p + len(data) > self._size:
            raise CodeBlockOverflow
        self._pos += len(data)
        return

    def tell(self):
        return self._base + self._pos

    def seekback(self, count):
        self._pos -= count

    def done(self):
        pass

class LLTypeInMemoryCodeBuilder(LLTypeMachineCodeBlock):
    _last_dump_start = 0

    def __init__(self, start, end):
        self._size = end - start
        self._pos = 0
        self._base = start



import os, sys
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.jit.backend.x86.rx86 import X86_32_CodeBuilder, X86_64_CodeBuilder
from pypy.jit.backend.x86.regloc import LocationCodeBuilder
from pypy.rlib.rmmap import PTR, alloc, free
from pypy.rlib.debug import make_sure_not_resized
from pypy.jit.backend.x86.arch import IS_X86_32, IS_X86_64
from pypy.rlib.objectmodel import we_are_translated

# XXX: Seems nasty to change the superclass of InMemoryCodeBuilder like this
if IS_X86_32:
    codebuilder_cls = X86_32_CodeBuilder
elif IS_X86_64:
    codebuilder_cls = X86_64_CodeBuilder

class InMemoryCodeBuilder(codebuilder_cls, LocationCodeBuilder):
    _last_dump_start = 0

    def __init__(self, start, end):
        map_size = end - start
        data = rffi.cast(PTR, start)
        self._init(data, map_size)

    def _init(self, data, map_size):
        self._data = data
        self._size = map_size
        self._pos = 0

    def overwrite(self, pos, listofchars):
        """ Overwrite a specified position with a given list of chars
        (position is relative
        """
        make_sure_not_resized(listofchars)
        assert pos + len(listofchars) <= self._size
        for c in listofchars:
            self._data[pos] = c
            pos += 1
        return pos

    def write(self, listofchars):
        self._pos = self.overwrite(self._pos, listofchars)

    def writechar(self, char):
        pos = self._pos
        assert pos + 1 <= self._size
        self._data[pos] = char
        self._pos = pos + 1

    def writechr(self, n):
        self.writechar(chr(n))

    def get_relative_pos(self):
        """ Current position, relative to code start
        """
        return self._pos

    def tell(self):
        """ Tell the current address at machine code block
        """
        baseaddr = rffi.cast(lltype.Signed, self._data)
        return baseaddr + self._pos

    def done(self):
        """ Called at the end of writing of each piece of machine code.
        Even though this function doesn't do much, it's extremely important
        to call this for all tools to work, like valgrind or machine code
        dumping
        """
        self.valgrind_invalidated()
        if machine_code_dumper.enabled:
            machine_code_dumper.dump_range(self, self._last_dump_start,
                                           self._pos)
            self._last_dump_start = self._pos

    def log(self, msg):
        """ Insert information into machine code dumper, if enabled
        """
        if machine_code_dumper.enabled:
            machine_code_dumper.dump(self, 'LOG', self._pos, msg)

    def valgrind_invalidated(self):
        """ Mark the range of the InMemoryCodeBuilder as invalidated
        for Valgrind
        """
        from pypy.jit.backend.x86 import valgrind
        valgrind.discard_translations(self._data, self._size)


class MachineCodeDumper:
    enabled = True
    log_fd = -1

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
            from pypy.jit.backend.hlinfo import highleveljitinfo
            if IS_X86_32:
                os.write(self.log_fd, 'BACKEND x86\n')
            elif IS_X86_64:
                os.write(self.log_fd, 'BACKEND x86_64\n')
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
        data = alloc(map_size)
        if IS_X86_64 and not we_are_translated():
            # Hack to make sure that mcs are not within 32-bits of one
            # another for testing purposes
            from pypy.rlib.rmmap import hint
            hint.pos += 0x80000000 - map_size
            
        self._init(data, map_size)

    def __del__(self):
        size = self._size
        assert size >= 0
        free(self._data, size)


# ____________________________________________________________

memcpy_fn = rffi.llexternal('memcpy', [llmemory.Address, llmemory.Address,
                                       rffi.SIZE_T], lltype.Void,
                            sandboxsafe=True, _nowrapper=True)

# ____________________________________________________________

if sys.platform == 'win32':
    ensure_sse2_floats = lambda : None
else:
    _sse2_eci = ExternalCompilationInfo(
        compile_extra = ['-msse2', '-mfpmath=sse'],
        separate_module_sources = ['void PYPY_NO_OP(void) {}'],
        )
    ensure_sse2_floats = rffi.llexternal('PYPY_NO_OP', [], lltype.Void,
                                         compilation_info=_sse2_eci,
                                         sandboxsafe=True)

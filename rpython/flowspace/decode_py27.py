"""
Decoder for the Python 2.7 bytecode of the host, CPython 2.7 or PyPy2.
"""
import opcode as _host_opcode

from rpython.flowspace import instr as I
from rpython.flowspace.bytecode import BytecodeCorruption, LineTable
from rpython.flowspace.decoder import Decoder

OPMAP = _host_opcode.opmap
OPNAMES = dict((num, name) for name, num in OPMAP.items())
HAVE_ARGUMENT = 90
EXTENDED_ARG = OPMAP['EXTENDED_ARG']
HASJREL = set(_host_opcode.hasjrel)
HASJABS = set(_host_opcode.hasjabs)


class Py2Decoder(Decoder):
    """Decoder for the bytecode of CPython 2.7 and PyPy2."""

    opcodes = {}    # filled by @decodes below

    def read(self):
        """Yield (offset, opcode name, oparg) for each host instruction,
        with relative jumps converted to absolute offsets. The name is
        None for unknown opcodes."""
        co_code = self.code.co_code
        offset = 0
        end = len(co_code)
        while offset < end:
            opnum = ord(co_code[offset])
            next_offset = offset + 1
            if opnum >= HAVE_ARGUMENT:
                oparg = (ord(co_code[next_offset]) |
                         (ord(co_code[next_offset + 1]) << 8))
                next_offset += 2
            else:
                oparg = 0
            while opnum == EXTENDED_ARG:
                opnum = ord(co_code[next_offset])
                if opnum < HAVE_ARGUMENT:
                    raise BytecodeCorruption
                lo = ord(co_code[next_offset + 1])
                hi = ord(co_code[next_offset + 2])
                next_offset += 3
                oparg = (oparg * 65536) | (hi * 256) | lo
            if opnum in HASJREL:
                oparg += next_offset
            yield offset, OPNAMES.get(opnum), oparg
            offset = next_offset

    def unknown_opcode(self, name, oparg):
        if name is None:
            return [I.HostOpcode('MISSING_OPCODE', oparg)]
        # Temporary: run the opcode with the FlowContext method of the
        # same name.
        methodname = name.replace('+', '_')
        if OPMAP[name] in HASJREL or OPMAP[name] in HASJABS:
            return [I.HostJumpOpcode(methodname, oparg)]
        return [I.HostOpcode(methodname, oparg)]

    def linetable(self):
        tab = self.code.co_lnotab
        addr = 0
        line = self.code.co_firstlineno
        starts = [(0, line)]
        for i in range(0, len(tab), 2):
            addr += ord(tab[i])
            line += ord(tab[i + 1])
            if starts[-1][0] == addr:
                starts[-1] = (addr, line)
            else:
                starts.append((addr, line))
        return LineTable(starts)


def decodes(*names):
    """Register the decorated function in Py2Decoder.opcodes."""
    def register(func):
        for name in names:
            Py2Decoder.opcodes[name] = func
        return func
    return register

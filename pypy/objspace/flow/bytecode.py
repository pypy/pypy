"""
Bytecode handling classes and functions for use by the flow space.
"""
from pypy.interpreter.pycode import PyCode, BytecodeCorruption
from pypy.tool.stdlib_opcode import (host_bytecode_spec, EXTENDED_ARG,
        HAVE_ARGUMENT)
from pypy.interpreter.astcompiler.consts import CO_GENERATOR

class HostCode(PyCode):
    """
    A wrapper around a native code object of the host interpreter
    """
    opnames = host_bytecode_spec.method_names

    def read(self, pos):
        """
        Decode the instruction starting at position ``next_instr``.

        Returns (next_instr, opname, oparg).
        """
        co_code = self.co_code
        opcode = ord(co_code[pos])
        next_instr = pos + 1

        if opcode >= HAVE_ARGUMENT:
            lo = ord(co_code[next_instr])
            hi = ord(co_code[next_instr+1])
            next_instr += 2
            oparg = (hi * 256) | lo
        else:
            oparg = 0

        while opcode == EXTENDED_ARG:
            opcode = ord(co_code[next_instr])
            if opcode < HAVE_ARGUMENT:
                raise BytecodeCorruption
            lo = ord(co_code[next_instr+1])
            hi = ord(co_code[next_instr+2])
            next_instr += 3
            oparg = (oparg * 65536) | (hi * 256) | lo

        opname = self.opnames[opcode]
        return next_instr, opname, oparg

    @property
    def is_generator(self):
        return bool(self.co_flags & CO_GENERATOR)

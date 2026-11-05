"""
Decoders translate host code objects into FlowCode.
"""
from rpython.flowspace import instr as I
from rpython.flowspace.bytecode import (
    BytecodeCorruption, FlowCode, cpython_code_signature)


class Decoder(object):
    """Translates one host code object into a FlowCode.

    There is a subclass for each bytecode dialect, which implements read()
    and fills its own 'opcodes' table."""

    # {opcode name: function(decoder, oparg) -> list of instructions}
    # Jump targets in the instructions are host offsets, which
    # decode_instructions() converts to positions.
    opcodes = {}

    def __init__(self, code):
        self.code = code

    def read(self):
        """Yield (offset, opcode name, oparg) for each host instruction."""
        raise NotImplementedError

    def unknown_opcode(self, name, oparg):
        """Instructions for an opcode missing from the 'opcodes' table."""
        raise BytecodeCorruption("unknown opcode %s" % (name,))

    def decode_instructions(self):
        instrs = []
        offset2pos = {}
        for offset, name, oparg in self.read():
            offset2pos[offset] = len(instrs)
            if name in self.opcodes:
                new = self.opcodes[name](self, oparg)
            else:
                new = self.unknown_opcode(name, oparg)
            for instr in new:
                instr.offset = offset
            instrs.extend(new)
        offset2pos[len(self.code.co_code)] = len(instrs)
        for instr in instrs:
            if isinstance(instr, I.JumpInstr):
                try:
                    instr.target = offset2pos[instr.target]
                except KeyError:
                    raise BytecodeCorruption("jump into an instruction")
        return instrs

    def linetable(self):
        """The LineTable of the code object."""
        raise NotImplementedError

    def signature(self):
        return cpython_code_signature(self.code)

    def decode(self):
        code = self.code
        instrs = self.decode_instructions()
        return FlowCode(self.signature(), code.co_nlocals,
                        list(code.co_varnames), list(code.co_freevars),
                        code.co_flags, code.co_filename, code.co_name,
                        code.co_firstlineno, instrs, self.linetable(),
                        list(code.co_consts), list(code.co_names))

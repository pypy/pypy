"""
Bytecode handling classes and functions for use by the flow space.
"""
from pypy.interpreter.pycode import (PyCode, BytecodeCorruption, cpython_magic,
        cpython_code_signature)
from pypy.tool.stdlib_opcode import (host_bytecode_spec, EXTENDED_ARG,
        HAVE_ARGUMENT)
from pypy.interpreter.astcompiler.consts import CO_GENERATOR

class HostCode(PyCode):
    """
    A wrapper around a native code object of the host interpreter
    """
    opnames = host_bytecode_spec.method_names

    def __init__(self, space,  argcount, nlocals, stacksize, flags,
                     code, consts, names, varnames, filename,
                     name, firstlineno, lnotab, freevars, cellvars,
                     hidden_applevel=False, magic=cpython_magic):
        """Initialize a new code object"""
        self.space = space
        self.co_name = name
        assert nlocals >= 0
        self.co_argcount = argcount
        self.co_nlocals = nlocals
        self.co_stacksize = stacksize
        self.co_flags = flags
        self.co_code = code
        self.co_consts_w = consts
        self.co_names_w = [space.wrap(aname) for aname in names]
        self.co_varnames = varnames
        self.co_freevars = freevars
        self.co_cellvars = cellvars
        self.co_filename = filename
        self.co_name = name
        self.co_firstlineno = firstlineno
        self.co_lnotab = lnotab
        self.hidden_applevel = hidden_applevel
        self.magic = magic
        self._signature = cpython_code_signature(self)
        self._initialize()

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

"""
Bytecode handling classes and functions for use by the flow space.
"""
from bisect import bisect_right

from rpython.tool.stdlib_opcode import host_bytecode_spec
from opcode import EXTENDED_ARG, HAVE_ARGUMENT
import opcode
from rpython.flowspace.argument import Signature

try:
    from __pypy__ import _promote
except ImportError:
    _promote = lambda x: x

CO_GENERATOR = 0x0020
CO_VARARGS = 0x0004
CO_VARKEYWORDS = 0x0008

def cpython_code_signature(code):
    "([list-of-arg-names], vararg-name-or-None, kwarg-name-or-None)."
    argcount = code.co_argcount
    argnames = list(code.co_varnames[:argcount])
    if code.co_flags & CO_VARARGS:
        varargname = code.co_varnames[argcount]
        argcount += 1
    else:
        varargname = None
    if code.co_flags & CO_VARKEYWORDS:
        kwargname = code.co_varnames[argcount]
        argcount += 1
    else:
        kwargname = None
    return Signature(argnames, varargname, kwargname)


class BytecodeCorruption(Exception):
    pass


class LineTable(object):
    """Maps host bytecode offsets to source line numbers."""

    def __init__(self, starts):
        """'starts' is a list of (offset, lineno) sorted by offset, where
        each lineno applies up to the next offset in the list."""
        assert starts and starts[0][0] == 0
        self.offsets = [offset for offset, _ in starts]
        self.linenos = [lineno for _, lineno in starts]

    def offset2lineno(self, offset):
        return self.linenos[bisect_right(self.offsets, offset) - 1]


def lnotab_linetable(firstlineno, lnotab):
    """The LineTable of a Python 2 code object."""
    addr = 0
    line = firstlineno
    starts = [(0, line)]
    for i in range(0, len(lnotab), 2):
        addr += ord(lnotab[i])
        line += ord(lnotab[i + 1])
        if starts[-1][0] == addr:
            starts[-1] = (addr, line)
        else:
            starts.append((addr, line))
    return LineTable(starts)

HASJREL = bytearray([_opnum in opcode.hasjrel for _opnum in range(256)])

class HostCode(object):
    """
    A wrapper around a native code object of the host interpreter
    """
    opnames = tuple(host_bytecode_spec.method_names)

    def __init__(self, argcount, nlocals, stacksize, flags,
                 code, consts, names, varnames, filename,
                 name, firstlineno, lnotab, freevars):
        """Initialize a new code object"""
        assert nlocals >= 0
        self.co_argcount = argcount
        self.co_nlocals = nlocals
        self.co_stacksize = stacksize
        self.co_flags = flags
        self.co_code = code
        self.consts = consts
        self.names = names
        self.co_varnames = varnames
        self.co_freevars = freevars
        self.co_filename = filename
        self.co_name = name
        self.co_firstlineno = firstlineno
        self.co_lnotab = lnotab
        self.linetable = lnotab_linetable(firstlineno, lnotab)
        self.signature = cpython_code_signature(self)

    @classmethod
    def _from_code(cls, code):
        """Initialize the code object from a real (CPython) one.
        """
        return cls(code.co_argcount,
                   code.co_nlocals,
                   code.co_stacksize,
                   code.co_flags,
                   code.co_code,
                   list(code.co_consts),
                   list(code.co_names),
                   list(code.co_varnames),
                   code.co_filename,
                   code.co_name,
                   code.co_firstlineno,
                   code.co_lnotab,
                   list(code.co_freevars))

    @property
    def formalargcount(self):
        """Total number of arguments passed into the frame, including *vararg
        and **varkwarg, if they exist."""
        return self.signature.scope_length()

    def read(self, offset):
        """
        Decode the instruction starting at position ``offset``.

        Returns (next_offset, opname, oparg).
        """
        co_code = self.co_code
        opnum = ord(co_code[offset])
        next_offset = offset + 1

        if opnum >= HAVE_ARGUMENT:
            lo = ord(co_code[next_offset])
            hi = ord(co_code[next_offset + 1])
            next_offset += 2
            oparg = (hi * 256) | lo
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

        if HASJREL[opnum]:
            oparg += next_offset
        opname = self.opnames[_promote(opnum)]
        return next_offset, opname, oparg

    @property
    def is_generator(self):
        return bool(self.co_flags & CO_GENERATOR)

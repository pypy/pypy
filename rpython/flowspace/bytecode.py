"""
Code objects, as seen by the flow space.
"""
from bisect import bisect_right

from rpython.flowspace.argument import Signature

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


class FlowCode(object):
    """
    A host code object decoded into a list of instructions (see instr.py)
    """

    def __init__(self, signature, nlocals, varnames, freevars, flags,
                 filename, name, firstlineno, instrs, linetable):
        assert nlocals >= 0
        self.signature = signature
        self.nlocals = nlocals
        self.varnames = varnames
        self.freevars = freevars
        self.flags = flags
        self.filename = filename
        self.name = name
        self.firstlineno = firstlineno
        self.instrs = instrs
        self.linetable = linetable

    @property
    def formalargcount(self):
        """Total number of arguments passed into the frame, including *vararg
        and **varkwarg, if they exist."""
        return self.signature.scope_length()

    @property
    def is_generator(self):
        return bool(self.flags & CO_GENERATOR)

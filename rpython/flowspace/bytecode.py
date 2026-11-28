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

    def __init__(self, firstlineno, starts):
        """'starts' is a list of (offset, lineno) sorted by offset, where
        each lineno applies up to the next offset in the list."""
        assert starts and starts[0][0] == 0
        self.firstlineno = firstlineno
        self.offsets = [offset for offset, _ in starts]
        self.linenos = [lineno for _, lineno in starts]

    def offset2lineno(self, offset):
        """The line of the instruction at 'offset', or the first line of
        the code object for a negative offset, which operations that were
        not recorded from a host instruction have."""
        if offset < 0:
            return self.firstlineno
        return self.linenos[bisect_right(self.offsets, offset) - 1]


class Handler(object):
    """An entry of the exception table of Python 3.11.

    An exception raised by the instructions from 'start' up to 'end' continues
    at 'target', with the stack cut down to 'depth' items. On top of these came
    the offset of the instruction, if 'lasti', and the exception.
    'catches' is False for a handler that only cleans up and re-raises.
    """

    def __init__(self, start, end, target, depth, lasti, catches):
        self.start = start
        self.end = end
        self.target = target
        self.depth = depth
        self.lasti = lasti
        self.catches = catches


class FlowCode(object):
    """
    A host code object decoded into a list of instructions (see instr.py)
    """

    def __init__(self, signature, nlocals, varnames, freevars, flags,
                 filename, name, firstlineno, instrs, linetable,
                 handlers=()):
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
        self.handlers = handlers

    def find_handler(self, pos):
        """The innermost Handler for the instruction at 'pos', or None."""
        for handler in self.handlers:
            if handler.start <= pos < handler.end:
                return handler
        return None

    @property
    def formalargcount(self):
        """Total number of arguments passed into the frame, including *vararg
        and **varkwarg, if they exist."""
        return self.signature.scope_length()

    @property
    def is_generator(self):
        return bool(self.flags & CO_GENERATOR)

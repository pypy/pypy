"""
Bytecode handling classes and functions for use by the flow space.
"""
from rpython.tool.stdlib_opcode import host_bytecode_spec
from opcode import EXTENDED_ARG, HAVE_ARGUMENT
import opcode
from rpython.flowspace.argument import Signature
from rpython.tool.twothree import PY2

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

LOCAL_OPS = frozenset(opcode.haslocal)
NAME_OPS = frozenset(opcode.hasname)
FREE_OPS = frozenset(opcode.hasfree)
COMPREHENSIONS = ('<listcomp>', '<dictcomp>', '<setcomp>')
DEREF_AS_LOCAL = {'LOAD_DEREF': 'LOAD_FAST', 'STORE_DEREF': 'STORE_FAST',
                  'DELETE_DEREF': 'DELETE_FAST'}


def read_wordcode(co_code, offset):
    """Decode one instruction of PyPy 3 bytecode: two bytes, after any
    EXTENDED_ARG prefixes.  Returns (next_offset, opnum, oparg)."""
    opnum = co_code[offset]
    oparg = co_code[offset + 1]
    next_offset = offset + 2
    while opnum == EXTENDED_ARG:
        opnum = co_code[next_offset]
        oparg = (oparg << 8) | co_code[next_offset + 1]
        next_offset += 2
    return next_offset, opnum, oparg


class Segment(object):
    """The bytecode of a function on PyPy 3, or of a comprehension in it.

    PyPy 3 compiles a comprehension to a nested function, called with the
    iterator, whose free variables are cells of the function around it.
    RPython has neither closures nor iterators as arguments, so the
    comprehension is flowed as part of that function instead: its code gets
    offsets after the function's own, its locals, constants and names are
    appended to the function's, and the cells become ordinary locals.
    """
    return_offset = None
    call_offset = None

    def __init__(self, hostcode, code, scope, outer):
        self.co_code = code.co_code
        self.is_function = code is outer
        if self.is_function:
            self.start = self.local_shift = 0
            self.const_shift = self.name_shift = 0
        else:
            self.start = hostcode.virtual_size
            self.local_shift = hostcode.co_nlocals
            self.const_shift = len(hostcode.consts)
            self.name_shift = len(hostcode.names)
            hostcode.co_nlocals += code.co_nlocals
            hostcode.co_varnames.extend(code.co_varnames)
            hostcode.consts.extend(code.co_consts)
            hostcode.names.extend(code.co_names)
        self.end = self.start + len(code.co_code)
        hostcode.virtual_size = self.end
        self.index = len(hostcode.segments)
        hostcode.segments.append(self)

        scope = dict(scope)
        self.derefs = []
        for name in code.co_cellvars:
            if name in code.co_varnames:
                slot = self.local_shift + code.co_varnames.index(name)
            else:
                slot = hostcode.co_nlocals
                hostcode.co_nlocals += 1
                hostcode.co_varnames.append(name)
            scope[name] = slot
            self.derefs.append(slot)
        for name in code.co_freevars:
            if name in scope:
                self.derefs.append(scope[name])
            else:
                self.derefs.append(~outer.co_freevars.index(name))

        self.inlined = {}
        offset = 0
        while offset < len(code.co_code):
            next_offset, opnum, oparg = read_wordcode(code.co_code, offset)
            if opcode.opname[opnum] == 'LOAD_CONST':
                const = code.co_consts[oparg]
                if (getattr(const, 'co_name', None) in COMPREHENSIONS and
                        not const.co_exceptiontable):
                    self.inlined[next_offset - 2] = Segment(
                        hostcode, const, scope, outer)
            offset = next_offset

    def read(self, offset, opnames):
        position = offset - self.start
        next_position, opnum, oparg = read_wordcode(self.co_code, position)
        opname = opnames[_promote(opnum)]
        if HASJREL[opnum]:
            oparg = self.start + next_position + oparg * 2
        elif HASJABS[opnum]:
            oparg = self.start + oparg * 2
        elif opnum in LOCAL_OPS:
            oparg += self.local_shift
        elif opname == 'LOAD_CONST':
            if next_position - 2 in self.inlined:
                opname = 'LOAD_INLINED'
                oparg = self.inlined[next_position - 2].index
            else:
                oparg += self.const_shift
        elif opnum in NAME_OPS:
            oparg += self.name_shift
        elif opnum in FREE_OPS:
            slot = self.derefs[oparg]
            if slot < 0:
                oparg = ~slot
            elif opname in DEREF_AS_LOCAL:
                opname = DEREF_AS_LOCAL[opname]
                oparg = slot
        elif opname == 'RETURN_VALUE' and not self.is_function:
            opname = 'RETURN_INLINED'
        return self.start + next_position, opname, oparg

HASJREL = bytearray([_opnum in opcode.hasjrel for _opnum in range(256)])
HASJABS = bytearray([_opnum in opcode.hasjabs for _opnum in range(256)])


def parse_exception_table(table):
    """Decode co_exceptiontable into (start, end, target, depth, lasti)
    tuples, with the offsets in bytes."""
    table = bytearray(table)
    entries = []
    pos = [0]

    def varint():
        byte = table[pos[0]]
        pos[0] += 1
        value = byte & 63
        while byte & 64:
            byte = table[pos[0]]
            pos[0] += 1
            value = (value << 6) | (byte & 63)
        return value

    while pos[0] < len(table):
        start = varint() * 2
        end = start + varint() * 2
        target = varint() * 2
        depth_lasti = varint()
        entries.append((start, end, target, depth_lasti >> 1,
                        bool(depth_lasti & 1)))
    return entries

class HostCode(object):
    """
    A wrapper around a native code object of the host interpreter
    """
    opnames = tuple(host_bytecode_spec.method_names)

    def __init__(self, argcount, nlocals, stacksize, flags,
                 code, consts, names, varnames, filename,
                 name, firstlineno, lnotab, freevars, exceptiontable=()):
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
        self.exceptiontable = exceptiontable
        self.segments = []
        self.signature = cpython_code_signature(self)

    @classmethod
    def _from_code(cls, code):
        """Initialize the code object from a real (CPython) one.
        """
        self = cls(code.co_argcount,
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
                   list(code.co_freevars),
                   parse_exception_table(
                       getattr(code, 'co_exceptiontable', b'')))
        if not PY2:
            self.virtual_size = 0
            Segment(self, code, {}, code)
        return self

    def segment_at(self, offset):
        for segment in self.segments:
            if segment.start <= offset < segment.end:
                return segment
        return None

    def outer_offset(self, offset):
        """The offset in the function itself that ``offset`` belongs to:
        for an instruction of an inlined comprehension, where it is
        called."""
        segment = self.segment_at(offset)
        while segment is not None and segment.call_offset is not None:
            offset = segment.call_offset
            segment = self.segment_at(offset)
        return offset

    @property
    def formalargcount(self):
        """Total number of arguments passed into the frame, including *vararg
        and **varkwarg, if they exist."""
        return self.signature.scope_length()

    def read_py2(self, offset):
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

    def find_handler(self, offset):
        """The (target, depth, lasti) of the exception table entry that
        covers the instruction at ``offset``, or None."""
        for start, end, target, depth, lasti in self.exceptiontable:
            if start <= offset < end:
                return target, depth, lasti
        return None

    def has_handler(self, offset):
        """Whether an exception raised at ``offset`` reaches an except or
        finally clause or a with statement.  The handlers that the compiler
        adds to restore the exception state and re-raise do not count."""
        while True:
            handler = self.find_handler(offset)
            if handler is None:
                return False
            offset = handler[0]
            next_offset, opname, _ = self.read(offset)
            if opname == 'PUSH_EXC_INFO':
                return True
            while opname != 'RERAISE':
                offset = next_offset
                next_offset, opname, _ = self.read(offset)

    def read(self, offset):
        """
        Decode the instruction starting at position ``offset``.

        Returns (next_offset, opname, oparg).  The oparg of a jump is the
        offset of its target.
        """
        if PY2:
            return self.read_py2(offset)
        return self.segment_at(offset).read(offset, self.opnames)

    @property
    def is_generator(self):
        return bool(self.co_flags & CO_GENERATOR)

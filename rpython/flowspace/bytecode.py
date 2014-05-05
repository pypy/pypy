"""
Bytecode handling classes and functions for use by the flow space.
"""
from rpython.tool.stdlib_opcode import host_bytecode_spec
from opcode import EXTENDED_ARG, HAVE_ARGUMENT
import opcode
from rpython.flowspace.argument import Signature
from rpython.flowspace.model import const
from rpython.flowspace.operation import op

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


class HostCode(object):
    """
    A wrapper around a native code object of the host interpreter
    """
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
        self.signature = cpython_code_signature(self)
        self.build_flow()

    def disassemble(self):
        contents = []
        offsets = []
        jumps = {}
        pos = 0
        i = 0
        while pos < len(self.co_code):
            offsets.append(pos)
            next_pos, op = self.decode(pos)
            contents.append(op)
            if op.has_jump():
                jumps[pos] = op.arg
            pos = next_pos
            i += 1
        return contents, offsets, jumps

    def build_flow(self):
        next_pos = pos = 0
        contents, offsets, jumps = self.disassemble()
        self.contents = zip(offsets, contents)
        self.pos_index = dict((offset, i) for i, offset in enumerate(offsets))
        # add end marker
        self.contents.append((len(self.co_code), None))


    @classmethod
    def _from_code(cls, code):
        """Initialize the code object from a real (CPython) one.
        """
        return cls(code.co_argcount, code.co_nlocals, code.co_stacksize,
                code.co_flags, code.co_code, list(code.co_consts),
                list(code.co_names), list(code.co_varnames), code.co_filename,
                code.co_name, code.co_firstlineno, code.co_lnotab,
                list(code.co_freevars))

    @property
    def formalargcount(self):
        """Total number of arguments passed into the frame, including *vararg
        and **varkwarg, if they exist."""
        return self.signature.scope_length()

    @property
    def is_generator(self):
        return bool(self.co_flags & CO_GENERATOR)

    def read(self, offset):
        i = self.pos_index[offset]
        op = self.contents[i][1]
        next_offset = self.contents[i+1][0]
        return next_offset, op

    def decode(self, offset):
        return bc_reader.read(self, offset)

class BytecodeReader(object):
    def __init__(self, opnames):
        self.opnames = opnames
        self.num2cls = {}

    def register_name(self, name, InstrClass):
        num = self.opnames.index(name)
        self.num2cls[num] = InstrClass
        return num

    def register_opcode(self, cls):
        """Class decorator: register opcode class as real Python opcode"""
        name = cls.__name__
        cls.name = name
        cls.num = self.register_name(name, cls)
        return cls

    def read(self, code, offset):
        """
        Decode the instruction starting at position ``offset``.

        Returns (next_offset, instruction).
        """
        co_code = code.co_code
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

        if opnum in opcode.hasjrel:
            oparg += next_offset
        elif opnum in opcode.hasname:
            oparg = code.names[oparg]
        try:
            op = self.num2cls[opnum].decode(oparg, offset, code)
        except KeyError:
            op = GenericOpcode(self.opnames[opnum], opnum, oparg, offset)
        return next_offset, op

bc_reader = BytecodeReader(host_bytecode_spec.method_names)


class BCInstruction(object):
    """
    A bytecode instruction, comprising an opcode and an optional argument.

    """
    def __init__(self, arg, offset=-1):
        self.arg = arg
        self.offset = offset

    @classmethod
    def decode(cls, arg, offset, code):
        return cls(arg, offset)

    def eval(self, ctx):
        pass

    def has_jump(self):
        return self.num in opcode.hasjrel or self.num in opcode.hasjabs

    def __repr__(self):
        return "%s(%s)" % (self.name, self.arg)

class GenericOpcode(BCInstruction):
    def __init__(self, name, opcode, arg, offset=-1):
        self.name = name
        self.num = opcode
        self.arg = arg
        self.offset = offset

    def eval(self, ctx):
        return getattr(ctx, self.name)(self.arg)


@bc_reader.register_opcode
class LOAD_CONST(BCInstruction):
    @staticmethod
    def decode(arg, offset, code):
        return LOAD_CONST(code.consts[arg], offset)

    def eval(self, ctx):
        ctx.pushvalue(const(self.arg))

_unary_ops = [
    ('UNARY_POSITIVE', op.pos),
    ('UNARY_NEGATIVE', op.neg),
    ('UNARY_CONVERT', op.repr),
    ('UNARY_INVERT', op.invert),
]

def unaryoperation(OPCODE, oper):
    class UNARY_OP(BCInstruction):
        def eval(self, ctx):
            w_1 = ctx.popvalue()
            w_result = oper(w_1).eval(ctx)
            ctx.pushvalue(w_result)
    UNARY_OP.__name__ = OPCODE
    bc_reader.register_opcode(UNARY_OP)
    return UNARY_OP

for OPCODE, oper in _unary_ops:
    globals()[OPCODE] = unaryoperation(OPCODE, oper)


_binary_ops = [
    ('BINARY_MULTIPLY', op.mul),
    ('BINARY_TRUE_DIVIDE', op.truediv),
    ('BINARY_FLOOR_DIVIDE', op.floordiv),
    ('BINARY_DIVIDE', op.div),
    ('BINARY_MODULO', op.mod),
    ('BINARY_ADD', op.add),
    ('BINARY_SUBTRACT', op.sub),
    ('BINARY_SUBSCR', op.getitem),
    ('BINARY_LSHIFT', op.lshift),
    ('BINARY_RSHIFT', op.rshift),
    ('BINARY_AND', op.and_),
    ('BINARY_XOR', op.xor),
    ('BINARY_OR', op.or_),
    ('INPLACE_MULTIPLY', op.inplace_mul),
    ('INPLACE_TRUE_DIVIDE', op.inplace_truediv),
    ('INPLACE_FLOOR_DIVIDE', op.inplace_floordiv),
    ('INPLACE_DIVIDE', op.inplace_div),
    ('INPLACE_MODULO', op.inplace_mod),
    ('INPLACE_ADD', op.inplace_add),
    ('INPLACE_SUBTRACT', op.inplace_sub),
    ('INPLACE_LSHIFT', op.inplace_lshift),
    ('INPLACE_RSHIFT', op.inplace_rshift),
    ('INPLACE_AND', op.inplace_and),
    ('INPLACE_XOR', op.inplace_xor),
    ('INPLACE_OR', op.inplace_or),
]

def binaryoperation(OPCODE, oper):
    class BINARY_OP(BCInstruction):
        def eval(self, ctx):
            w_2 = ctx.popvalue()
            w_1 = ctx.popvalue()
            w_result = oper(w_1, w_2).eval(ctx)
            ctx.pushvalue(w_result)
    BINARY_OP.__name__ = OPCODE
    bc_reader.register_opcode(BINARY_OP)
    return BINARY_OP

for OPCODE, oper in _binary_ops:
    globals()[OPCODE] = binaryoperation(OPCODE, oper)

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
        self.graph = bc_reader.build_flow(self)

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

    def _iter_instr(self, code):
        self.offset = 0
        i = 0
        while self.offset < len(code.co_code):
            if self.offset in self.pending_blocks:
                next_block = self.pending_blocks[self.offset]
                if not self.curr_block.operations:
                    import pdb; pdb.set_trace
                    self.blocks.pop()
                self.enter_next_block(next_block)
            elif self.needs_new_block:
                next_block = self.get_next_block()
                self.enter_next_block(next_block)
            next_offset, instr = self.read(code, self.offset)
            self.next_offset = next_offset
            yield instr
            self.offset = next_offset
            i += 1

    def find_position(self, offset):
        for i, block in enumerate(self.blocks):
            if block.startpos <= offset:
                n = i
            else:
                break
        for i, instr in enumerate(self.blocks[n]):
            if instr.offset == offset:
                return n, i

    def new_block(self):
        return SimpleBlock([])

    def get_block_at(self, offset):
        """Get or create the block starting at ``offset``"""
        if offset < self.next_offset:
            i_block, i_instr = self.find_position(offset)
            split = self.blocks[i_block].split_at(i_instr)
            if len(split) == 2:
                new_block = split[1]
                for i, instr in enumerate(new_block.operations):
                    self.graph.pos_index[instr.offset] = new_block, i
            self.blocks[i_block:i_block + 1] = split
            return split[-1]
        else:
            if offset in self.pending_blocks:
                return self.pending_blocks[offset]
            new_block = self.new_block()
            self.pending_blocks[offset] = new_block
            return new_block

    def get_next_block(self):
        """Find or create the block starting at the next offset"""
        return self.get_block_at(self.next_offset)

    def enter_next_block(self, block):
        if not self.curr_block._exits:
            assert block is not self.curr_block
            self.curr_block.set_exits([block])
        self.curr_block = block
        self.blocks.append(block)
        self.needs_new_block = False

    def end_block(self):
        self.needs_new_block = True

    def build_flow(self, code):
        self.pending_blocks = {}
        self.blocks = [SimpleBlock([])]
        self.curr_block = self.blocks[0]
        self.needs_new_block = False
        self.graph = graph = BytecodeGraph(self.blocks[0])
        for instr in self._iter_instr(code):
            block = self.curr_block
            graph.pos_index[instr.offset] = block, len(block.operations)
            instr.bc_flow(self)
        self.check_graph()
        return graph

    def check_graph(self):
        for b in self.blocks:
            if not b._exits:
                assert any(instr.name in ('RETURN_VALUE', 'RAISE_VARARGS')
                        for instr in b.operations)
            for x in b._exits:
                assert x in self.blocks

    def build_code(self, code):
        return HostCode._from_code(code)

bc_reader = BytecodeReader(host_bytecode_spec.method_names)

class BytecodeGraph(object):
    def __init__(self, startblock):
        self.entry = EntryBlock()
        self.entry.set_exits([startblock])
        self.pos_index = {}

    def read(self, pos):
        bc_block, i = self.pos_index[pos]
        return bc_block[i]

    def next_pos(self, instr):
        block, i = self.pos_index[instr.offset]
        i = i + 1
        if i >= len(block.operations):
            assert len(block._exits) == 1
            assert block._exits[0] is not block
            return block._exits[0].startpos
        else:
            return block.operations[i].offset

    def get_position(self, offset):
        return self.pos_index[offset]

    def get_offset(self, position):
        block, i = position
        return block[i].offset

    def iter_instr(self):
        while True:
            offset = self.get_offset(self.curr_position)
            instr = self.read(offset)
            yield instr

    def dump(self):
        all_blocks = set(x[0] for x in self.pos_index.values())
        blocks = sorted(all_blocks, key=lambda b: b.startpos)
        return [b.operations for b in blocks]


class BytecodeBlock(object):
    """Base class for opcode blocks"""
    def __init__(self):
        self.parents = set()
        self._exits = []

    def __getitem__(self, i):
        return self.operations[i]

    def add_exit(self, exit):
        self._exits.append(exit)
        exit.parents.add(self)

    def set_exits(self, exits):
        for old_exit in self._exits:
            old_exit.parents.remove(self)
        self._exits = exits
        for new_exit in exits:
            new_exit.parents.add(self)

    def change_exit(self, old_exit, new_exit):
        self._exits = [new_exit if exit is old_exit else exit
                for exit in self._exits]
        old_exit.parents.remove(self)
        new_exit.parents.add(self)

    @property
    def startpos(self):
        return self.operations[0].offset

    def split_at(self, i):
        if i == 0 or i == len(self.operations):
            return [self]
        assert 0 < i < len(self.operations)
        tail = self.operations[i:]
        del self.operations[i:]
        new_block = SimpleBlock(tail)
        new_block.set_exits(self._exits)
        self.set_exits([new_block])
        return [self, new_block]


class EntryBlock(BytecodeBlock):
    """A fake block to represent the beginning of a code object"""

class SimpleBlock(BytecodeBlock):
    """A block with a single exit."""
    def __init__(self, operations, exit=None):
        BytecodeBlock.__init__(self)
        self.operations = operations
        if exit:
            self.set_exits([exit])


OPNAMES = host_bytecode_spec.method_names
NO_ARG = -1

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

    def bc_flow(self, reader):
        reader.curr_block.operations.append(self)
        if self.has_jump():
            reader.end_block()
            reader.get_block_at(self.arg)

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


def flow_opcode(func):
    name = func.__name__
    class Op(BCInstruction):
        def __init__(self, arg=0, offset=-1):
            self.arg = arg
            self.offset = offset

        def eval(self, ctx):
            pass
    Op.__name__ = Op.name = name
    Op.bc_flow = func
    bc_reader.register_opcode(Op)
    return Op

@bc_reader.register_opcode
class LOAD_CONST(BCInstruction):
    @staticmethod
    def decode(arg, offset, code):
        return LOAD_CONST(code.consts[arg], offset)

    def eval(self, ctx):
        ctx.pushvalue(const(self.arg))

@bc_reader.register_opcode
class DUP_TOP(BCInstruction):
    def eval(self, ctx):
        w_1 = ctx.peekvalue()
        ctx.pushvalue(w_1)

@bc_reader.register_opcode
class POP_TOP(BCInstruction):
    def eval(self, ctx):
        ctx.popvalue()

@flow_opcode
def POP_JUMP_IF_FALSE(self, reader):
    reader.curr_block.operations.append(self)
    on_True = reader.get_next_block()
    on_False = reader.get_block_at(self.arg)
    block = reader.curr_block
    block.operations[-1] = SWITCH_BOOL(on_False, on_True, offset=self.offset)
    block.set_exits([on_False, on_True])

@flow_opcode
def POP_JUMP_IF_TRUE(self, reader):
    reader.curr_block.operations.append(self)
    on_False = reader.get_next_block()
    on_True = reader.get_block_at(self.arg)
    block = reader.curr_block
    block.operations[-1] = SWITCH_BOOL(on_False, on_True, offset=self.offset)
    block.set_exits([on_False, on_True])

@bc_reader.register_opcode
class JUMP_IF_FALSE_OR_POP(BCInstruction):
    def bc_flow(self, reader):
        block = reader.curr_block
        block.operations.append(self)
        self.on_True = reader.get_next_block()
        self.on_False = reader.get_block_at(self.arg)
        block.set_exits([self.on_False, self.on_True])

    def eval(self, ctx):
        w_value = ctx.peekvalue()
        if not ctx.guessbool(op.bool(w_value).eval(ctx)):
            return self.on_False
        ctx.popvalue()
        return self.on_True

@bc_reader.register_opcode
class JUMP_IF_TRUE_OR_POP(BCInstruction):
    def bc_flow(self, reader):
        block = reader.curr_block
        block.operations.append(self)
        self.on_True = reader.get_block_at(self.arg)
        self.on_False = reader.get_next_block()
        block.set_exits([self.on_False, self.on_True])

    def eval(self, ctx):
        w_value = ctx.peekvalue()
        if ctx.guessbool(op.bool(w_value).eval(ctx)):
            return self.on_True
        ctx.popvalue()
        return self.on_False


class SWITCH_BOOL(BCInstruction):
    name = 'SWITCH_BOOL'
    arg = NO_ARG
    def __init__(self, on_False, on_True, offset=-1):
        self.on_False = on_False
        self.on_True = on_True
        self.offset = offset

    def eval(self, ctx):
        w_value = ctx.popvalue()
        if ctx.guessbool(op.bool(w_value).eval(ctx)):
            return self.on_True
        else:
            return self.on_False

@flow_opcode
def JUMP_ABSOLUTE(self, reader):
    block = reader.curr_block
    block.operations.append(self)
    target_block = reader.get_block_at(self.arg)
    block.set_exits([target_block])
    reader.end_block()

@flow_opcode
def JUMP_FORWARD(self, reader):
    block = reader.curr_block
    block.operations.append(self)
    target_block = reader.get_block_at(self.arg)
    block.set_exits([target_block])
    reader.end_block()

@bc_reader.register_opcode
class FOR_ITER(BCInstruction):
    def bc_flow(self, reader):
        block = reader.curr_block
        block.operations.append(self)
        self.exit = reader.get_block_at(self.arg)
        self.body = reader.get_next_block()
        block.set_exits([self.body, self.exit])
        reader.end_block()

    def eval(self, ctx):
        from rpython.flowspace.flowcontext import Raise
        w_iterator = ctx.peekvalue()
        try:
            w_nextitem = op.next(w_iterator).eval(ctx)
            ctx.pushvalue(w_nextitem)
            return self.body
        except Raise as e:
            if ctx.exception_match(e.w_exc.w_type, const(StopIteration)):
                ctx.popvalue()
                return self.exit
            else:
                raise


@bc_reader.register_opcode
class SETUP_EXCEPT(BCInstruction):
    def eval(self, ctx):
        from rpython.flowspace.flowcontext import ExceptBlock
        block = ExceptBlock(ctx.stackdepth, self.arg)
        ctx.blockstack.append(block)

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

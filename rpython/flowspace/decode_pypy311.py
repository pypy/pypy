"""Decoder for the bytecode of PyPy 3.11."""
import dis
import opcode as _host_opcode

from rpython.flowspace import instr as I
from rpython.flowspace.bytecode import (
    BytecodeCorruption, FlowCode, Handler, LineTable
)
from rpython.flowspace.decoder import Decoder
from rpython.flowspace.operation import op

OPMAP = _host_opcode.opmap
OPNAMES = dict((num, name) for name, num in OPMAP.items())
HAVE_ARGUMENT = _host_opcode.HAVE_ARGUMENT
EXTENDED_ARG = OPMAP['EXTENDED_ARG']
HASJREL = set(_host_opcode.hasjrel)
HASJABS = set(_host_opcode.hasjabs)

NO_FALLTHROUGH = ('JUMP_FORWARD', 'JUMP_ABSOLUTE', 'RETURN_VALUE',
                  'RAISE_VARARGS', 'RERAISE')
LOADS = ('LOAD_FAST', 'LOAD_CONST', 'LOAD_GLOBAL', 'LOAD_NAME', 'LOAD_DEREF',
         'LOAD_CLOSURE', 'LOAD_ASSERTION_ERROR')
EMPTY_DISPLAYS = ('BUILD_LIST', 'BUILD_TUPLE', 'BUILD_MAP', 'BUILD_SET')
SUBSCRIPTS = {'BINARY_SUBSCR': I.GetSlice, 'STORE_SUBSCR': I.StoreSlice,
              'DELETE_SUBSCR': I.DeleteSlice}
UNSUPPORTED_COMPREHENSIONS = {'<dictcomp>': 'dict comprehensions',
                              '<setcomp>': 'set comprehensions'}
CLOSURE_ERROR = """RPython functions cannot create closures
Possible causes:
    Function is inner function
    Function uses generator expressions
    Lambda expressions
in %r"""


class HostInstr(object):
    """An instruction of the host.
    
    'oparg' is the offset of the target for a jump, and 'depth' the height of
    the stack before it, or None if it cannot be reached.
    """
    depth = None

    def __init__(self, offset, opnum, oparg, target):
        self.offset = offset
        self.opnum = opnum
        self.name = OPNAMES.get(opnum)
        self.oparg = oparg if target is None else target
        self.is_jump = target is not None
        self.raw_oparg = oparg if opnum >= HAVE_ARGUMENT else None

    def stack_effect(self, jump):
        return dis.stack_effect(self.opnum, self.raw_oparg, jump=jump)

    def pushes_only(self):
        return (self.name in LOADS or
                (self.name in EMPTY_DISPLAYS and self.oparg == 0))


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


class PyPy311Decoder(Decoder):
    """Decoder for the bytecode of PyPy 3.11.

    'rewritten' maps the index of a host instruction to the instructions
    to emit for it instead of what 'opcodes' says."""

    opcodes = {}

    def __init__(self, code, outer=None):
        """'outer' is the decoder of the function that the list
        comprehension 'code' is inlined into."""
        Decoder.__init__(self, code)
        if outer is None:
            self.root = self
            self.varnames = list(code.co_varnames)
            self.local_shift = 0
            scope = {}
        else:
            self.root = outer.root
            self.local_shift = len(self.root.varnames)
            self.root.varnames.extend(code.co_varnames)
            scope = dict(outer.scope)
        self.derefs = []
        for name in code.co_cellvars:
            if name in code.co_varnames:
                slot = self.local_shift + code.co_varnames.index(name)
            else:
                slot = len(self.root.varnames)
                self.root.varnames.append(name)
            scope[name] = slot
            self.derefs.append(slot)
        for name in code.co_freevars:
            if name in scope:
                self.derefs.append(scope[name])
            else:
                self.derefs.append(~self.root.code.co_freevars.index(name))
        self.scope = scope
        self.table = parse_exception_table(code.co_exceptiontable)
        self.host_instrs = list(self.read_host_instrs())
        self.index = dict((host.offset, i)
                          for i, host in enumerate(self.host_instrs))
        self.compute_depths()
        self.rewritten = {}
        self.rewrite_constant_names()
        self.rewrite_slices()
        self.rewrite_star_calls()
        self.rewrite_exception_stores()
        self.rewrite_comprehensions()

    def read_host_instrs(self):
        co_code = self.code.co_code
        offset = 0
        while offset < len(co_code):
            start = offset
            opnum = co_code[offset]
            oparg = co_code[offset + 1]
            offset += 2
            while opnum == EXTENDED_ARG:
                opnum = co_code[offset]
                oparg = (oparg << 8) | co_code[offset + 1]
                offset += 2
            target = None
            if opnum in HASJREL:
                target = offset + oparg * 2
            elif opnum in HASJABS:
                target = oparg * 2
            yield HostInstr(start, opnum, oparg, target)

    def read(self):
        for host in self.host_instrs:
            yield host.offset, host.name, host.oparg

    def compute_depths(self):
        hosts = self.host_instrs
        pending = [(0, 0)]
        for _, _, target, depth, lasti in self.table:
            pending.append((self.index[target], depth + lasti + 1))
        while pending:
            i, depth = pending.pop()
            while i < len(hosts) and hosts[i].depth is None:
                host = hosts[i]
                host.depth = depth
                if host.name is None:
                    break
                if host.is_jump:
                    pending.append((self.index[host.oparg],
                                    depth + host.stack_effect(True)))
                if host.name in NO_FALLTHROUGH:
                    break
                depth += host.stack_effect(False)
                i += 1

    # ____________________________________________________________

    def is_host(self, i, name, oparg=None):
        if not 0 <= i < len(self.host_instrs):
            return False
        host = self.host_instrs[i]
        return (i not in self.rewritten and host.name == name and
                (oparg is None or host.oparg == oparg))

    def constant_tuple(self, i):
        """The constant tuple loaded by the host instruction i, or None."""
        if not self.is_host(i, 'LOAD_CONST'):
            return None
        value = self.code.co_consts[self.host_instrs[i].oparg]
        if type(value) is not tuple:
            return None
        return value

    def rewrite_constant_names(self):
        for i, host in enumerate(self.host_instrs):
            if host.name in ('CALL_FUNCTION_KW', 'CALL_METHOD_KW'):
                names = self.constant_tuple(i - 1)
                if names is None:
                    raise BytecodeCorruption("no names for %s" % host.name)
                self.rewritten[i - 1] = []
                self.rewritten[i] = [
                    I.Call(host.oparg - len(names), names)]
            elif host.name == 'BUILD_CONST_KEY_MAP':
                keys = self.constant_tuple(i - 1)
                if keys is None:
                    raise BytecodeCorruption("no keys for %s" % host.name)
                self.rewritten[i - 1] = []
                self.rewritten[i] = [I.BuildConstKeyMap(keys)]

    def rewrite_slices(self):
        for i, host in enumerate(self.host_instrs):
            if self.is_host(i, 'BUILD_SLICE', 2):
                following = self.host_instrs[i + 1]
                if (following.name in SUBSCRIPTS and
                        i + 1 not in self.rewritten):
                    self.rewritten[i] = []
                    self.rewritten[i + 1] = [
                        SUBSCRIPTS[following.name](True, True)]

    def find_consumer(self, i, name):
        """The index of the first host instruction after i that pops the
        value that i leaves on top of the stack, if it is called 'name'
        and pops that value with (name, n) for an oparg of n."""
        hosts = self.host_instrs
        depth = hosts[i].depth + hosts[i].stack_effect(False)
        for j in range(i + 1, len(hosts)):
            host = hosts[j]
            if host.depth is None or host.depth < depth:
                return None
            if host.name == name and host.depth == depth + self.above(host):
                return j
            if host.depth == depth and not host.pushes_only():
                return None
        return None

    @staticmethod
    def above(host):
        """How many items a CALL_FUNCTION or CALL_FUNCTION_EX has on the
        stack above its function or its star argument."""
        if host.name == 'CALL_FUNCTION_EX':
            return host.oparg & 1
        return host.oparg

    def find_list(self, i):
        """The index of the BUILD_LIST of the list that the LIST_TO_TUPLE
        at i has on top of the stack, if nothing but the LIST_EXTEND before
        i has used the list."""
        hosts = self.host_instrs
        depth = hosts[i].depth
        for j in range(i - 2, -1, -1):
            host = hosts[j]
            if host.depth is None:
                return None
            if (host.name == 'BUILD_LIST' and j not in self.rewritten and
                    host.depth - host.oparg == depth - 1):
                return j
            if host.depth < depth:
                return None
            if host.depth == depth and not host.pushes_only():
                return None
            if (host.name in ('LIST_EXTEND', 'LIST_APPEND') and
                    host.depth - host.oparg == depth):
                return None
        return None

    def rewrite_star_calls(self):
        hosts = self.host_instrs
        nargs = {}
        for i, host in enumerate(hosts):
            if host.name != 'LIST_TO_TUPLE' or host.depth is None:
                continue
            if not self.is_host(i - 1, 'LIST_EXTEND', 1):
                continue
            call = self.find_consumer(i, 'CALL_FUNCTION_EX')
            if call is None:
                continue
            build = self.find_list(i)
            if build is None:
                continue
            self.rewritten[build] = []
            self.rewritten[i - 1] = []
            self.rewritten[i] = []
            nargs[call] = hosts[build].oparg
        for i, host in enumerate(hosts):
            if host.name != 'CALL_FUNCTION_EX':
                continue
            names = ()
            if host.oparg & 1:
                if not self.is_rewritten_as(i - 1, I.BuildConstKeyMap):
                    self.rewritten[i] = [
                        I.Unsupported("Dict-unpacking is not RPython")]
                    continue
                names = self.rewritten[i - 1][0].keys
                self.rewritten[i - 1] = []
            self.rewritten[i] = [I.Call(nargs.get(i, 0), names, True)]

    def is_rewritten_as(self, i, cls):
        new = self.rewritten.get(i)
        return bool(new) and type(new[0]) is cls

    def rewrite_exception_stores(self):
        """'except E as e' stores the exception right after matching it."""
        for i, host in enumerate(self.host_instrs):
            if (self.is_host(i, 'CHECK_EXC_MATCH') and
                    self.is_host(i + 1, 'POP_JUMP_IF_FALSE')):
                store = i + 2
            elif self.is_host(i, 'JUMP_IF_NOT_EXC_MATCH'):
                store = i + 1
            else:
                continue
            if self.is_host(store, 'STORE_FAST'):
                slot = self.local_shift + self.host_instrs[store].oparg
            elif self.is_host(store, 'STORE_DEREF'):
                slot = self.derefs[self.host_instrs[store].oparg]
                if slot < 0:
                    continue
            else:
                continue
            self.rewritten[store] = [I.StoreException(slot)]

    def rewrite_comprehensions(self):
        hosts = self.host_instrs
        for i, host in enumerate(hosts):
            if not self.is_host(i, 'LOAD_CONST'):
                continue
            code = self.code.co_consts[host.oparg]
            name = getattr(code, 'co_name', None)
            if not self.is_host(i + 1, 'MAKE_FUNCTION'):
                continue
            flags = hosts[i + 1].oparg
            if name in UNSUPPORTED_COMPREHENSIONS and not flags & ~0x08:
                self.drop_closure(i, flags)
                self.rewritten[i] = [I.Unsupported(
                    "%s is not RPython" % UNSUPPORTED_COMPREHENSIONS[name])]
                self.rewritten[i + 1] = []
                continue
            if (name != '<listcomp>' or flags & ~0x08 or
                    code.co_exceptiontable):
                continue
            call = self.find_consumer(i + 1, 'CALL_FUNCTION')
            if call is None or hosts[call].oparg != 1:
                continue
            if not self.drop_closure(i, flags):
                continue
            self.rewritten[i] = []
            self.rewritten[i + 1] = []
            self.rewritten[call] = Inlined(PyPy311Decoder(code, self))

    def drop_closure(self, i, flags):
        """Remove the tuple of cells built for the MAKE_FUNCTION of the
        code object loaded by the host instruction i."""
        if not flags & 0x08:
            return True
        if not self.is_host(i - 1, 'BUILD_TUPLE'):
            return False
        ncells = self.host_instrs[i - 1].oparg
        cells = range(i - 1 - ncells, i - 1)
        if not all(self.is_host(j, 'LOAD_CLOSURE') for j in cells):
            return False
        for j in cells:
            self.rewritten[j] = []
        self.rewritten[i - 1] = []
        return True

    # ____________________________________________________________

    def unknown_opcode(self, name, oparg):
        if name is None:
            return [I.Unsupported("??? is not RPython")]
        return Decoder.unknown_opcode(self, name, oparg)

    def decode_instructions(self):
        instrs = []
        jumps = []
        offset2pos = {}
        for i, host in enumerate(self.host_instrs):
            offset2pos[host.offset] = len(instrs)
            if i in self.rewritten:
                new = self.rewritten[i]
                if isinstance(new, Inlined):
                    new = new.instructions(len(instrs))
            elif host.name in self.opcodes:
                new = self.opcodes[host.name](self, host.oparg)
                jumps.extend([instr for instr in new
                              if isinstance(instr, I.JumpInstr)])
            else:
                new = self.unknown_opcode(host.name, host.oparg)
            for instr in new:
                instr.offset = host.offset
            instrs.extend(new)
        offset2pos[len(self.code.co_code)] = len(instrs)
        for instr in jumps:
            try:
                instr.target = offset2pos[instr.target]
            except KeyError:
                raise BytecodeCorruption("jump into an instruction")
        self.offset2pos = offset2pos
        return instrs

    def handlers(self):
        offset2pos = self.offset2pos
        return [Handler(offset2pos[start], offset2pos[end],
                        offset2pos[target], depth, lasti,
                        self.catches(target))
                for start, end, target, depth, lasti in self.table]

    def catches(self, target):
        """Whether the handler at the offset 'target' is an except or
        finally clause or the end of a with statement, or leads to one.
        The handlers that the compiler adds to restore the previous
        exception re-raise without a PUSH_EXC_INFO."""
        hosts = self.host_instrs
        seen = set()
        while target not in seen:
            seen.add(target)
            i = self.index[target]
            if hosts[i].name == 'PUSH_EXC_INFO':
                return True
            while hosts[i].name != 'RERAISE':
                i += 1
                if i == len(hosts):
                    return True
            for start, end, target, _, _ in self.table:
                if start <= hosts[i].offset < end:
                    break
            else:
                return False
        return True

    def linetable(self):
        firstlineno = self.code.co_firstlineno
        starts = [(0, firstlineno)]
        for start, _, lineno in self.code.co_lines():
            if lineno is None or lineno == starts[-1][1]:
                continue
            if starts[-1][0] == start:
                starts[-1] = (start, lineno)
            else:
                starts.append((start, lineno))
        return LineTable(firstlineno, starts)

    def decode(self):
        code = self.code
        instrs = self.decode_instructions()
        return FlowCode(self.signature(), len(self.varnames), self.varnames,
                        list(code.co_freevars), code.co_flags,
                        code.co_filename, code.co_name, code.co_firstlineno,
                        instrs, self.linetable(), self.handlers())


class Inlined(object):
    """The instructions of a list comprehension, to emit in place of the
    call of its function with the iterator."""

    def __init__(self, decoder):
        self.decoder = decoder

    def instructions(self, pos):
        """The instructions, when the first one is at position 'pos'."""
        body = self.decoder.decode_instructions()
        start = pos + 1
        for i, instr in enumerate(body):
            if isinstance(instr, I.ReturnValue):
                body[i] = instr = I.Jump(len(body))
            if isinstance(instr, I.JumpInstr):
                instr.target += start
        return [I.StoreFast(self.decoder.local_shift)] + body


def decodes(*names):
    """Register the decorated function in PyPy311Decoder.opcodes."""
    def register(func):
        for name in names:
            PyPy311Decoder.opcodes[name] = func
        return func
    return register


def no_operand(cls):
    """Decoder for opcodes whose oparg is ignored."""
    return lambda decoder, oparg: [cls()]

def with_oparg(cls):
    """Decoder for opcodes whose oparg is the operand of the instruction."""
    return lambda decoder, oparg: [cls(oparg)]

def with_name(cls):
    """Decoder for opcodes whose oparg is an index in co_names."""
    return lambda decoder, oparg: [cls(decoder.code.co_names[oparg])]

def with_local(cls):
    """Decoder for opcodes whose oparg is the index of a local variable."""
    return lambda decoder, oparg: [cls(decoder.local_shift + oparg)]

def register_all(table, make_decoder):
    for name, value in table.items():
        decodes(name)(make_decoder(value))

# ____________________________________________________________
# Variables and names

register_all({
    'LOAD_FAST': I.LoadFast,
    'STORE_FAST': I.StoreFast,
    'DELETE_FAST': I.DeleteFast,
}, with_local)

register_all({
    'LOAD_GLOBAL': I.LoadGlobal,
    'LOAD_NAME': I.LoadGlobal,
    'LOAD_ATTR': I.LoadAttr,
    'LOAD_METHOD': I.LoadAttr,
    'STORE_ATTR': I.StoreAttr,
    'IMPORT_NAME': I.ImportName,
    'IMPORT_FROM': I.ImportFrom,
}, with_name)

@decodes('LOAD_CONST')
def decode_load_const(decoder, oparg):
    return [I.LoadConst(decoder.code.co_consts[oparg])]

@decodes('LOAD_ASSERTION_ERROR')
def decode_load_assertion_error(decoder, oparg):
    return [I.LoadConst(AssertionError)]

@decodes('STORE_GLOBAL')
def decode_store_global(decoder, oparg):
    return [I.Unsupported("Attempting to modify global variable  %r."
                          % (decoder.code.co_names[oparg],))]

def cell_op(local_cls):
    """Decoder for the opcodes that access a cell or a free variable: a
    cell is a local variable here, and a free variable can only be read."""
    def decode(decoder, oparg):
        slot = decoder.derefs[oparg]
        if slot >= 0:
            return [local_cls(slot)]
        if local_cls is I.LoadFast:
            return [I.LoadDeref(~slot)]
        return [I.Unsupported("This operation is not RPython")]
    return decode

register_all({
    'LOAD_DEREF': I.LoadFast,
    'STORE_DEREF': I.StoreFast,
    'DELETE_DEREF': I.DeleteFast,
}, cell_op)

@decodes('LOAD_CLOSURE')
def decode_load_closure(decoder, oparg):
    raise ValueError(CLOSURE_ERROR % (decoder.root.code,))

# ____________________________________________________________
# Operators and unsupported opcodes

def unary_op(operation):
    return lambda decoder, oparg: [I.UnaryOp(operation)]

def binary_op(operation):
    return lambda decoder, oparg: [I.BinaryOp(operation)]

register_all({
    'UNARY_POSITIVE': op.pos,
    'UNARY_NEGATIVE': op.neg,
    'UNARY_INVERT': op.invert,
}, unary_op)

register_all({
    'BINARY_MULTIPLY': op.mul,
    'BINARY_TRUE_DIVIDE': op.truediv,
    'BINARY_FLOOR_DIVIDE': op.floordiv,
    'BINARY_MODULO': op.mod,
    'BINARY_ADD': op.add,
    'BINARY_SUBTRACT': op.sub,
    'BINARY_SUBSCR': op.getitem,
    'BINARY_LSHIFT': op.lshift,
    'BINARY_RSHIFT': op.rshift,
    'BINARY_AND': op.and_,
    'BINARY_XOR': op.xor,
    'BINARY_OR': op.or_,
    'INPLACE_MULTIPLY': op.inplace_mul,
    'INPLACE_TRUE_DIVIDE': op.inplace_truediv,
    'INPLACE_FLOOR_DIVIDE': op.inplace_floordiv,
    'INPLACE_MODULO': op.inplace_mod,
    'INPLACE_ADD': op.inplace_add,
    'INPLACE_SUBTRACT': op.inplace_sub,
    'INPLACE_LSHIFT': op.inplace_lshift,
    'INPLACE_RSHIFT': op.inplace_rshift,
    'INPLACE_AND': op.inplace_and,
    'INPLACE_XOR': op.inplace_xor,
    'INPLACE_OR': op.inplace_or,
}, binary_op)

decodes('UNARY_NOT')(no_operand(I.UnaryNot))

COMPARE_OPS = ['lt', 'le', 'eq', 'ne', 'gt', 'ge']

@decodes('COMPARE_OP')
def decode_compare_op(decoder, oparg):
    if not 0 <= oparg < len(COMPARE_OPS):
        raise BytecodeCorruption("bad COMPARE_OP %d" % (oparg,))
    return [I.Compare(COMPARE_OPS[oparg])]

@decodes('IS_OP')
def decode_is_op(decoder, oparg):
    return [I.Compare('is_not' if oparg else 'is')]

@decodes('CONTAINS_OP')
def decode_contains_op(decoder, oparg):
    return [I.Compare('not_in' if oparg else 'in')]

def unsupported(what):
    return lambda decoder, oparg: [
        I.Unsupported("%s is not RPython" % (what,))]

register_all({
    'BINARY_POWER': "a ** b",
    'INPLACE_POWER': 'a **= b',
    'BINARY_MATRIX_MULTIPLY': 'a @ b',
    'INPLACE_MATRIX_MULTIPLY': 'a @= b',
    'LOAD_BUILD_CLASS': 'defining classes inside functions',
    'STORE_NAME': 'modifying globals',
    'IMPORT_STAR': 'import *',
    'DELETE_GLOBAL': 'modifying globals',
    'DELETE_NAME': 'modifying globals',
    'DELETE_ATTR': 'deleting attributes',
    'BUILD_SET': 'building sets',
    'SET_ADD': 'set comprehensions',
    'SET_UPDATE': 'building sets',
    'MAP_ADD': 'dict comprehensions',
    'DICT_MERGE': 'dict unpacking',
    'DICT_UPDATE': 'dict unpacking',
    'LIST_EXTEND': 'iterable unpacking',
    'LIST_TO_TUPLE': 'iterable unpacking',
    'UNPACK_EX': 'iterable unpacking',
    'BUILD_STRING': 'f-strings',
    'FORMAT_VALUE': 'f-strings',
    'YIELD_FROM': 'yield from',
    'GET_YIELD_FROM_ITER': 'yield from',
    'GET_AWAITABLE': 'await',
    'GET_AITER': 'async for',
    'GET_ANEXT': 'async for',
    'END_ASYNC_FOR': 'async for',
    'BEFORE_ASYNC_WITH': 'async with',
    'CHECK_EG_MATCH': 'except*',
    'PREP_RERAISE_STAR': 'except*',
    'MATCH_CLASS': 'match statement',
    'MATCH_KEYS': 'match statement',
    'MATCH_MAPPING': 'match statement',
    'MATCH_SEQUENCE': 'match statement',
    'COPY_DICT_WITHOUT_KEYS': 'match statement',
    'GET_LEN': 'match statement',
    'SETUP_ANNOTATIONS': 'annotations',
}, unsupported)

@decodes('PRINT_EXPR', 'LOAD_CLASSDEREF', 'LOAD_REVDB_VAR')
def decode_unsupported_operation(decoder, oparg):
    return [I.Unsupported("This operation is not RPython")]

# ____________________________________________________________
# Stack manipulation

decodes('POP_TOP')(no_operand(I.PopTop))
decodes('DUP_TOP')(lambda decoder, oparg: [I.Copy(1)])
decodes('DUP_TOP_TWO')(lambda decoder, oparg: [I.Copy(2), I.Copy(2)])
decodes('ROT_TWO')(lambda decoder, oparg: [I.Swap(2)])
decodes('ROT_THREE')(lambda decoder, oparg: [I.Swap(3), I.Swap(2)])
decodes('ROT_FOUR')(lambda decoder, oparg: [I.Swap(4), I.Swap(3), I.Swap(2)])
decodes('SWAP')(with_oparg(I.Swap))
decodes('NOP')(lambda decoder, oparg: [])

# ____________________________________________________________
# Containers

register_all({
    'BUILD_TUPLE': I.BuildTuple,
    'BUILD_LIST': I.BuildList,
    'LIST_APPEND': I.ListAppend,
    'UNPACK_SEQUENCE': I.UnpackSequence,
}, with_oparg)

register_all({
    'BUILD_LIST_FROM_ARG': I.BuildListFromArg,
    'STORE_SUBSCR': I.StoreSubscr,
    'DELETE_SUBSCR': I.DeleteSubscr,
}, no_operand)

@decodes('BUILD_MAP')
def decode_build_map(decoder, oparg):
    if oparg == 0:
        return [I.BuildMap()]
    return [I.BuildMapFromItems(oparg)]

@decodes('BUILD_SLICE')
def decode_build_slice(decoder, oparg):
    if oparg not in (2, 3):
        raise BytecodeCorruption("bad BUILD_SLICE %d" % (oparg,))
    return [I.BuildSlice(oparg == 3)]

# ____________________________________________________________
# Calls and functions

decodes('CALL_FUNCTION', 'CALL_METHOD')(with_oparg(I.Call))

@decodes('MAKE_FUNCTION')
def decode_make_function(decoder, oparg):
    if oparg & 0x08:
        raise ValueError(CLOSURE_ERROR % (decoder.root.code,))
    if oparg & ~0x01:
        return [I.Unsupported("Dynamically created function must not have"
                              " keyword-only defaults or annotations.")]
    if oparg:
        return [I.MakeFunctionWithDefaults()]
    return [I.MakeFunction(0)]

# ____________________________________________________________
# Control flow

register_all({
    'JUMP_FORWARD': I.Jump,
    'JUMP_ABSOLUTE': I.Jump,
    'FOR_ITER': I.ForIter,
    'JUMP_IF_NOT_EXC_MATCH': I.JumpIfNotExcMatch,
}, with_oparg)

register_all({
    'GET_ITER': I.GetIter,
    'RETURN_VALUE': I.ReturnValue,
    'YIELD_VALUE': I.YieldValue,
    'PUSH_EXC_INFO': I.PushExcInfo,
    'POP_EXCEPT': I.PopExcept,
    'CHECK_EXC_MATCH': I.CheckExcMatch,
    'RERAISE': I.Reraise,
    'BEFORE_WITH': I.BeforeWith,
    'WITH_EXCEPT_START': I.WithExceptStart,
}, no_operand)

def conditional_jump(cls, cond):
    return lambda decoder, oparg: [cls(cond, oparg)]

decodes('POP_JUMP_IF_FALSE')(conditional_jump(I.PopJumpIf, False))
decodes('POP_JUMP_IF_TRUE')(conditional_jump(I.PopJumpIf, True))
decodes('JUMP_IF_FALSE_OR_POP')(conditional_jump(I.JumpIfOrPop, False))
decodes('JUMP_IF_TRUE_OR_POP')(conditional_jump(I.JumpIfOrPop, True))
decodes('POP_JUMP_FORWARD_IF_NONE')(conditional_jump(I.PopJumpIfNone, True))
decodes('POP_JUMP_FORWARD_IF_NOT_NONE')(
    conditional_jump(I.PopJumpIfNone, False))

@decodes('COPY')
def decode_copy(decoder, oparg):
    """COPY has no operand on PyPy: it is the COPY 3 of CPython, which the
    handlers that restore the previous exception start with."""
    return [I.Copy(3)]

@decodes('RAISE_VARARGS')
def decode_raise_varargs(decoder, oparg):
    if oparg == 2:
        return [I.PopTop(), I.Py2Raise(1)]
    return [I.Py2Raise(oparg)]

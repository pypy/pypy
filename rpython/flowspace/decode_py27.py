"""
Decoder for the Python 2.7 bytecode of the host, CPython 2.7 or PyPy2.
"""
import opcode as _host_opcode

from rpython.flowspace import instr as I
from rpython.flowspace.bytecode import BytecodeCorruption, LineTable
from rpython.flowspace.decoder import Decoder
from rpython.flowspace.operation import op

OPMAP = _host_opcode.opmap
OPNAMES = dict((num, name) for name, num in OPMAP.items())
HAVE_ARGUMENT = 90
EXTENDED_ARG = OPMAP['EXTENDED_ARG']
HASJREL = set(_host_opcode.hasjrel)


class Py2Decoder(Decoder):
    """Decoder for the bytecode of CPython 2.7 and PyPy2."""

    opcodes = {}    # filled by @decodes below

    def read(self):
        """Yield (offset, opcode name, oparg) for each host instruction,
        with relative jumps converted to absolute offsets. The name is
        None for unknown opcodes."""
        co_code = self.code.co_code
        offset = 0
        end = len(co_code)
        while offset < end:
            opnum = ord(co_code[offset])
            next_offset = offset + 1
            if opnum >= HAVE_ARGUMENT:
                oparg = (ord(co_code[next_offset]) |
                         (ord(co_code[next_offset + 1]) << 8))
                next_offset += 2
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
            if opnum in HASJREL:
                oparg += next_offset
            yield offset, OPNAMES.get(opnum), oparg
            offset = next_offset

    def unknown_opcode(self, name, oparg):
        if name is None:
            return [I.Unsupported("??? is not RPython")]
        return Decoder.unknown_opcode(self, name, oparg)

    def linetable(self):
        tab = self.code.co_lnotab
        addr = 0
        line = self.code.co_firstlineno
        starts = [(0, line)]
        for i in range(0, len(tab), 2):
            addr += ord(tab[i])
            line += ord(tab[i + 1])
            if starts[-1][0] == addr:
                starts[-1] = (addr, line)
            else:
                starts.append((addr, line))
        return LineTable(self.code.co_firstlineno, starts)


def decodes(*names):
    """Register the decorated function in Py2Decoder.opcodes."""
    def register(func):
        for name in names:
            Py2Decoder.opcodes[name] = func
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

def register_all(table, make_decoder):
    for name, value in table.items():
        decodes(name)(make_decoder(value))

# ____________________________________________________________
# Variables and names

register_all({
    'LOAD_FAST': I.LoadFast,
    'STORE_FAST': I.StoreFast,
    'DELETE_FAST': I.DeleteFast,
    'LOAD_DEREF': I.LoadDeref,
}, with_oparg)

register_all({
    'LOAD_GLOBAL': I.LoadGlobal,
    'LOAD_NAME': I.LoadGlobal,
    'LOAD_ATTR': I.LoadAttr,
    'LOOKUP_METHOD': I.LoadAttr,
    'STORE_ATTR': I.StoreAttr,
    'IMPORT_NAME': I.ImportName,
    'IMPORT_FROM': I.ImportFrom,
}, with_name)

@decodes('LOAD_CONST')
def decode_load_const(decoder, oparg):
    return [I.LoadConst(decoder.code.co_consts[oparg])]

@decodes('STORE_GLOBAL')
def decode_store_global(decoder, oparg):
    return [I.Unsupported("Attempting to modify global variable  %r."
                          % (decoder.code.co_names[oparg],))]

# ____________________________________________________________
# Operators and unsupported opcodes

def unary_op(operation):
    return lambda decoder, oparg: [I.UnaryOp(operation)]

def binary_op(operation):
    return lambda decoder, oparg: [I.BinaryOp(operation)]

register_all({
    'UNARY_POSITIVE': op.pos,
    'UNARY_NEGATIVE': op.neg,
    'UNARY_CONVERT': op.repr,
    'UNARY_INVERT': op.invert,
}, unary_op)

register_all({
    'BINARY_MULTIPLY': op.mul,
    'BINARY_TRUE_DIVIDE': op.truediv,
    'BINARY_FLOOR_DIVIDE': op.floordiv,
    'BINARY_DIVIDE': op.div,
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
    'INPLACE_DIVIDE': op.inplace_div,
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

COMPARE_OPS = ['lt', 'le', 'eq', 'ne', 'gt', 'ge', 'in', 'not_in', 'is',
               'is_not', 'exc_match']

@decodes('COMPARE_OP')
def decode_compare_op(decoder, oparg):
    if not 0 <= oparg < len(COMPARE_OPS):
        raise BytecodeCorruption("bad COMPARE_OP %d" % (oparg,))
    return [I.Compare(COMPARE_OPS[oparg])]

def unsupported(what):
    return lambda decoder, oparg: [
        I.Unsupported("%s is not RPython" % (what,))]

register_all({
    'BINARY_POWER': "a ** b",
    'INPLACE_POWER': 'a **= b',
    'BUILD_CLASS': 'defining classes inside functions',
    'EXEC_STMT': 'exec statement',
    'STOP_CODE': '???',
    'STORE_NAME': 'modifying globals',
    'LOAD_LOCALS': 'locals()',
    'IMPORT_STAR': 'import *',
    'DELETE_GLOBAL': 'modifying globals',
    'DELETE_NAME': 'modifying globals',
    'DELETE_ATTR': 'deleting attributes',
    'BUILD_SET': 'building sets',
    'SET_ADD': 'set comprehensions',
    'MAP_ADD': 'dict comprehensions',
}, unsupported)

@decodes('PRINT_EXPR', 'PRINT_ITEM_TO', 'PRINT_NEWLINE_TO', 'STORE_DEREF',
         'LOAD_CLOSURE', 'MAKE_CLOSURE', 'LOAD_REVDB_VAR')
def decode_unsupported_operation(decoder, oparg):
    return [I.Unsupported("This operation is not RPython")]

# ____________________________________________________________
# Stack manipulation

decodes('POP_TOP')(no_operand(I.PopTop))
decodes('DUP_TOP')(lambda decoder, oparg: [I.Copy(1)])
decodes('DUP_TOPX')(
    lambda decoder, oparg: [I.Copy(oparg) for _ in range(oparg)])
decodes('ROT_TWO')(lambda decoder, oparg: [I.Swap(2)])
decodes('ROT_THREE')(lambda decoder, oparg: [I.Swap(3), I.Swap(2)])
decodes('ROT_FOUR')(lambda decoder, oparg: [I.Swap(4), I.Swap(3), I.Swap(2)])
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
    'BUILD_MAP': I.BuildMap,
    'BUILD_LIST_FROM_ARG': I.BuildListFromArg,
    'STORE_MAP': I.StoreMap,
    'STORE_SUBSCR': I.StoreSubscr,
    'DELETE_SUBSCR': I.DeleteSubscr,
}, no_operand)

@decodes('BUILD_SLICE')
def decode_build_slice(decoder, oparg):
    if oparg not in (2, 3):
        raise BytecodeCorruption("bad BUILD_SLICE %d" % (oparg,))
    return [I.BuildSlice(oparg == 3)]

def slice_op(cls, n):
    """Decoder for SLICE+n and the like: bit 0 of n means that there is a
    start index on the stack, bit 1 a stop index."""
    return lambda decoder, oparg: [cls(bool(n & 1), bool(n & 2))]

for _n in range(4):
    decodes('SLICE+%d' % _n)(slice_op(I.GetSlice, _n))
    decodes('STORE_SLICE+%d' % _n)(slice_op(I.StoreSlice, _n))
    decodes('DELETE_SLICE+%d' % _n)(slice_op(I.DeleteSlice, _n))

# ____________________________________________________________
# Calls and functions

@decodes('CALL_FUNCTION', 'CALL_METHOD')
def decode_call_function(decoder, oparg):
    return [I.Py2Call(oparg & 0xff, (oparg >> 8) & 0xff, False, False)]

@decodes('CALL_FUNCTION_VAR')
def decode_call_function_var(decoder, oparg):
    return [I.Py2Call(oparg & 0xff, (oparg >> 8) & 0xff, True, False)]

@decodes('CALL_FUNCTION_KW')
def decode_call_function_kw(decoder, oparg):
    return [I.Py2Call(oparg & 0xff, (oparg >> 8) & 0xff, False, True)]

@decodes('CALL_FUNCTION_VAR_KW')
def decode_call_function_var_kw(decoder, oparg):
    return [I.Py2Call(oparg & 0xff, (oparg >> 8) & 0xff, True, True)]

decodes('MAKE_FUNCTION')(with_oparg(I.MakeFunction))

# ____________________________________________________________
# Control flow

register_all({
    'JUMP_FORWARD': I.Jump,
    'JUMP_ABSOLUTE': I.Jump,
    'FOR_ITER': I.ForIter,
    'SETUP_LOOP': I.SetupLoop,
    'SETUP_EXCEPT': I.SetupExcept,
    'SETUP_FINALLY': I.SetupFinally,
    'SETUP_WITH': I.SetupWith,
    'CONTINUE_LOOP': I.ContinueLoop,
    'RAISE_VARARGS': I.Py2Raise,
}, with_oparg)

register_all({
    'GET_ITER': I.GetIter,
    'RETURN_VALUE': I.ReturnValue,
    'YIELD_VALUE': I.YieldValue,
    'POP_BLOCK': I.PopBlock,
    'BREAK_LOOP': I.BreakLoop,
    'END_FINALLY': I.EndFinally,
    'WITH_CLEANUP': I.WithCleanup,
    'PRINT_ITEM': I.PrintItem,
    'PRINT_NEWLINE': I.PrintNewline,
}, no_operand)

def conditional_jump(cls, cond):
    return lambda decoder, oparg: [cls(cond, oparg)]

decodes('POP_JUMP_IF_FALSE')(conditional_jump(I.PopJumpIf, False))
decodes('POP_JUMP_IF_TRUE')(conditional_jump(I.PopJumpIf, True))
decodes('JUMP_IF_FALSE_OR_POP')(conditional_jump(I.JumpIfOrPop, False))
decodes('JUMP_IF_TRUE_OR_POP')(conditional_jump(I.JumpIfOrPop, True))

# assert statements are always kept
decodes('JUMP_IF_NOT_DEBUG')(lambda decoder, oparg: [])

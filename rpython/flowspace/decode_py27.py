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
HASJABS = set(_host_opcode.hasjabs)


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
        # Temporary: run the opcode with the FlowContext method of the
        # same name.
        methodname = name.replace('+', '_')
        if OPMAP[name] in HASJREL or OPMAP[name] in HASJABS:
            return [I.HostJumpOpcode(methodname, oparg)]
        return [I.HostOpcode(methodname, oparg)]

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
        return LineTable(starts)


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

from hypothesis import given, settings
import hypothesis.strategies as st

from pypy.interpreter.astcompiler.assemble import (
    Instruction, _remove_redundant_nops, Block, _encode_varint)
from pypy.interpreter.pycode import _decode_varint
from pypy.tool import stdlib_opcode as ops


# unit tests for remove_redundant_nops

def create(*args):
    assert len(args) % 2 == 0
    res = []
    for i in range(0, len(args), 2):
        res.append(Instruction(args[i], position_info=(args[i+1], -1, -1, -1)))
    block = Block()
    block.instructions = res
    block.next_block = Block()
    return block

def check(block, *args):
    _remove_redundant_nops(block)
    assert len(args) % 2 == 0
    got = []
    for op in block.instructions:
        got.append(op.opcode)
        got.append(op.position_info[0])
    assert got == list(args)



def test_remove_redundant_nops():
    # chains of nops removed to one
    block = create(
        ops.NOP, 1,
        ops.NOP, 1,
        ops.NOP, 1,
        ops.NOP, 1,
        ops.NOP, 1,
        ops.NOP, 2,
        ops.NOP, 2,
        ops.NOP, 2,
    )
    check(block, ops.NOP, 1, ops.NOP, 2)

    # nops without position get removed
    block = create(
        ops.NOP, 1,
        ops.NOP, 1,
        ops.NOP, -1,
        ops.NOP, 1,
        ops.NOP, 1,
        ops.NOP, -1,
        ops.NOP, 2,
        ops.NOP, -1,
        ops.NOP, 2,
        ops.NOP, -1,
        ops.NOP, 2,
        ops.NOP, -1,
    )
    check(block, ops.NOP, 1, ops.NOP, 2)

    # nops with the same line as a non-nop op get removed
    block = create(
        ops.POP_TOP, 1,
        ops.NOP, 1,
    )
    check(block, ops.POP_TOP, 1)
    block = create(
        ops.NOP, 1,
        ops.POP_TOP, 1,
    )
    check(block, ops.POP_TOP, 1)


# varint encode/decode round-trip tests

@given(st.integers(min_value=0, max_value=2**30))
def test_varint_roundtrip(value):
    result = []
    _encode_varint(result, value)
    decoded, new_i = _decode_varint(''.join(result), 0)
    assert decoded == value
    assert new_i == len(result)


@given(st.lists(st.integers(min_value=0, max_value=2**30), min_size=1, max_size=8))
def test_varint_sequence_roundtrip(values):
    # Encode a sequence of varints and decode them back in order.
    result = []
    for v in values:
        _encode_varint(result, v)
    table = ''.join(result)
    i = 0
    for v in values:
        decoded, i = _decode_varint(table, i)
        assert decoded == v
    assert i == len(table)


# tests that do precise checks on the shape of generated assembly

class TestInstructionDetails(object):
    def compile_ast_to_blocks(self, src, mode="exec"):
        from pypy.interpreter.pyparser import pyparse
        from pypy.interpreter.astcompiler import ast, assemble, symtable, optimize, codegen
        space = self.space
        p = pyparse.PegParser(space)
        info = pyparse.CompileInfo("<test>", mode)
        ast = p.parse_source(src, info)
        module = optimize.optimize_ast(space, ast, info)
        symbols = symtable.SymtableBuilder(space, module, info)
        generator = codegen.TopLevelCodeGenerator(space, module, symbols, info)
        pycode = generator.assemble()
        return pycode, generator._final_blocks

    def extract_opnames(self, blocks):
        res = []
        for block in blocks:
            for instr in block.instructions:
                res.append(ops.opname[instr.opcode])
        return res

    def test_match_uses_accept_jump_if(self):
        code, blocks = self.compile_ast_to_blocks("""match x:
    case [a] if not a:
        f()
    case _:
        g()
""")
        opnames = self.extract_opnames(blocks)
        assert "UNARY_NOT" not in opnames

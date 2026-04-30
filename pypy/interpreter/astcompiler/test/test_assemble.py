from hypothesis import given, settings
import hypothesis.strategies as st

from pypy.interpreter.astcompiler.assemble import (
    Instruction, _remove_redundant_nops, Block, _encode_varint,
    _apply_static_swaps, _SETUP_FINALLY)
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


# unit tests for apply_static_swaps

def make_block(*opcodes_and_args):
    """Build a single Block from (opcode, arg, lineno) triples."""
    block = Block()
    for opcode, arg, lineno in opcodes_and_args:
        instr = Instruction(opcode, arg, position_info=(lineno, -1, -1, -1))
        block.instructions.append(instr)
    return block

def opcodes(block):
    return [instr.opcode for instr in block.instructions]

def run_static_swaps(block):
    instructions = block.instructions
    for i in range(len(instructions)):
        if instructions[i].opcode == ops.SWAP:
            _apply_static_swaps(instructions, i)


def test_static_swaps_no_swap():
    # no SWAP present: instructions unchanged
    block = make_block(
        (ops.STORE_FAST, 0, 1),
        (ops.STORE_FAST, 1, 1),
    )
    run_static_swaps(block)
    assert opcodes(block) == [ops.STORE_FAST, ops.STORE_FAST]

def test_static_swaps_swap2_two_store_fast():
    # SWAP(2) + STORE_FAST a + STORE_FAST b -> NOP + STORE_FAST b + STORE_FAST a
    block = make_block(
        (ops.SWAP, 2, 1),
        (ops.STORE_FAST, 0, 1),
        (ops.STORE_FAST, 1, 1),
    )
    run_static_swaps(block)
    instrs = block.instructions
    assert instrs[0].opcode == ops.NOP
    assert instrs[1].opcode == ops.STORE_FAST and instrs[1].arg == 1
    assert instrs[2].opcode == ops.STORE_FAST and instrs[2].arg == 0

def test_static_swaps_swap2_pop_top_store_fast():
    # SWAP(2) + POP_TOP + STORE_FAST -> NOP + STORE_FAST + POP_TOP
    block = make_block(
        (ops.SWAP, 2, 1),
        (ops.POP_TOP, 0, 1),
        (ops.STORE_FAST, 5, 1),
    )
    run_static_swaps(block)
    instrs = block.instructions
    assert instrs[0].opcode == ops.NOP
    assert instrs[1].opcode == ops.STORE_FAST and instrs[1].arg == 5
    assert instrs[2].opcode == ops.POP_TOP

def test_static_swaps_swap2_two_pop_top():
    # SWAP(2) + POP_TOP + POP_TOP -> NOP + POP_TOP + POP_TOP (order unchanged, both POP_TOP)
    block = make_block(
        (ops.SWAP, 2, 1),
        (ops.POP_TOP, 0, 1),
        (ops.POP_TOP, 0, 1),
    )
    run_static_swaps(block)
    instrs = block.instructions
    assert instrs[0].opcode == ops.NOP
    assert instrs[1].opcode == ops.POP_TOP
    assert instrs[2].opcode == ops.POP_TOP

def test_static_swaps_swap_n_greater_than_2():
    # SWAP(3): j=first swappable, k=third swappable; swap them
    block = make_block(
        (ops.SWAP, 3, 1),
        (ops.STORE_FAST, 0, 1),
        (ops.STORE_FAST, 1, 1),
        (ops.STORE_FAST, 2, 1),
    )
    run_static_swaps(block)
    instrs = block.instructions
    assert instrs[0].opcode == ops.NOP
    assert instrs[1].arg == 2  # swapped with k
    assert instrs[2].arg == 1  # unchanged
    assert instrs[3].arg == 0  # swapped with j

def test_static_swaps_no_followers():
    # SWAP at end of block: j not found, no change
    block = make_block(
        (ops.SWAP, 2, 1),
    )
    run_static_swaps(block)
    assert opcodes(block) == [ops.SWAP]

def test_static_swaps_follower_not_swappable():
    # SWAP(2) followed by a non-swappable: no change
    block = make_block(
        (ops.SWAP, 2, 1),
        (ops.LOAD_FAST, 0, 1),
        (ops.STORE_FAST, 1, 1),
    )
    run_static_swaps(block)
    assert opcodes(block) == [ops.SWAP, ops.LOAD_FAST, ops.STORE_FAST]

def test_static_swaps_not_enough_swappables():
    # SWAP(3) but only one swappable follower: k not found, no change
    block = make_block(
        (ops.SWAP, 3, 1),
        (ops.STORE_FAST, 0, 1),
        (ops.LOAD_FAST, 1, 1),
        (ops.STORE_FAST, 2, 1),
    )
    run_static_swaps(block)
    assert opcodes(block) == [ops.SWAP, ops.STORE_FAST, ops.LOAD_FAST, ops.STORE_FAST]

def test_static_swaps_conflict_same_var():
    # j and k both STORE_FAST to the same variable: no change
    block = make_block(
        (ops.SWAP, 2, 1),
        (ops.STORE_FAST, 7, 1),
        (ops.STORE_FAST, 7, 1),
    )
    run_static_swaps(block)
    assert opcodes(block) == [ops.SWAP, ops.STORE_FAST, ops.STORE_FAST]

def test_static_swaps_conflict_intermediate_store():
    # SWAP(3): j stores to var 0, k stores to var 2, but instructions[j+1]
    # also stores to var 0 -> conflict, no change
    block = make_block(
        (ops.SWAP, 3, 1),
        (ops.STORE_FAST, 0, 1),
        (ops.STORE_FAST, 0, 1),
        (ops.STORE_FAST, 2, 1),
    )
    run_static_swaps(block)
    assert opcodes(block) == [ops.SWAP, ops.STORE_FAST, ops.STORE_FAST, ops.STORE_FAST]

def test_static_swaps_nop_skipped():
    # NOP between SWAP and swappables is transparent
    block = make_block(
        (ops.SWAP, 2, 1),
        (ops.NOP, 0, 1),
        (ops.STORE_FAST, 0, 1),
        (ops.STORE_FAST, 1, 1),
    )
    run_static_swaps(block)
    instrs = block.instructions
    assert instrs[0].opcode == ops.NOP        # was SWAP
    assert instrs[1].opcode == ops.NOP        # original NOP
    assert instrs[2].arg == 1                 # swapped
    assert instrs[3].arg == 0                 # swapped

def test_static_swaps_pseudo_op_skipped():
    # pseudo-op between SWAP and swappables is transparent
    block = make_block(
        (ops.SWAP, 2, 1),
        (_SETUP_FINALLY, 0, 1),
        (ops.STORE_FAST, 0, 1),
        (ops.STORE_FAST, 1, 1),
    )
    run_static_swaps(block)
    instrs = block.instructions
    assert instrs[0].opcode == ops.NOP
    assert instrs[2].arg == 1
    assert instrs[3].arg == 0

def test_static_swaps_lineno_mismatch_stops_k_search():
    # SWAP(3): j is on line 1, but the next candidate for k is on line 2 -> no change
    block = make_block(
        (ops.SWAP, 3, 1),
        (ops.STORE_FAST, 0, 1),
        (ops.STORE_FAST, 1, 2),
        (ops.STORE_FAST, 2, 1),
    )
    run_static_swaps(block)
    assert opcodes(block) == [ops.SWAP, ops.STORE_FAST, ops.STORE_FAST, ops.STORE_FAST]

def test_static_swaps_backwards_scan_through_swappable():
    # When scanning backwards, a STORE_FAST before the SWAP is allowed (scan continues).
    # STORE_FAST(a), SWAP(2), STORE_FAST(b), STORE_FAST(c):
    # Called at i=1 (SWAP): process SWAP -> NOP, swap b/c.
    # i decremented to 0: STORE_FAST is swappable -> continue.
    # i decremented to -1: loop ends. Result: STORE_FAST(a), NOP, STORE_FAST(c), STORE_FAST(b).
    block = make_block(
        (ops.STORE_FAST, 0, 1),
        (ops.SWAP, 2, 1),
        (ops.STORE_FAST, 1, 1),
        (ops.STORE_FAST, 2, 1),
    )
    run_static_swaps(block)
    instrs = block.instructions
    assert instrs[0].opcode == ops.STORE_FAST and instrs[0].arg == 0
    assert instrs[1].opcode == ops.NOP
    assert instrs[2].arg == 2
    assert instrs[3].arg == 1

def test_static_swaps_backwards_scan_stops_at_non_swappable():
    # A non-swappable, non-SWAP before the SWAP stops the backwards scan early.
    # LOAD_FAST, SWAP(2), STORE_FAST(a), STORE_FAST(b):
    # Called at i=1: process SWAP -> NOP, swap a/b.
    # i=0: LOAD_FAST is not swappable -> return.
    block = make_block(
        (ops.LOAD_FAST, 9, 1),
        (ops.SWAP, 2, 1),
        (ops.STORE_FAST, 0, 1),
        (ops.STORE_FAST, 1, 1),
    )
    run_static_swaps(block)
    instrs = block.instructions
    assert instrs[0].opcode == ops.LOAD_FAST
    assert instrs[1].opcode == ops.NOP
    assert instrs[2].arg == 1
    assert instrs[3].arg == 0


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

@given(st.integers(min_value=0, max_value=2**30))
def test_varint_roundtrip_msb(value):
    result = []
    _encode_varint(result, value, msb=0x80)
    decoded, new_i = _decode_varint(''.join(result), 0)
    assert decoded == value
    assert new_i == len(result)


@given(st.lists(st.integers(min_value=0, max_value=2**30), min_size=1, max_size=8))
def test_varint_sequence_roundtrip_msb(values):
    # Encode a sequence of varints and decode them back in order.
    result = []
    for v in values:
        _encode_varint(result, v, msb=0x80)
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

    def test_copy_emitted_in_except_as(self):
        code, blocks = self.compile_ast_to_blocks("""
try:
    x = 1
except ValueError as e:
    pass
""")
        opnames = self.extract_opnames(blocks)
        assert "COPY" in opnames

    def test_copy_encoding(self):
        code, blocks = self.compile_ast_to_blocks("""
try:
    x = 1
except ValueError as e:
    pass
""")
        co_code = bytearray(code.co_code)
        found = False
        for i in range(0, len(co_code), 2):
            if co_code[i] == ops.COPY and co_code[i + 1] == 3:
                found = True
                break
        assert found, "COPY 3 not found in co_code"

from pypy.interpreter.astcompiler.assemble import Instruction, _remove_redundant_nops
from pypy.tool import stdlib_opcode as ops

def create(*args):
    assert len(args) % 2 == 0
    res = []
    for i in range(0, len(args), 2):
        res.append(Instruction(args[i], position_info=(args[i+1], -1, -1, -1)))
    return res

def check(block, *args):
    _remove_redundant_nops(block)
    assert len(args) % 2 == 0
    got = []
    for op in block:
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

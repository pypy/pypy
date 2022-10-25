from pypy.interpreter.astcompiler import assemble
from pypy.tool import stdlib_opcode as ops


def test_simple_lnotab():
    first_line_number = 5
    block = assemble.Block()
    block.offset = 0
    instr = assemble.Instruction(ops.NOP)
    instr.lineno = first_line_number + 1
    instr2 = assemble.Instruction(ops.NOP)
    instr2.lineno = first_line_number + 1 + 3
    instr3 = assemble.Instruction(ops.NOP)
    instr3.lineno = first_line_number + 1
    block.instructions.extend([instr, instr2, instr3])
    blocks = [block]

    lnotab = assemble.PythonCodeMaker._build_lnotab(blocks, first_line_number)

    assert lnotab == b"\x00\x01\x02\x03\x02\xFD"

def test_simple_linetable():
    first_line_number = 5
    block = assemble.Block()
    block.offset = 0
    instr = assemble.Instruction(ops.NOP)
    instr.lineno = first_line_number + 1
    instr2 = assemble.Instruction(ops.NOP)
    instr2.lineno = first_line_number + 1 + 3
    instr3 = assemble.Instruction(ops.NOP)
    instr3.lineno = first_line_number + 1
    block.instructions.extend([instr, instr2, instr3])
    blocks = [block]

    linetable = assemble.PythonCodeMaker._build_linetable(blocks, first_line_number)

    assert linetable == b""

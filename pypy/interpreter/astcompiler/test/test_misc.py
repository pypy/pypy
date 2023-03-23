from pypy.interpreter.astcompiler.misc import mangle
from pypy.interpreter.astcompiler.assemble import Instruction, ops, Block
from pypy.interpreter.location import _encode_lnotab_pair
from pypy.interpreter.astcompiler.codegen import compute_reordering, rot_n


def test_mangle():
    assert mangle("foo", "Bar") == "foo"
    assert mangle("__foo__", "Bar") == "__foo__"
    assert mangle("foo.baz", "Bar") == "foo.baz"
    assert mangle("__", "Bar") == "__"
    assert mangle("___", "Bar") == "___"
    assert mangle("____", "Bar") == "____"
    assert mangle("__foo", "Bar") == "_Bar__foo"
    assert mangle("__foo", "_Bar") == "_Bar__foo"
    assert mangle("__foo", "__Bar") == "_Bar__foo"
    assert mangle("__foo", "___") == "__foo"
    assert mangle("___foo", "__Bar") == "_Bar___foo"

def test_instruction_size():
    assert Instruction(ops.POP_TOP).size() == 2
    assert Instruction(ops.LOAD_FAST, 23).size() == 2
    assert Instruction(ops.LOAD_FAST, 0xfff0).size() == 4
    assert Instruction(ops.LOAD_FAST, 0x10000).size() == 6
    assert Instruction(ops.LOAD_FAST, 0x1000000).size() == 8

def test_instruction_encode():
    c = []
    Instruction(ops.POP_TOP).encode(c)
    assert c == [chr(ops.POP_TOP), '\x00']

    c = []
    Instruction(ops.LOAD_FAST, 1).encode(c)
    assert c == [chr(ops.LOAD_FAST), '\x01']

    c = []
    Instruction(ops.LOAD_FAST, 0x201).encode(c)
    assert c == [chr(ops.EXTENDED_ARG), '\x02', chr(ops.LOAD_FAST), '\x01']

    c = []
    Instruction(ops.LOAD_FAST, 0x30201).encode(c)
    assert c == [chr(ops.EXTENDED_ARG), '\x03', chr(ops.EXTENDED_ARG), '\x02', chr(ops.LOAD_FAST), '\x01']

    c = []
    Instruction(ops.LOAD_FAST, 0x5030201).encode(c)
    assert c == [chr(ops.EXTENDED_ARG), '\x05', chr(ops.EXTENDED_ARG), '\x03', chr(ops.EXTENDED_ARG), '\x02', chr(ops.LOAD_FAST), '\x01']

def test_encode_lnotab_pair():
    l = []
    _encode_lnotab_pair(0, 1, l)
    assert l == ["\x00", "\x01"]

    l = []
    _encode_lnotab_pair(4, 1, l)
    assert l == ["\x04", "\x01"]

    l = []
    _encode_lnotab_pair(4, -1, l)
    assert l == ["\x04", "\xff"]

    l = []
    _encode_lnotab_pair(4, 127, l)
    assert l == ["\x04", "\x7f"]

    l = []
    _encode_lnotab_pair(4, 128, l)
    assert l == list("\x04\x7f\x00\x01")

    l = []
    _encode_lnotab_pair(4, -1000, l)
    assert l == list("\x04\x80\x00\x80\x00\x80\x00\x80\x00\x80\x00\x80\x00\x80\x00\x98")

def test_compute_reordering():
    import itertools
    # exhaustive test up to size 8
    for size in range(2, 9):
        target = range(size)
        for perm in itertools.permutations(range(size)):
            if perm[0] == len(perm) - 1:
                continue
            l = list(perm)
            rots = compute_reordering(l)
            l = list(perm)
            for rot in rots:
                rot_n(l, rot)
            assert l == list(reversed(target))

def jumpinstr(block, opcode, target):
    jump = Instruction(opcode)
    jump.jump = target
    block.instructions.append(jump)
    return jump

def test_jump_thread_remove_jump_to_empty():
    b = Block()
    b2 = Block()
    b3 = Block()
    b4 = Block()
    b2.next_block = b3
    b3.next_block = b4

    jump = jumpinstr(b, ops.JUMP_FORWARD, b2)

    b4.instructions.append(Instruction(ops.NOP))

    b.jump_thread()
    assert jump.jump is b4

def test_jump_thread_jump_to_jump_forward():
    for opcode in (ops.JUMP_FORWARD, ops.JUMP_ABSOLUTE):
        b = Block()
        b2 = Block()
        b3 = Block()

        jump1 = jumpinstr(b, opcode, b2)
        jump2 = jumpinstr(b2, ops.JUMP_FORWARD, b3)
        b3.instructions.append(Instruction(ops.NOP))

        b.jump_thread()
        assert jump1.jump is b3

def test_dont_jump_thread_on_lineno_differences():
    for opcode in (ops.JUMP_FORWARD, ops.JUMP_ABSOLUTE):
        b = Block()
        b2 = Block()
        b3 = Block()

        jump1 = jumpinstr(b, opcode, b2)
        jump1.position_info = (1, -1, -1, -1)
        jump2 = jumpinstr(b2, ops.RETURN_VALUE, b3)
        jump2.position_info = (2, -1, -1, -1)
        b3.instructions.append(Instruction(ops.NOP))

        b.jump_thread()
        assert jump1.jump is b2 # can't thread to not lose line numbers

def test_uncond_jump_despite_lineno_differences():
    for opcode in (ops.JUMP_FORWARD, ops.JUMP_ABSOLUTE):
        b = Block()
        b2 = Block()
        b3 = Block()

        jump1 = jumpinstr(b, opcode, b2)
        jump1.position_info = (1, -1, -1, -1)
        jump2 = jumpinstr(b2, ops.JUMP_FORWARD, b3)
        jump2.position_info = (2, -1, -1, -1)
        instr3 = Instruction(ops.NOP)
        instr3.position_info = (2, -1, -1, -1)
        b3.instructions.append(instr3)

        b.jump_thread()
        assert jump1.jump is b3 # can't thread to not lose line numbers

def test_jump_thread_jump_to_jump_absolute():
    for opcode in (ops.JUMP_FORWARD, ops.JUMP_ABSOLUTE):
        b = Block()
        b2 = Block()
        b3 = Block()

        jump1 = jumpinstr(b, opcode, b2)
        jump2 = jumpinstr(b2, ops.JUMP_ABSOLUTE, b3)
        b3.instructions.append(Instruction(ops.NOP))

        b.jump_thread()
        assert jump1.jump is b3
        assert jump1.opcode == ops.JUMP_ABSOLUTE

def test_jump_thread_jump_to_return():
    for opcode in (ops.JUMP_FORWARD, ops.JUMP_ABSOLUTE):
        b = Block()
        b2 = Block()

        jump1 = jumpinstr(b, opcode, b2)
        jump2 = Instruction(ops.RETURN_VALUE)
        b2.instructions.append(jump2)

        b.jump_thread()
        assert jump1.jump is None
        assert jump1.opcode == ops.RETURN_VALUE

def test_jump_thread_conditional_jump():
    for opcode1 in (ops.POP_JUMP_IF_FALSE, ops.POP_JUMP_IF_TRUE,
            ops.JUMP_IF_FALSE_OR_POP, ops.JUMP_IF_TRUE_OR_POP):
        for opcode2 in (ops.JUMP_FORWARD, ops.JUMP_ABSOLUTE):
            b = Block()
            b2 = Block()
            b3 = Block()

            jump1 = jumpinstr(b, opcode1, b2)
            jump2 = jumpinstr(b2, opcode2, b3)
            b3.instructions.append(Instruction(ops.NOP))

            b.jump_thread()
            assert jump1.jump is b3
            assert jump1.opcode == opcode1

def test_jump_thread_jump_to_jump_to_jump():
    for opcode1 in (ops.POP_JUMP_IF_FALSE, ops.POP_JUMP_IF_TRUE,
            ops.JUMP_IF_FALSE_OR_POP, ops.JUMP_IF_TRUE_OR_POP,
            ops.JUMP_FORWARD, ops.JUMP_ABSOLUTE):
        b = Block()
        b2 = Block()
        b3 = Block()
        b4 = Block()

        jump1 = jumpinstr(b, opcode1, b2)
        jump2 = jumpinstr(b2, ops.JUMP_FORWARD, b3)
        jump3 = jumpinstr(b3, ops.JUMP_FORWARD, b4)
        b4.instructions.append(Instruction(ops.NOP))
        b.jump_thread()
        assert jump1.jump is b4

def test_jump_thread_fallthrough():
    b = Block()
    b.next_block = b2 = Block()
    b2.next_block = b3 = Block()

    b.instructions.append(Instruction(ops.NOP))
    b3.instructions.append(Instruction(ops.NOP))
    b.jump_thread()
    assert b.next_block is b3


def test_block_exits_function():
    for opcode in (ops.RETURN_VALUE, ops.RAISE_VARARGS, ops.RERAISE):
        b = Block()
        b.emit_instr(Instruction(opcode))
        assert b.exits_function
        assert b.cant_add_instructions

import types

import pytest

from rpython.flowspace import instr as I
from rpython.flowspace.decode_py27 import Py2Decoder


def decode(code):
    decoder = Py2Decoder(code)
    instrs = decoder.decode_instructions()
    return instrs


def make_code(co_code, co_consts=(), co_names=()):
    class code:
        pass
    code.co_code = co_code
    code.co_consts = co_consts
    code.co_names = co_names
    return code


def test_jump_targets_are_positions():
    def f(x):
        while x:
            x = x.y
        return x
    instrs = decode(f.__code__)
    offsets = [instr.offset for instr in instrs]
    assert offsets == sorted(offsets)
    for instr in instrs:
        if isinstance(instr, I.JumpInstr):
            assert 0 <= instr.target < len(instrs)
    targets = set([instrs[instr.target].offset for instr in instrs
                   if isinstance(instr, I.JumpInstr)])
    import dis
    assert targets == set(dis.findlabels(f.__code__.co_code))


def test_extended_arg():
    code = make_code('\x91\x01\x00'  # EXTENDED_ARG 1
                     'd\x02\x00'     # LOAD_CONST 0x10002
                     'S',            # RETURN_VALUE
                     co_consts={0x10002: 'abc'})
    instrs = decode(code)
    assert len(instrs) == 2
    assert [instr.offset for instr in instrs] == [0, 6]


def test_linetable():
    from rpython.flowspace import flowcontext, instr
    from rpython.tool.error import offset2lineno
    source = ('def f(x):\n    y = x\n    if x:\n%s        return 1\n'
              '%s    return y\n')
    namespace = {}
    exec(compile(source % ('\n' * 300, '\n' * 1000), '<test>', 'exec'),
         namespace)
    codes = [namespace['f'].__code__]
    for module in [flowcontext, instr]:
        for obj in vars(module).values():
            for func in vars(obj).values() if isinstance(obj, type) else [obj]:
                code = getattr(func, '__code__', None)
                if isinstance(code, types.CodeType):
                    codes.append(code)
    assert len(codes) > 50
    for code in codes:
        table = Py2Decoder(code).linetable()
        for offset in range(len(code.co_code)):
            assert (table.offset2lineno(offset) ==
                    offset2lineno(code, offset))

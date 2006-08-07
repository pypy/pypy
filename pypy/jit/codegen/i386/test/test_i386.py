import py
from pypy.jit.codegen.i386.i386 import *
from pypy.jit.codegen.i386.assembler import CodeBuilder


def test_basic():
    def check(expected, insn, *args):
        s = CodeBuilder()
        insn.encode(s, *args)
        assert s.buffer.getvalue() == expected

    # nop
    yield check, '\x90',                 NOP

    # mov [ebp+19], ecx
    yield check, '\x89\x4D\x13',         MOV, (MODRM, (memBase, (EBP, 19))), \
                                              (ECX, None)
    # add edx, 0x12345678
    yield check, '\x81\xEA\x78\x56\x34\x12', \
                                         SUB, (EDX, None), (IMM32, 0x12345678)

    # mov dh, 1  (inefficient encoding)
    yield check, '\xC6\xC6\x01',         MOV, (MODRM8, (memRegister, (DH,))), \
                                              (IMM8, 1)
    # add esp, 12
    yield check, '\x83\xC4\x0C',         ADD, (ESP, None), (IMM8, 12)

    # mov esp, 12
    yield check, '\xBC\x0C\x00\x00\x00', MOV, (ESP, None), (IMM8, 12)

    # sub esi, ecx
    yield check, '\x29\xCE',             SUB, (ESI, None), (ECX, None)


def test_auto():
    import os
    g = os.popen('as --version')
    data = g.read()
    g.close()
    if not data.startswith('GNU assembler'):
        py.test.skip("full tests require the GNU 'as' assembler")

    from pypy.jit.codegen.i386 import autotest
    def do_test(name, insn):
        print name
        if name in ('CMOVPE', 'CMOVPO'):
            py.test.skip("why doesn't 'as' know about CMOVPE/CMOVPO?")
        if name in ('SHL', 'SHR', 'SAR'):
            py.test.skip("i386 produces a less efficient encoding")
        autotest.complete_test(name, insn)

    items = all_instructions.items()
    items.sort()
    for key, value in items:
        yield do_test, key, value
    del key, value

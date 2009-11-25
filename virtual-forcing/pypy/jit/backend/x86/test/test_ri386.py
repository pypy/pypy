import py
from pypy.jit.backend.x86.ri386 import *

class CodeBuilder(I386CodeBuilder):
    def __init__(self):
        self.buffer = []

    def write(self, data):
        for c in data:
            self.buffer.append(c)    # extend the list of characters

    def tell(self):
        return len(self.buffer)

    def getvalue(self):
        return ''.join(self.buffer)


def test_example():
    s = CodeBuilder()
    s.NOP()
    s.ADD(eax, eax)
    assert s.getvalue() == '\x90\x01\xC0'

def test_modrm():
    assert memregister(ecx).assembler() == '%ecx'
    assert memregister(ebp).assembler() == '%ebp'
    assert memregister(esp).assembler() == '%esp'
    assert memSIB(eax, ebx, 0, 2).assembler() == '2(%eax,%ebx,1)'
    assert memSIB(None, ebx, 1, 2).assembler() == '2(,%ebx,2)'
    assert memSIB(eax, None, 0, 2).assembler() == '2(%eax)'
    assert memSIB(None, None, 0, 2).assembler() == '2'
    assert memSIB(ebp, ebx, 0, 2).assembler() == '2(%ebp,%ebx,1)'
    assert memSIB(ebp, None, 0, 2).assembler() == '2(%ebp)'
    assert memSIB(None, ebp, 1, 2).assembler() == '2(,%ebp,2)'
    assert memSIB(ebp, ebp, 0, 2).assembler() == '2(%ebp,%ebp,1)'
    assert memSIB(eax, ebx, 0, 0).assembler() == '(%eax,%ebx,1)'
    assert memSIB(None, ebx, 1, 0).assembler() == '0(,%ebx,2)'
    assert memSIB(eax, None, 0, 0).assembler() == '(%eax)'
    assert memSIB(None, None, 0, 0).assembler() == '0'
    assert memSIB(ebp, ebx, 0, 0).assembler() == '0(%ebp,%ebx,1)'
    assert memSIB(ebp, None, 0, 0).assembler() == '0(%ebp)'
    assert memSIB(None, ebp, 1, 0).assembler() == '0(,%ebp,2)'
    assert memSIB(ebp, ebp, 0, 0).assembler() == '0(%ebp,%ebp,1)'


def test_basic():
    def check(expected, insn, *args):
        s = CodeBuilder()
        getattr(s, insn)(*args)
        assert s.getvalue() == expected

    # nop
    yield check, '\x90',                     'NOP'
    # mov [ebp+19], ecx
    yield check, '\x89\x4D\x13',             'MOV', mem(ebp, 19), ecx
    # add edx, 0x12345678
    yield check, '\x81\xEA\x78\x56\x34\x12', 'SUB', edx, imm32(0x12345678)
    # mov dh, 1  (inefficient encoding)
    yield check, '\xC6\xC6\x01',             'MOV', memregister8(dh), imm8(1)
    # add esp, 12
    yield check, '\x83\xC4\x0C',             'ADD', esp, imm8(12)
    # mov esp, 12
    yield check, '\xBC\x0C\x00\x00\x00',     'MOV', esp, imm8(12)
    # sub esi, ecx
    yield check, '\x29\xCE',                 'SUB', esi, ecx
    # ret
    yield check, '\xC3',                     'RET'
    # ret 20
    yield check, '\xC2\x14\x00',             'RET', imm16(20)
    # mov eax, [8*ecx]
    yield check, '\x89\x04\xcd\x00\x00\x00\x00', \
                                             'MOV', memSIB(None,ecx,3,0), eax
    # call +17
    yield check, '\xE8\x11\x00\x00\x00',     'CALL', rel32(22)
    # fld
    #yield check, '\xDD\x44\x24\x04', 'FLD', mem(esp, 4)
    # fadd
    #yield check, '\xDC\x44\x24\x08', 'FADD', mem(esp, 8)

##def test_conditional():
##    """Compare the encoding for the instructions JE, JAE, JC etc.,
##    with the encoding for the 'Jcond' pseudo-instruction.
##    """
##    def check(insn, *args):
##        from pypy.jit.codegen.i386.ri386setup import Conditions
##        for cond, value in Conditions.items():
##            s1 = CodeBuilder()
##            getattr(s1, insn+cond)(*args)
##            s2 = CodeBuilder()
##            getattr(s2, insn+'cond')(imm8(value), *args)


def test_translate():
    from pypy.rpython.test.test_llinterp import interpret

    def f():
        s = CodeBuilder()
        s.SUB(esi, ecx)
        s.MOV(mem(ebp, 19), ecx)
        return s.getvalue()

    res = interpret(f, [])
    assert ''.join(res.chars) == '\x29\xCE\x89\x4D\x13'


def test_unpack_compiled():
    from pypy.translator.c.test.test_genc import compile

    def f(n):
        return mem(ebp, n).ofs_relative_to_ebp()

    fn = compile(f, [int])
    for i in [0, 4, 44, 124, 128, 132, 252, 256, 10000000,
              -4, -44, -124, -128, -132, -252, -256, -10000000]:
        assert fn(i) == i

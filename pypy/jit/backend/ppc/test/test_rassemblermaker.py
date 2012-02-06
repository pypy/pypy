from pypy.jit.backend.ppc.rassemblermaker import make_rassembler
from pypy.jit.backend.ppc.ppc_assembler import PPCAssembler

RPPCAssembler = make_rassembler(PPCAssembler)

_a = PPCAssembler()
_a.add(3, 3, 4)
add_r3_r3_r4 = _a.insts[0].assemble()

def test_simple():
    ra = RPPCAssembler()
    ra.add(3, 3, 4)
    assert ra.insts == [add_r3_r3_r4]

def test_rtyped():
    from pypy.rpython.test.test_llinterp import interpret
    def f():
        ra = RPPCAssembler()
        ra.add(3, 3, 4)
        ra.lwz(1, 1, 1)  # ensure that high bit doesn't produce long but r_uint
        return ra.insts[0]
    res = interpret(f, [])
    assert res == add_r3_r3_r4

def test_mnemonic():
    mrs = []
    for A in PPCAssembler, RPPCAssembler:
        a = A()
        a.mr(3, 4)
        mrs.append(a.insts[0])
    assert mrs[0].assemble() == mrs[1]

def test_spr_coding():
    mrs = []
    for A in PPCAssembler, RPPCAssembler:
        a = A()
        a.mtctr(3)
        mrs.append(a.insts[0])
    assert mrs[0].assemble() == mrs[1]

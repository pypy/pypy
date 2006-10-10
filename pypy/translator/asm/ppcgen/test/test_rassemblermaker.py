from pypy.translator.asm.ppcgen.rassemblermaker import make_rassembler
from pypy.translator.asm.ppcgen.ppc_assembler import PPCAssembler

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
        return ra.insts[0]
    res = interpret(f, [])
    assert res == add_r3_r3_r4
    

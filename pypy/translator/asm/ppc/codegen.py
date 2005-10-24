from pypy.translator.asm.model import *

def make_native_code(graph, infreginsns):
    from pypy.translator.asm.ppcgen.func_builder import make_func
    maxregs = 0
    for insn in infreginsns:
        for r in insn.registers_used():
            maxregs = max(r, maxregs)

    from pypy.translator.asm import regalloc, simulator

    insns = regalloc.regalloc(infreginsns, 30)

    #insns = simulator.TranslateProgram(infreginsns, 5)

    codegen = PPCCodeGen()

    return make_func(codegen.assemble(insns), 'i',
                     'i'*len(graph.startblock.inputargs),
                     maxregs)


class PPCCodeGen(object):

    def assemble(self, insns):
        from pypy.translator.asm.ppcgen import ppc_assembler
        A = ppc_assembler.PPCAssembler()

        for i in insns:
            i.ppc_assemble(A)

        return A

class __extend__(LOAD_ARGUMENT):
    def ppc_assemble(self, A):
        assert self.target + 2 == self.argindex + 3

class __extend__(LOAD_IMMEDIATE):
    def ppc_assemble(self, A):
        assert isinstance(self.immed, int)
        assert -30000 < self.immed < 30000
        A.li(self.target + 2, self.immed)

class __extend__(Label):
    def ppc_assemble(self, A):
        A.label(self.name)

class __extend__(JUMP_IF_TRUE):
    def ppc_assemble(self, A):
        # should be "A.bt(BI=0, BD=branch)" but this crashes.
        A.blt(self.target)

class __extend__(JUMP):
    def ppc_assemble(self, A):
        A.b(self.target)

class __extend__(RETPYTHON):
    def ppc_assemble(self, A):
        A.mr(3, self.source + 2)
        A.blr()

class __extend__(MOVE):
    def ppc_assemble(self, A):
        A.mr(self.target + 2, self.source + 2)

class __extend__(STORE_STACK):
    def ppc_assemble(self, A):
        A.stw(self.source+2, 1, 24+4*self.stackindex)

class __extend__(LOAD_STACK):
    def ppc_assemble(self, A):
        A.lwz(self.target+2, 1, 24+4*self.stackindex)

class __extend__(LLInstruction):
    def ppc_assemble(self, A):
        getattr(self, self.opname)(A, self.dest+2,
                                   *[s + 2 for s in self.sources])


    def int_add(self, A, dest, a, b):
        A.add(dest, a, b)

    def int_sub(self, A, dest, a, b):
        A.sub(dest, a, b)

    def int_mul(self, A, dest, a, b):
        A.mullw(dest, a, b)

    def int_mod(self, A, dest, a, b):
        A.divw(dest, a, b)
        A.mullw(dest, dest, b)
        A.subf(dest, dest, a)


    def int_and(self, A, dest, a, b):
        A.and_(dest, a, b)


    def int_gt(self, A, dest, a, b):
        A.cmpw(a, b)
        A.crmove(0, 1)
        A.mfcr(dest)
        A.srwi(dest, dest, 31)
        
    def int_lt(self, A, dest, a, b):
        A.cmpw(a, b)
        A.mfcr(dest)
        A.srwi(dest, dest, 31)

    def int_ge(self, A, dest, a, b):
        A.cmpw(a, b)
        A.cror(0, 1, 2)
        A.mfcr(dest)
        A.srwi(dest, dest, 31)

    def int_le(self, A, dest, a, b):
        A.cmpw(a, b)
        A.cror(0, 0, 2)
        A.mfcr(dest)
        A.srwi(dest, dest, 31)

    def int_eq(self, A, dest, a, b):
        A.cmpw(a, b)
        A.crmove(0, 2)
        A.mfcr(dest)
        A.srwi(dest, dest, 31)

    def int_ne(self, A, dest, a, b):
        A.cmpw(a, b)
        A.cror(0, 0, 1)
        A.mfcr(dest)
        A.srwi(dest, dest, 31)
        

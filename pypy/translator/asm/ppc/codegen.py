
def make_native_code(graph, infreginsns):
    from pypy.translator.asm.ppcgen.func_builder import make_func
    maxregs = 0
    for insn in infreginsns:
        if isinstance(insn, str):
            continue
        for r in insn.registers_used():
            maxregs = max(r, maxregs)
    
    from pypy.translator.asm import regalloc

    insns = regalloc.regalloc(infreginsns, 30)

    codegen = PPCCodeGen()

    return make_func(codegen.assemble(insns), 'i',
                     'i'*len(graph.startblock.inputargs),
                     maxregs)

    
class PPCCodeGen(object):

    def assemble(self, insns):
        from pypy.translator.asm.ppcgen import ppc_assembler
        A = ppc_assembler.PPCAssembler()

        for i in insns:
            if isinstance(i, str):
                A.label(i)
                continue

            getattr(self, i.name)(A, *i.arguments)

        return A

    def LIA(self, A, dest, argindex):
        assert dest + 2 == argindex.value + 3

    def LOAD(self, A, dest, value):
        value = value.value
        assert isinstance(value, int)
        assert -30000 < value < 30000
        A.li(dest + 2, value)

    def int_add(self, A, dest, a, b):
        A.add(dest + 2, a + 2, b + 2)

    def int_sub(self, A, dest, a, b):
        A.sub(dest + 2, a + 2, b + 2)

    def int_mul(self, A, dest, a, b):
        A.mullw(dest + 2, a + 2, b + 2)

    def int_gt(self, A, a, b):
        A.cmpw(a + 2, b + 2)
        A.crmove(0, 1)

    def int_lt(self, A, a, b):
        A.cmpw(a + 2, b + 2)

    def JT(self, A, branch):
        # should be "A.bt(BI=0, BD=branch)" but this crashes.
        A.blt(branch)

    def J(self, A, branch):
        A.b(branch)

    def RETPYTHON(self, A, reg):
        A.mr(3, reg + 2)
        A.blr()

    def MOV(self, A, dest, src):
        A.mr(dest + 2, src + 2)

    def EXCH(self, A, a, b):
        A.xor(a+2, a+2, b+2)
        A.xor(b+2, b+2, a+2)
        A.xor(a+2, a+2, b+2)

    def STORESTACK(self, A, s, v):
        A.stw(v+2, 1, 24+4*s.value)

    def LOADSTACK(self, A, v, s):
        A.lwz(v+2, 1, 24+4*s.value)
    

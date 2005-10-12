
class Instruction(object):

    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments

    def registers_used(self):
        return [a for a in self.arguments if isinstance(a, int)]

    def renumber(self, regmap):
        def _(a):
            if isinstance(a, int) and a in regmap:
                return regmap[a]
            else:
                return a
        return Instruction(self.name, map(_, self.arguments))

    def __repr__(self):
        if self.name == 'LIA':
            r, a = self.arguments
            args = 'r%s, %s'%tuple(self.arguments)
        elif self.name in ('JT', 'JF', 'J'):
            args = self.arguments[0]
        elif self.name == 'LOAD':
            args = 'r%s, #%s'%tuple(self.arguments)
        else:
            def c(x):
                if isinstance(x, int):
                    return 'r%s'%x
                else:
                    return str(x)
            args = ', '.join(map(c, self.arguments))
        return '%-30s'%('    %-10s %s'%(self.name, args),)

class Program(object):
    # approximately a list of Instructions, but with sprinkles
    # not used yet.

    def __init__(self, insns):
        self.insns = insns

    def iterinsns(self):
        for insn in self.insns:
            if isinstance(ins, str):
                continue
            yield insn

class Assembler(object):
    def __init__(self):
        self.instructions = []

    def emit(self, name, *args):
        self.instructions.append(Instruction(name, args))

    def label(self, lab):
        self.instructions.append(lab)

    def dump(self):
        for i in self.instructions:
            if isinstance(i, str):
                i += ':'
            print i

    def allocate_registers(self, nregisters):
        from pypy.translator.asm import regalloc
        r = FiniteRegisterAssembler(nregisters)
        r.instructions = regalloc.regalloc(self.instructions, nregisters)
        r.dump()
        return r

class FiniteRegisterAssembler(Assembler):
    def __init__(self, nregisters):
        Assembler.__init__(self)
        self.nregisters = nregisters

    def assemble(self):
        from pypy.translator.asm.ppcgen import ppc_assembler
        A = ppc_assembler.PPCAssembler()

        for i in self.instructions:
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

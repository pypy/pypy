
class Instruction(object):

    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments

    def registers_used(self):
        if self.name == 'LIA' or self.name == 'LOAD':
            return [self.arguments[0]]
        elif self.name in ('JT', 'JF', 'J'):
            return []
        else:
            return list(self.arguments)

    def __repr__(self):
        if self.name == 'LIA':
            r, a = self.arguments
            args = 'r%s, %s'%tuple(self.arguments)
        elif self.name in ('JT', 'JF', 'J'):
            args = self.arguments[0]
        elif self.name == 'LOAD':
            args = 'r%s, %s'%tuple(self.arguments)
        else:
            args = ', '.join(['r%s'%a for a in self.arguments])
        return '    %-10s %s'%(self.name, args)

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
        r = FiniteRegisterAssembler(nregisters)
        for i in self.instructions:
            if not isinstance(i, str): # labels
                assert max(i.registers_used() + [0]) < nregisters
            r.instructions.append(i)
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
        assert dest + 2 == argindex + 3

    def LOAD(self, A, dest, value):
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

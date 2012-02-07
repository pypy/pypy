import os
from pypy.jit.backend.ppc.ppcgen import form

# don't be fooled by the fact that there's some separation between a
# generic assembler class and a PPC assembler class... there's
# certainly a RISC dependency in here, and quite possibly a PPC
# dependency or two too.  I personally don't care :)

class AssemblerException(Exception):
    pass

class Assembler(object):
    def __init__(self):
        self.insts = []
        self.labels = {}
        self.rlabels = {}

    def reset(self):
        self.insts = []
        self.labels = {}
        self.rlabels = {}

    def label(self, name):
        if name in self.labels:
            raise AssemblerException, "duplicate label '%s'"%(name,)
        self.labels[name] = len(self.insts)*4
        self.rlabels.setdefault(len(self.insts)*4, []).append(name)

    def labelname(self, base="L"):
        i = 0
        while 1:
            ln = base + str(i)
            if ln not in self.labels:
                return ln
            i += 1

    def get_number_of_ops(self):
        return len(self.insts)

    def get_rel_pos(self):
        return 4 * len(self.insts)

    def patch_op(self, index):
        last = self.insts.pop()
        self.insts[index] = last

    def assemble0(self, dump=os.environ.has_key('PPY_DEBUG')):
        for i, inst in enumerate(self.insts):
            for f in inst.lfields:
                l = self.labels[inst.fields[f]] - 4*i
                inst.fields[f] = l
        buf = []
        for inst in self.insts:
            buf.append(inst)#.assemble())
        if dump:
            for i in range(len(buf)):
                inst = self.disassemble(buf[i], self.rlabels, i*4)
                for lab in self.rlabels.get(4*i, []):
                    print "%s:"%(lab,)
                print "\t%4d    %s"%(4*i, inst)
        return buf

    def assemble(self, dump=os.environ.has_key('PPY_DEBUG')):
        #insns = self.assemble0(dump)
        from pypy.jit.backend.ppc.ppcgen import asmfunc
        c = asmfunc.AsmCode(len(self.insts)*4)
        for i in self.insts:
            c.emit(i)#.assemble())
        #return c.get_function()

    def get_idescs(cls):
        r = []
        for name in dir(cls):
            a = getattr(cls, name)
            if isinstance(a, form.IDesc):
                r.append((name, a))
        return r
    get_idescs = classmethod(get_idescs)

    def disassemble(cls, inst, labels={}, pc=0):
        matches = []
        idescs = cls.get_idescs()
        for name, idesc in idescs:
            m = idesc.match(inst)
            if m > 0:
                matches.append((m, idesc, name))
        if matches:
            score, idesc, name = max(matches)
            return idesc.disassemble(name, inst, labels, pc)
    disassemble = classmethod(disassemble)

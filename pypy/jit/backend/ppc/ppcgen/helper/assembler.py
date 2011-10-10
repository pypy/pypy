import pypy.jit.backend.ppc.ppcgen.condition as c
from pypy.rlib.rarithmetic import r_uint, r_longlong, intmask

def gen_emit_cmp_op(condition):
    def f(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        # do the comparison
        if l1.is_imm():
            self.mc.cmpwi(0, l0.value, l1.value)
        else:
            self.mc.cmpw(0, l0.value, l1.value)

        # After the comparison, place the result
        # in the first bit of the CR
        if condition == c.LT:
            self.mc.cror(0, 0, 0)
        elif condition == c.LE:
            self.mc.cror(0, 0, 2)
        elif condition == c.EQ:
            self.mc.cror(0, 2, 2)
        elif condition == c.GE:
            self.mc.cror(0, 1, 2)
        elif condition == c.GT:
            self.mc.cror(0, 1, 1)

        resval = res.value 
        # move the content of the CR to resval
        self.mc.mfcr(resval)       
        # zero out everything except of the result
        self.mc.rlwinm(resval, resval, 1, 31, 31)
    return f

def encode32(mem, i, n):
    mem[i] = chr(n & 0xFF)
    mem[i+1] = chr((n >> 8) & 0xFF)
    mem[i+2] = chr((n >> 16) & 0xFF)
    mem[i+3] = chr((n >> 24) & 0xFF)

def decode32(mem, index):
    return intmask(ord(mem[index])
            | ord(mem[index+1]) << 8
            | ord(mem[index+2]) << 16
            | ord(mem[index+3]) << 24)

class saved_registers(object):
    def __init__(self, assembler, regs_to_save, regalloc=None):
        self.assembler = assembler
        self.regalloc = regalloc
        if self.regalloc:
            self._filter_regs(regs_to_save, vfp_regs_to_save)
        else:
            self.regs = regs_to_save

    def __enter__(self):
        if len(self.regs) > 0:
            self.assembler.PUSH([r.value for r in self.regs])

    def _filter_regs(self, regs_to_save, vfp_regs_to_save):
        regs = []
        for box, reg in self.regalloc.rm.reg_bindings.iteritems():
            if reg is r.ip or (reg in regs_to_save and self.regalloc.stays_alive(box)):
                regs.append(reg)
        self.regs = regs

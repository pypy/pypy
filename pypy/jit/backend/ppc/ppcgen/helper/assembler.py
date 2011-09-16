import pypy.jit.backend.ppc.ppcgen.condition as c

def gen_emit_cmp_op(condition):
    def f(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if l1.is_imm():
            self.mc.cmpwi(0, l0.value, l1.value)
        else:
            self.mc.cmpw(0, l0.value, l1.value)

        if condition == c.LE:
            self.mc.cror(0, 0, 2)

        resval = res.value
        self.mc.mfcr(resval)
        self.mc.rlwinm(resval, resval, 1, 31, 31)
    return f

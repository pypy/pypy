import pypy.jit.backend.ppc.ppcgen.condition as c

def gen_emit_cmp_op(condition):
    def f(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if l1.is_imm():
            self.cmpwi(0, l0.value, l1.value)
        else:
            self.cmpw(0, l0.value, l1.value)

        if condition == c.LE:
            self.cror(0, 0, 2)

        resval = res.value
        self.mfcr(resval)
        self.rlwinm(resval, resval, 1, 31, 31)
    return f

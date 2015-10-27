
class IntOpAssembler(object):
    _mixin_ = True

    def emit_int_add(self, op, arglocs, regalloc):
        l0, l1 = arglocs
        assert not l0.is_imm()
        if l1.is_imm():
            self.mc.AGHI(l0, l1)
        else:
            self.mc.AGR(l0, l1)

class FloatOpAssembler(object):
    _mixin_ = True

    def emit_float_add(self, op, arglocs, regalloc):
        l0, l1 = arglocs
        if l1.is_in_pool():
            self.mc.ADB(l0, l1)
        else:
            self.mc.ADBR(l0, l1)

    def emit_float_sub(self, op, arglocs, regalloc):
        l0, l1 = arglocs
        if l1.is_in_pool():
            self.mc.SDB(l0, l1)
        else:
            self.mc.SDBR(l0, l1)

    def emit_float_mul(self, op, arglocs, regalloc):
        l0, l1 = arglocs
        if l1.is_in_pool():
            self.mc.MDB(l0, l1)
        else:
            self.mc.MDBR(l0, l1)

    def emit_float_div(self, op, arglocs, regalloc):
        l0, l1 = arglocs
        if l1.is_in_pool():
            self.mc.DDB(l0, l1)
        else:
            self.mc.DDBR(l0, l1)

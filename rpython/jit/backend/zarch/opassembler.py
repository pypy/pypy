
class IntOpAssembler(object):
    _mixin_ = True

    def emit_int_add(self, op, arglocs, regalloc):
        l0, l1 = arglocs
        assert not l0.is_imm()
        if l1.is_imm():
            self.mc.AGHI(l0, l1)
        else:
            self.mc.AGR(l0, l1)


import rpython.jit.backend.zarch.conditions as c
import rpython.jit.backend.zarch.registers as r
from rpython.rlib.rarithmetic import intmask
from rpython.jit.backend.zarch.arch import WORD
from rpython.jit.metainterp.history import FLOAT
from rpython.jit.metainterp.resoperation import rop
from rpython.rtyper.lltypesystem import rffi, lltype

def flush_cc(asm, condition, result_loc):
    # After emitting an instruction that leaves a boolean result in
    # a condition code (cc), call this.  In the common case, result_loc
    # will be set to SPP by the regalloc, which in this case means
    # "propagate it between this operation and the next guard by keeping
    # it in the cc".  In the uncommon case, result_loc is another
    # register, and we emit a load from the cc into this register.
    assert asm.guard_success_cc == c.cond_none
    if result_loc is r.SPP:
        asm.guard_success_cc = condition
    else:
        # Possibly invert the bit in the CR
        bit, invert = c.encoding[condition]
        assert 0 <= bit <= 3
        if invert == 12:
            pass
        elif invert == 4:
            asm.mc.crnor(bit, bit, bit)
        else:
            assert 0

        resval = result_loc.value
        # move the content of the CR to resval
        asm.mc.mfcr(resval)
        # zero out everything except of the result
        asm.mc.rlwinm(resval, resval, 1 + bit, 31, 31)


def do_emit_cmp_op(self, arglocs, condition, signed, fp):
    l0 = arglocs[0]
    l1 = arglocs[1]
    assert not l0.is_imm()
    # do the comparison
    self.mc.cmp_op(l0, l1, pool=l1.is_in_pool(), imm=l1.is_imm(), signed=signed, fp=fp)

    # CR bits:
    #     0: LT
    #     1: GT
    #     2: EQ
    #     3: UNordered

    if fp:
        # Support for NaNs: with LE or GE, if one of the operands is a
        # NaN, we get CR=1,0,0,0 (unordered bit only).  We're about to
        # check "not GT" or "not LT", but in case of NaN we want to
        # get the answer False.
        #if condition == c.LE:
        #    self.mc.crnor(1, 1, 3)
        #    condition = c.GT
        #elif condition == c.GE:
        #    self.mc.crnor(0, 0, 3)
        #    condition = c.LT
        pass

    flush_cc(self, condition, r.SPP)


def gen_emit_cmp_op(condition, signed=True, fp=False):
    def f(self, op, arglocs, regalloc):
        do_emit_cmp_op(self, arglocs, condition, signed, fp)
    return f

import rpython.jit.backend.ppc.condition as c
from rpython.rlib.rarithmetic import intmask
from rpython.jit.backend.ppc.arch import MAX_REG_PARAMS, IS_PPC_32, WORD
from rpython.jit.metainterp.history import FLOAT
from rpython.jit.metainterp.resoperation import rop
import rpython.jit.backend.ppc.register as r
from rpython.rtyper.lltypesystem import rffi, lltype

def test_condition_for(condition, guard_op):
    opnum = guard_op.getopnum()
    if opnum == rop.GUARD_FALSE:
        return condition
    elif opnum == rop.GUARD_TRUE:
        return c.negate(condition)
    assert 0, opnum

def do_emit_cmp_op(self, guard_op, arglocs, condition, signed, fp):
    l0 = arglocs[0]
    l1 = arglocs[1]
    assert not l0.is_imm()
    # do the comparison
    self.mc.cmp_op(0, l0.value, l1.value,
                   imm=l1.is_imm(), signed=signed, fp=fp)

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
        if condition == c.LE:
            self.mc.crnor(1, 1, 3)
            condition = c.GT
        elif condition == c.GE:
            self.mc.crnor(0, 0, 3)
            condition = c.LT

    if guard_op is None:
        # After the comparison, place the result in a single bit of the CR
        bit, invert = c.encoding[condition]
        assert 0 <= bit <= 3
        if invert == 12:
            pass
        elif invert == 4:
            self.mc.crnor(bit, bit, bit)
        else:
            assert 0

        assert len(arglocs) == 3
        res = arglocs[2]
        resval = res.value
        # move the content of the CR to resval
        self.mc.mfcr(resval)
        # zero out everything except of the result
        self.mc.rlwinm(resval, resval, 1 + bit, 31, 31)
    else:
        failargs = arglocs[2:]
        fcond = test_condition_for(condition, guard_op)
        self._emit_guard(guard_op, failargs, fcond)

def gen_emit_cmp_op(condition, signed=True, fp=False):
    def f(self, op, guard_op, arglocs, regalloc):
        do_emit_cmp_op(self, guard_op, arglocs, condition, signed, fp)
    return f

def count_reg_args(args):
    reg_args = 0
    words = 0
    count = 0
    for x in range(min(len(args), MAX_REG_PARAMS)):
        if args[x].type == FLOAT:
            count += 1
            words += 1
        else:
            count += 1
            words += 1
        reg_args += 1
        if words > MAX_REG_PARAMS:
            reg_args = x
            break
    return reg_args

class Saved_Volatiles(object):
    """ used in _gen_leave_jitted_hook_code to save volatile registers
        in ENCODING AREA around calls
    """

    def __init__(self, codebuilder, save_RES=True, save_FLOAT=True):
        self.mc = codebuilder
        self.save_RES = save_RES
        self.save_FLOAT = save_FLOAT
        self.FLOAT_OFFSET = len(r.VOLATILES)

    def __enter__(self):
        """ before a call, volatile registers are saved in ENCODING AREA
        """
        for i, reg in enumerate(r.VOLATILES):
            if not self.save_RES and reg is r.RES:
                continue
            self.mc.store(reg.value, r.SPP.value, i * WORD)
        if self.save_FLOAT:
            for i, reg in enumerate(r.VOLATILES_FLOAT):
                if not self.save_RES and reg is r.f1:
                    continue
                self.mc.stfd(reg.value, r.SPP.value,
                             (i + self.FLOAT_OFFSET) * WORD)

    def __exit__(self, *args):
        """ after call, volatile registers have to be restored
        """
        for i, reg in enumerate(r.VOLATILES):
            if not self.save_RES and reg is r.RES:
                continue
            self.mc.load(reg.value, r.SPP.value, i * WORD)
        if self.save_FLOAT:
            for i, reg in enumerate(r.VOLATILES_FLOAT):
                if not self.save_RES and reg is r.f1:
                    continue
                self.mc.lfd(reg.value, r.SPP.value,
                             (i + self.FLOAT_OFFSET) * WORD)

import pypy.jit.backend.ppc.condition as c
from pypy.rlib.rarithmetic import intmask
from pypy.jit.backend.ppc.arch import (MAX_REG_PARAMS, IS_PPC_32, WORD,
                                              BACKCHAIN_SIZE)
from pypy.jit.metainterp.history import FLOAT
import pypy.jit.backend.ppc.register as r
from pypy.rpython.lltypesystem import rffi, lltype

def gen_emit_cmp_op(condition, signed=True):
    def f(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        # do the comparison
        self.mc.cmp_op(0, l0.value, l1.value,
                       imm=l1.is_imm(), signed=signed)
        # After the comparison, place the result
        # in the first bit of the CR
        if condition == c.LT or condition == c.U_LT:
            self.mc.cror(0, 0, 0)
        elif condition == c.LE or condition == c.U_LE:
            self.mc.cror(0, 0, 2)
        elif condition == c.EQ:
            self.mc.cror(0, 2, 2)
        elif condition == c.GE or condition == c.U_GE:
            self.mc.cror(0, 1, 2)
        elif condition == c.GT or condition == c.U_GT:
            self.mc.cror(0, 1, 1)
        elif condition == c.NE:
            self.mc.cror(0, 0, 1)
        else:
            assert 0, "condition not known"

        resval = res.value 
        # move the content of the CR to resval
        self.mc.mfcr(resval)       
        # zero out everything except of the result
        self.mc.rlwinm(resval, resval, 1, 31, 31)
    return f

def gen_emit_unary_cmp_op(condition):
    def f(self, op, arglocs, regalloc):
        reg, res = arglocs

        self.mc.cmp_op(0, reg.value, 0, imm=True)
        if condition == c.IS_ZERO:
            self.mc.cror(0, 2, 2)
        elif condition == c.IS_TRUE:
            self.mc.cror(0, 0, 1)
        else:
            assert 0, "condition not known"

        self.mc.mfcr(res.value)
        self.mc.rlwinm(res.value, res.value, 1, 31, 31)
    return f

def count_reg_args(args):
    reg_args = 0
    words = 0
    count = 0
    for x in range(min(len(args), MAX_REG_PARAMS)):
        if args[x].type == FLOAT:
            assert 0, "not implemented yet"
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

    def __init__(self, codebuilder):
        self.mc = codebuilder

    def __enter__(self):
        """ before a call, volatile registers are saved in ENCODING AREA
        """
        for i, reg in enumerate(r.VOLATILES):
            if IS_PPC_32:
                self.mc.stw(reg.value, r.SPP.value, i * WORD)
            else:
                self.mc.std(reg.value, r.SPP.value, i * WORD)

    def __exit__(self, *args):
        """ after call, volatile registers have to be restored
        """
        for i, reg in enumerate(r.VOLATILES):
            if IS_PPC_32:
                self.mc.lwz(reg.value, r.SPP.value, i * WORD)
            else:
                self.mc.ld(reg.value, r.SPP.value, i * WORD)

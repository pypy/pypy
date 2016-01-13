import rpython.jit.backend.zarch.conditions as c
import rpython.jit.backend.zarch.registers as r
from rpython.rlib.rarithmetic import intmask
from rpython.jit.backend.zarch.arch import WORD
from rpython.jit.metainterp.history import FLOAT
from rpython.jit.metainterp.resoperation import rop
from rpython.rtyper.lltypesystem import rffi, lltype

def do_emit_cmp_op(self, arglocs, condition, signed, fp):
    l0 = arglocs[0]
    l1 = arglocs[1]
    assert not l0.is_imm()
    # do the comparison
    self.mc.cmp_op(l0, l1, pool=l1.is_in_pool(), imm=l1.is_imm(), signed=signed, fp=fp)

    if fp:
        # Support for NaNs: S390X sets condition register to 0x3 (unordered)
        # as soon as any of the operands is NaN
        condition = c.prepare_float_condition(condition)
    self.flush_cc(condition, arglocs[2])


def gen_emit_cmp_op(condition, signed=True, fp=False):
    def f(self, op, arglocs, regalloc):
        do_emit_cmp_op(self, arglocs, condition, signed, fp)
    return f

def gen_emit_shift(func):
    def f(self, op, arglocs, regalloc):
        lr, l0, l1 = arglocs
        assert lr is not l0
        getattr(self.mc, func)(lr, l0, l1)
    f.name = 'emit_shift_' + func
    return f

def gen_emit_rr_or_rpool(rr_func, rp_func):
    """ the parameters can either be both in registers or
        the first is in the register, second in literal pool.
    """
    def f(self, op, arglocs, regalloc):
        l0, l1 = arglocs
        if l1.is_imm() and not l1.is_in_pool():
            assert 0, "logical imm must reside in pool!"
        if l1.is_in_pool():
            getattr(self.mc, rp_func)(l0, l1)
        else:
            getattr(self.mc, rr_func)(l0, l1)
    return f

def gen_emit_imm_pool_rr(imm_func, pool_func, rr_func):
    def emit(self, op, arglocs, regalloc):
        l0, l1 = arglocs
        if l1.is_in_pool():
            getattr(self.mc, pool_func)(l0, l1)
        elif l1.is_imm():
            getattr(self.mc, imm_func)(l0, l1)
        else:
            getattr(self.mc, rr_func)(l0, l1)
    return emit

def gen_emit_pool_or_rr_evenodd(pool_func, rr_func):
    def emit(self, op, arglocs, regalloc):
        lr, lq, l1 = arglocs # lr == remainer, lq == quotient
        # when entering the function lr contains the dividend
        # after this operation either lr or lq is used further
        assert l1.is_in_pool() or not l1.is_imm() , "imm divider not supported"
        # remainer is always a even register r0, r2, ... , r14
        assert lr.is_even()
        assert lq.is_odd()
        self.mc.XGR(lr, lr)
        if l1.is_in_pool():
            getattr(self.mc,pool_func)(lr, l1)
        else:
            getattr(self.mc,rr_func)(lr, l1)
    return emit

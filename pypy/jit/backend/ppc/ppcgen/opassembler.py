from pypy.jit.backend.ppc.ppcgen.helper.assembler import (gen_emit_cmp_op, 
                                                          gen_emit_unary_cmp_op)
import pypy.jit.backend.ppc.ppcgen.condition as c
import pypy.jit.backend.ppc.ppcgen.register as r
from pypy.jit.backend.ppc.ppcgen.arch import GPR_SAVE_AREA, IS_PPC_32, WORD

from pypy.jit.metainterp.history import LoopToken, AbstractFailDescr

class GuardToken(object):
    def __init__(self, descr, failargs, faillocs, offset, fcond=c.NE,
                                        save_exc=False, is_invalidate=False):
        self.descr = descr
        self.offset = offset
        self.is_invalidate = is_invalidate
        self.failargs = failargs
        self.faillocs = faillocs
        self.save_exc = save_exc
        self.fcond=fcond

class OpAssembler(object):
        
    # ********************************************************
    # *               I N T    O P E R A T I O N S           *
    # ********************************************************

    def emit_int_add(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if l0.is_imm():
            self.mc.addi(res.value, l1.value, l0.value)
        elif l1.is_imm():
            self.mc.addi(res.value, l0.value, l1.value)
        else:
            self.mc.add(res.value, l0.value, l1.value)

    def emit_int_add_ovf(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        self.mc.addo(res.value, l0.value, l1.value)

    def emit_int_sub(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if l0.is_imm():
            self.mc.load_imm(r.r0, l0.value)
            self.mc.sub(res.value, r.r0.value, l1.value)
        elif l1.is_imm():
            self.mc.subi(res.value, l0.value, l1.value)
        else:
            self.mc.sub(res.value, l0.value, l1.value)
 
    def emit_int_sub_ovf(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        self.mc.subfo(res.value, l1.value, l0.value)

    def emit_int_mul(self, op, arglocs, regalloc):
        reg1, reg2, res = arglocs
        self.mc.mullw(res.value, reg1.value, reg2.value)

    def emit_int_mul_ovf(self, op, arglocs, regalloc):
        reg1, reg2, res = arglocs
        self.mc.mullwo(res.value, reg1.value, reg2.value)

    def emit_int_mul_ovf(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        self.mc.mullwo(res.value, l0.value, l1.value)

    def emit_int_floordiv(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if IS_PPC_32:
            div = self.mc.divw
        else:
            div = self.mc.divd

        if l0.is_imm():
            self.mc.load_imm(r.r0, l0.value)
            div(res.value, r.r0.value, l1.value)
        elif l1.is_imm():
            self.mc.load_imm(r.r0, l1.value)
            div(res.value, l0.value, r.r0.value)
        else:
            div(res.value, l0.value, l1.value)

    def emit_int_mod(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if IS_PPC_32:
            self.mc.divw(r.r0.value, l0.value, l1.value)
            self.mc.mullw(r.r0.value, r.r0.value, l1.value)
        else:
            self.mc.divd(r.r0.value, l0.value, l1.value)
            self.mc.mulld(r.r0.value, r.r0.value, l1.value)
        self.mc.subf(r.r0.value, r.r0.value, l0.value)
        self.mc.mr(res.value, r.r0.value)

    def emit_int_and(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        self.mc.and_(res.value, l0.value, l1.value)

    def emit_int_or(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        self.mc.or_(res.value, l0.value, l1.value)

    def emit_int_xor(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        self.mc.xor(res.value, l0.value, l1.value)
        
    def emit_int_lshift(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if IS_PPC_32:
            self.mc.slw(res.value, l0.value, l1.value)
        else:
            self.mc.sld(res.value, l0.value, l1.value)

    def emit_int_rshift(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if IS_PPC_32:
            self.mc.sraw(res.value, l0.value, l1.value)
        else:
            self.mc.srad(res.value, l0.value, l1.value)

    def emit_uint_rshift(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if IS_PPC_32:
            self.mc.srw(res.value, l0.value, l1.value)
        else:
            self.mc.srd(res.value, l0.value, l1.value)
    
    def emit_uint_floordiv(self, op, arglocs, regalloc):
        l0, l1, res = arglocs
        if IS_PPC_32:
            self.mc.divwu(res.value, l0.value, l1.value)
        else:
            self.mc.divdu(res.value, l0.value, l1.value)

    emit_int_le = gen_emit_cmp_op(c.LE)
    emit_int_lt = gen_emit_cmp_op(c.LT)
    emit_int_gt = gen_emit_cmp_op(c.GT)
    emit_int_ge = gen_emit_cmp_op(c.GE)
    emit_int_eq = gen_emit_cmp_op(c.EQ)
    emit_int_ne = gen_emit_cmp_op(c.NE)

    emit_uint_lt = gen_emit_cmp_op(c.U_LT, signed=False)
    emit_uint_le = gen_emit_cmp_op(c.U_LE, signed=False)
    emit_uint_gt = gen_emit_cmp_op(c.U_GT, signed=False)
    emit_uint_ge = gen_emit_cmp_op(c.U_GE, signed=False)

    emit_int_is_zero = gen_emit_unary_cmp_op(c.IS_ZERO)
    emit_int_is_true = gen_emit_unary_cmp_op(c.IS_TRUE)

    def emit_int_neg(self, op, arglocs, regalloc):
        l0, res = arglocs
        self.mc.neg(res.value, l0.value)

    def emit_int_invert(self, op, arglocs, regalloc):
        l0, res = arglocs
        self.mc.not_(res.value, l0.value)

    def _emit_guard(self, op, arglocs, fcond, save_exc=False,
            is_guard_not_invalidated=False):
        descr = op.getdescr()
        assert isinstance(descr, AbstractFailDescr)
        pos = self.mc.currpos()
        self.mc.nop()     # has to be patched later on
        self.pending_guards.append(GuardToken(descr,
                                   failargs=op.getfailargs(),
                                   faillocs=arglocs,
                                   offset=pos,
                                   fcond=fcond,
                                   is_invalidate=is_guard_not_invalidated,
                                   save_exc=save_exc))

    def emit_guard_true(self, op, arglocs, regalloc):
        l0 = arglocs[0]
        failargs = arglocs[1:]
        self.mc.cmpi(l0.value, 0)
        self._emit_guard(op, failargs, c.EQ)
        #                        #      ^^^^ If this condition is met,
        #                        #           then the guard fails.

    # TODO - Evaluate whether this can be done with 
    #        SO bit instead of OV bit => usage of CR
    #        instead of XER could be more efficient
    def _emit_ovf_guard(self, op, arglocs, cond):
        # move content of XER to GPR
        self.mc.mfspr(r.r0.value, 1)
        # shift and mask to get comparison result
        self.mc.rlwinm(r.r0.value, r.r0.value, 1, 0, 0)
        self.mc.cmpi(r.r0.value, 0)
        self._emit_guard(op, arglocs, cond)

    def emit_guard_no_overflow(self, op, arglocs, regalloc):
        self._emit_ovf_guard(op, arglocs, c.NE)

    def emit_guard_overflow(self, op, arglocs, regalloc):
        self._emit_ovf_guard(op, arglocs, c.EQ)

    def emit_finish(self, op, arglocs, regalloc):
        self.gen_exit_stub(op.getdescr(), op.getarglist(), arglocs)

    def emit_jump(self, op, arglocs, regalloc):
        descr = op.getdescr()
        assert isinstance(descr, LoopToken)
        if descr._ppc_bootstrap_code == 0:
            curpos = self.mc.get_rel_pos()
            self.mc.b(descr._ppc_loop_code - curpos)
        else:
            assert 0, "case not implemented yet"

    def nop(self):
        self.mc.ori(0, 0, 0)

    def branch_abs(self, address):
        self.load_imm(r.r0.value, address)
        self.mc.mtctr(0)
        self.mc.bctr()

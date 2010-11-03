from pypy.jit.backend.arm import conditions as c
from pypy.jit.backend.arm import locations
from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm.arch import (WORD, FUNC_ALIGN, arm_int_div,
                                        arm_int_div_sign, arm_int_mod_sign, arm_int_mod)

from pypy.jit.backend.arm.helper.assembler import (gen_emit_op_by_helper_call,
                                                    gen_emit_op_unary_cmp,
                                                    gen_emit_op_ri, gen_emit_cmp_op)
from pypy.jit.backend.arm.codebuilder import ARMv7Builder, ARMv7InMemoryBuilder
from pypy.jit.backend.arm.regalloc import ARMRegisterManager
from pypy.jit.backend.llsupport.regalloc import compute_vars_longevity
from pypy.jit.metainterp.history import ConstInt, BoxInt, Box, BasicFailDescr
from pypy.jit.metainterp.resoperation import rop
from pypy.rlib import rgc
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype, rffi, llmemory

class IntOpAsslember(object):
    _mixin_ = True

    def emit_op_int_add(self, op, regalloc, fcond):
        # assuming only one argument is constant
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        imm_a0 = isinstance(a0, ConstInt) and (a0.getint() <= 0xFF or -1 * a0.getint() <= 0xFF)
        imm_a1 = isinstance(a1, ConstInt) and (a1.getint() <= 0xFF or -1 * a1.getint() <= 0xFF)
        if imm_a0:
            imm_a0, imm_a1 = imm_a1, imm_a0
            a0, a1 = a1, a0
        if imm_a1:
            l0 = regalloc.make_sure_var_in_reg(a0, imm_fine=False)
            l1 = regalloc.make_sure_var_in_reg(a1, imm_fine=True)
            res = regalloc.force_allocate_reg(op.result)
            if l1.getint() < 0:
                self.mc.SUB_ri(res.value, l0.value, -1 * l1.getint())
            else:
                self.mc.ADD_ri(res.value, l0.value, l1.getint())
        else:
            l0 = regalloc.make_sure_var_in_reg(a0, imm_fine=False)
            l1 = regalloc.make_sure_var_in_reg(a1, imm_fine=False)
            res = regalloc.force_allocate_reg(op.result)
            self.mc.ADD_rr(res.value, l0.value, l1.value)

        regalloc.possibly_free_vars_for_op(op)
        return fcond

    def emit_op_int_sub(self, op, regalloc, fcond):
        # assuming only one argument is constant
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        imm_a0 = isinstance(a0, ConstInt) and (a0.getint() <= 0xFF or -1 * a0.getint() <= 0xFF)
        imm_a1 = isinstance(a1, ConstInt) and (a1.getint() <= 0xFF or -1 * a1.getint() <= 0xFF)
        l0 = regalloc.make_sure_var_in_reg(a0, imm_fine=imm_a0)
        l1 = regalloc.make_sure_var_in_reg(a1, imm_fine=imm_a1)
        res = regalloc.force_allocate_reg(op.result)
        if imm_a0:
            value = l0.getint()
            if value < 0:
                # XXX needs a test
                self.mc.ADD_ri(res.value, l1.value, -1 * value)
                self.mc.MVN_rr(res.value, l1.value)
            else:
                # reverse substract ftw
                self.mc.RSB_ri(res.value, l1.value, value)
        elif imm_a1:
            value = l1.getint()
            if value < 0:
                self.mc.ADD_ri(res.value, l0.value, -1 * value)
            else:
                self.mc.SUB_ri(res.value, l0.value, value)
        else:
            self.mc.SUB_rr(res.value, l0.value, l1.value)

        regalloc.possibly_free_vars_for_op(op)
        return fcond

    def emit_op_int_mul(self, op, regalloc, fcond):
        reg1 = regalloc.make_sure_var_in_reg(op.getarg(0), imm_fine=False)
        reg2 = regalloc.make_sure_var_in_reg(op.getarg(1), imm_fine=False)
        res = regalloc.force_allocate_reg(op.result)
        self.mc.MUL(res.value, reg1.value, reg2.value)
        regalloc.possibly_free_vars_for_op(op)
        return fcond

    emit_op_int_floordiv = gen_emit_op_by_helper_call('DIV')
    emit_op_int_mod = gen_emit_op_by_helper_call('MOD')
    emit_op_uint_floordiv = gen_emit_op_by_helper_call('UDIV')

    emit_op_int_and = gen_emit_op_ri('AND')
    emit_op_int_or = gen_emit_op_ri('ORR')
    emit_op_int_xor = gen_emit_op_ri('EOR')
    emit_op_int_lshift = gen_emit_op_ri('LSL', imm_size=0x1F, allow_zero=False, commutative=False)
    emit_op_int_rshift = gen_emit_op_ri('ASR', imm_size=0x1F, commutative=False)
    emit_op_uint_rshift = gen_emit_op_ri('LSR', imm_size=0x1F, commutative=False)

    emit_op_int_lt = gen_emit_cmp_op(c.LT)
    emit_op_int_le = gen_emit_cmp_op(c.LE)
    emit_op_int_eq = gen_emit_cmp_op(c.EQ)
    emit_op_int_ne = gen_emit_cmp_op(c.NE)
    emit_op_int_gt = gen_emit_cmp_op(c.GT)
    emit_op_int_ge = gen_emit_cmp_op(c.GE)

    emit_op_uint_le = gen_emit_cmp_op(c.LS)
    emit_op_uint_gt = gen_emit_cmp_op(c.HI)

    emit_op_uint_lt = gen_emit_cmp_op(c.HI, inverse=True)
    emit_op_uint_ge = gen_emit_cmp_op(c.LS, inverse=True)



class UnaryIntOpAssembler(object):
    emit_op_int_is_true = gen_emit_op_unary_cmp(c.NE, c.EQ)
    emit_op_int_is_zero = gen_emit_op_unary_cmp(c.EQ, c.NE)

    def emit_op_int_invert(self, op, regalloc, fcond):
        reg = regalloc.make_sure_var_in_reg(op.getarg(0), imm_fine=False)
        res = regalloc.force_allocate_reg(op.result)

        self.mc.MVN_rr(res.value, reg.value)
        regalloc.possibly_free_vars_for_op(op)
        return fcond

    #XXX check for a better way of doing this
    def emit_op_int_neg(self, op, regalloc, fcond):
            arg = op.getarg(0)
            l0 = regalloc.make_sure_var_in_reg(op.getarg(0), imm_fine=False)
            l1 = regalloc.make_sure_var_in_reg(ConstInt(-1), imm_fine=False)
            res = regalloc.force_allocate_reg(op.result)
            self.mc.MUL(res.value, l0.value, l1.value)
            regalloc.possibly_free_vars([l0, l1, res])
            return fcond

class GuardOpAssembler(object):
    _mixin_ = True

    def _emit_guard(self, op, regalloc, fcond):
        descr = op.getdescr()
        assert isinstance(descr, BasicFailDescr)
        descr._arm_guard_code = self.mc.curraddr()
        memaddr = self._gen_path_to_exit_path(op, op.getfailargs(), regalloc, fcond)
        descr._failure_recovery_code = memaddr
        descr._arm_guard_cond = fcond
        descr._arm_guard_size = self.mc.curraddr() - descr._arm_guard_code
        regalloc.possibly_free_vars_for_op(op)

    def emit_op_guard_true(self, op, regalloc, fcond):
        assert fcond == c.LE
        cond = c.get_opposite_of(fcond)
        assert cond == c.GT
        self._emit_guard(op, regalloc, cond)
        return c.AL

    def emit_op_guard_false(self, op, regalloc, fcond):
        assert fcond == c.EQ
        self._emit_guard(op, regalloc, fcond)
        return c.AL

class OpAssembler(object):
    _mixin_ = True

    def emit_op_jump(self, op, regalloc, fcond):
        registers = op.getdescr()._arm_arglocs
        for i in range(op.numargs()):
            # avoid moving stuff twice
            loc = registers[i]
            prev_loc = regalloc.loc(op.getarg(i))
            self.mov_loc_loc(prev_loc, loc)

        loop_code = op.getdescr()._arm_loop_code
        self.mc.B(loop_code, fcond)
        return fcond

    def emit_op_finish(self, op, regalloc, fcond):
        self._gen_path_to_exit_path(op, op.getarglist(), regalloc, c.AL)
        return fcond

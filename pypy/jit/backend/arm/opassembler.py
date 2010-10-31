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
        res = regalloc.try_allocate_reg(op.result)
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        imm_a0 = isinstance(a0, ConstInt) and (a0.getint() <= 0xFF or -1 * a0.getint() <= 0xFF)
        imm_a1 = isinstance(a1, ConstInt) and (a1.getint() <= 0xFF or -1 * a1.getint() <= 0xFF)
        if imm_a0 or imm_a1:
            if imm_a1:
                reg = regalloc.try_allocate_reg(a0)
                arg1 = a1
            elif imm_a0:
                reg = regalloc.try_allocate_reg(a1)
                arg1 = a0
            value = arg1.getint()
            if value < 0:
                self.mc.SUB_ri(res.value, reg.value, -1 * value)
            else:
                self.mc.ADD_ri(res.value, reg.value, value)
        else:
            r1 = regalloc.try_allocate_reg(a0)
            r2 = regalloc.try_allocate_reg(a1)
            self.mc.ADD_rr(res.value, r1.value, r2.value)

        regalloc.possibly_free_vars_for_op(op)
        return fcond

    def emit_op_int_sub(self, op, regalloc, fcond):
        # assuming only one argument is constant
        res = regalloc.try_allocate_reg(op.result)
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        imm_a0 = isinstance(a0, ConstInt) and (a0.getint() <= 0xFF or -1 * a0.getint() <= 0xFF)
        imm_a1 = isinstance(a1, ConstInt) and (a1.getint() <= 0xFF or -1 * a1.getint() <= 0xFF)
        if imm_a0 or imm_a1:
            if imm_a1:
                reg = self._put_in_reg(a0, regalloc)
                value = a1.getint()
                if value < 0:
                    self.mc.ADD_ri(res.value, reg.value, -1 * value)
                else:
                    self.mc.SUB_ri(res.value, reg.value, value)
            elif imm_a0:
                reg = self._put_in_reg(a1, regalloc)
                value = a0.getint()
                if value < 0:
                    self.mc.ADD_ri(res.value, reg.value, -1 * value)
                    self.mc.MVN_rr(res.value, res.value)
                else:
                    # reverse substract ftw
                    self.mc.RSB_ri(res.value, reg.value, value)
        else:
            r1 = regalloc.try_allocate_reg(a0)
            r2 = regalloc.try_allocate_reg(a1)
            self.mc.SUB_rr(res.value, r1.value, r2.value)

        regalloc.possibly_free_vars_for_op(op)
        return fcond

    def emit_op_int_mul(self, op, regalloc, fcond):
        res = regalloc.try_allocate_reg(op.result)
        reg1 = self._put_in_reg(op.getarg(0), regalloc)
        reg2 = self._put_in_reg(op.getarg(1), regalloc)
        self.mc.MUL(res.value, reg1.value, reg2.value)
        regalloc.possibly_free_var(reg1)
        regalloc.possibly_free_var(reg2)
        return fcond

    def _put_in_reg(self, box, regalloc):
        if isinstance(box, ConstInt):
            t = Box()
            reg = regalloc.try_allocate_reg(t)
            self.mc.gen_load_int(reg.value, box.getint())
        else:
            reg = regalloc.try_allocate_reg(box)
        return reg

    emit_op_int_floordiv = gen_emit_op_by_helper_call('DIV')
    emit_op_int_mod = gen_emit_op_by_helper_call('MOD')
    emit_op_uint_floordiv = gen_emit_op_by_helper_call('UDIV')

    emit_op_int_and = gen_emit_op_ri('AND')
    emit_op_int_or = gen_emit_op_ri('ORR')
    emit_op_int_xor = gen_emit_op_ri('EOR')
    emit_op_int_lshift = gen_emit_op_ri('LSL', imm_size=0x1F, commutative=False)
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
        arg = op.getarg(0)
        reg = self._put_in_reg(arg, regalloc)
        res = regalloc.try_allocate_reg(op.result)

        self.mc.MVN_rr(res.value, reg.value)
        regalloc.possibly_free_var(reg)
        regalloc.possibly_free_var(res)
        return fcond

    #XXX check for a better way of doing this
    def emit_op_int_neg(self, op, regalloc, fcond):
            arg = op.getarg(0)
            reg = self._put_in_reg(arg, regalloc)
            reg2 = self._put_in_reg(ConstInt(-1), regalloc)
            res = regalloc.try_allocate_reg(op.result)
            self.mc.MUL(res.value, reg.value, reg2.value)
            regalloc.possibly_free_var(reg)
            regalloc.possibly_free_var(reg2)
            regalloc.possibly_free_var(res)
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
        tmp = Box()
        tmpreg = regalloc.try_allocate_reg(tmp)
        registers = op.getdescr()._arm_arglocs
        for i in range(op.numargs()):
            reg = regalloc.try_allocate_reg(op.getarg(i))
            inpreg = registers[i]
            # XXX only if every value is in a register
            self.mc.MOV_rr(inpreg.value, reg.value)
        loop_code = op.getdescr()._arm_loop_code
        self.mc.gen_load_int(tmpreg.value, loop_code)
        self.mc.MOV_rr(r.pc.value, tmpreg.value)
        regalloc.possibly_free_var(tmpreg)
        return fcond

    def emit_op_finish(self, op, regalloc, fcond):
        self._gen_path_to_exit_path(op, op.getarglist(), regalloc, c.AL)
        return fcond

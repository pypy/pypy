from pypy.jit.backend.arm import conditions as c
from pypy.jit.backend.arm import locations
from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm.arch import WORD, FUNC_ALIGN
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

    # XXX support constants larger than imm

    def emit_op_int_add(self, op, regalloc, fcond):
        # assuming only one argument is constant
        res = regalloc.try_allocate_reg(op.result)
        if isinstance(op.getarg(0), ConstInt) or isinstance(op.getarg(1), ConstInt):
            if isinstance(op.getarg(1), ConstInt):
                reg = regalloc.try_allocate_reg(op.getarg(0))
                arg1 = op.getarg(1)
            elif isinstance(op.getarg(0), ConstInt):
                reg = regalloc.try_allocate_reg(op.getarg(1))
                arg1 = op.getarg(0)
            value = arg1.getint()
            if value < 0:
                self.mc.SUB_ri(res.value, reg.value, -1 * value)
            else:
                self.mc.ADD_ri(res.value, reg.value, value)
        else:
            r1 = regalloc.try_allocate_reg(op.getarg(0))
            r2 = regalloc.try_allocate_reg(op.getarg(1))
            self.mc.ADD_rr(res.value, r1.value, r2.value)

        regalloc.possibly_free_vars_for_op(op)
        return fcond

    def emit_op_int_sub(self, op, regalloc, fcond):
        # assuming only one argument is constant
        res = regalloc.try_allocate_reg(op.result)
        if isinstance(op.getarg(0), ConstInt) or isinstance(op.getarg(1), ConstInt):
            if isinstance(op.getarg(1), ConstInt):
                reg = regalloc.try_allocate_reg(op.getarg(0))
                value = op.getarg(1).getint()
                if value < 0:
                    self.mc.ADD_ri(res.value, reg.value, -1 * value)
                else:
                    self.mc.SUB_ri(res.value, reg.value, value)
            elif isinstance(op.getarg(0), ConstInt):
                reg = regalloc.try_allocate_reg(op.getarg(1))
                value = op.getarg(0).getint()
                if value < 0:
                    self.mc.ADD_ri(res.value, reg.value, -1 * value)
                    self.mc.MVN_rr(res.value, res.value)
                else:
                    # reverse substract ftw
                    self.mc.RSB_ri(res.value, reg.value, value)
        else:
            r1 = regalloc.try_allocate_reg(op.getarg(0))
            r2 = regalloc.try_allocate_reg(op.getarg(1))
            self.mc.SUB_rr(res.value, r1.value, r2.value)

        regalloc.possibly_free_vars_for_op(op)
        return fcond

    def emit_op_int_mul(self, op, regalloc, fcond):
        import pdb; pdb.set_trace()

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
        assert fcond == c.GT
        self._emit_guard(op, regalloc, fcond)
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
        self._gen_path_to_exit_path(op, op.getarglist(), regalloc, fcond)
        return fcond

    def emit_op_int_le(self, op, regalloc, fcond):
        reg = regalloc.try_allocate_reg(op.getarg(0))
        assert isinstance(op.getarg(1), ConstInt)
        self.mc.CMP(reg.value, op.getarg(1).getint())
        return c.GT

    def emit_op_int_eq(self, op, regalloc, fcond):
        reg = regalloc.try_allocate_reg(op.getarg(0))
        assert isinstance(op.getarg(1), ConstInt)
        self.mc.CMP(reg.value, op.getarg(1).getint())
        return c.EQ

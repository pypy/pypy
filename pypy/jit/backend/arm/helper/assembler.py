from pypy.jit.backend.arm import conditions as c
from pypy.jit.backend.arm import registers as r
from pypy.jit.metainterp.history import ConstInt, BoxInt, Box

def gen_emit_op_unary_cmp(true_cond, false_cond):
    def f(self, op, regalloc, fcond):
        arg = op.getarg(0)
        reg = self._put_in_reg(arg, regalloc)
        res = regalloc.try_allocate_reg(op.result)
        self.mc.CMP_ri(reg.value, 0)
        self.mc.MOV_ri(res.value, 1, true_cond)
        self.mc.MOV_ri(res.value, 0, false_cond)
        regalloc.possibly_free_var(reg)
        regalloc.possibly_free_var(res)
        return fcond
    return f

def gen_emit_op_ri(opname, imm_size=0xFF, commutative=True):
    def f(self, op, regalloc, fcond):
        ri_op = getattr(self.mc, '%s_ri' % opname)
        rr_op = getattr(self.mc, '%s_rr' % opname)

        arg0 = op.getarg(0)
        arg1 = op.getarg(1)
        res = regalloc.try_allocate_reg(op.result)
        if (commutative
                and self._check_imm_arg(arg0, imm_size)
                and not isinstance(arg1, ConstInt)):
            reg = regalloc.try_allocate_reg(arg1)
            ri_op(res.value, reg.value, imm=arg0.getint(), cond=fcond)
        elif self._check_imm_arg(arg1, imm_size) and not isinstance(arg0, ConstInt):
            reg = regalloc.try_allocate_reg(arg0)
            ri_op(res.value, reg.value, imm=arg1.getint(), cond=fcond)
        else:
            reg = self._put_in_reg(arg0, regalloc)
            reg2 = self._put_in_reg(arg1, regalloc)
            rr_op(res.value, reg.value, reg2.value)
            regalloc.possibly_free_var(reg2)

        regalloc.possibly_free_var(res)
        regalloc.possibly_free_var(reg)
        return fcond
    return f

def gen_emit_op_by_helper_call(opname):
    def f(self, op, regalloc, fcond):
        arg1 = regalloc.make_sure_var_in_reg(op.getarg(0), selected_reg=r.r0)
        arg2 = regalloc.make_sure_var_in_reg(op.getarg(1), selected_reg=r.r1)
        assert arg1 == r.r0
        assert arg2 == r.r1
        res = regalloc.try_allocate_reg(op.result)
        getattr(self.mc, opname)(fcond)
        self.mc.MOV_rr(res.value, r.r0.value, cond=fcond)
        regalloc.possibly_free_vars_for_op(op)
        return fcond
    return f

def gen_emit_cmp_op(condition, inverse=False):
    def f(self, op, regalloc, fcond):
        assert fcond == c.AL
        if not inverse:
            arg0 = op.getarg(0)
            arg1 = op.getarg(1)
        else:
            arg0 = op.getarg(1)
            arg1 = op.getarg(0)
        res = regalloc.try_allocate_reg(op.result)
        # XXX consider swapping argumentes if arg0 is const
        if self._check_imm_arg(arg1) and not isinstance(arg0, ConstInt):
            reg = regalloc.try_allocate_reg(arg0)
            self.mc.CMP_ri(reg.value, imm=arg1.getint(), cond=fcond)
        else:
            reg = self._put_in_reg(arg0, regalloc)
            reg2 = self._put_in_reg(arg1, regalloc)
            self.mc.CMP_rr(reg.value, reg2.value)
            regalloc.possibly_free_var(reg2)

        inv = c.get_opposite_of(condition)
        self.mc.MOV_ri(res.value, 1, cond=condition)
        self.mc.MOV_ri(res.value, 0, cond=inv)
        return condition
    return f

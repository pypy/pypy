from pypy.jit.backend.arm import conditions as c
from pypy.jit.backend.arm import registers as r
from pypy.jit.metainterp.history import ConstInt, BoxInt

def gen_emit_op_unary_cmp(true_cond, false_cond):
    def f(self, op, regalloc, fcond):
        a0 = op.getarg(0)
        reg = regalloc.make_sure_var_in_reg(a0, imm_fine=False)
        res = regalloc.force_allocate_reg(op.result, [a0])
        self.mc.CMP_ri(reg.value, 0)
        self.mc.MOV_ri(res.value, 1, true_cond)
        self.mc.MOV_ri(res.value, 0, false_cond)
        regalloc.possibly_free_vars_for_op(op)
        return fcond
    return f

def gen_emit_op_ri(opname, imm_size=0xFF, commutative=True, allow_zero=True):
    def f(self, op, regalloc, fcond):
        ri_op = getattr(self.mc, '%s_ri' % opname)
        rr_op = getattr(self.mc, '%s_rr' % opname)

        arg0 = op.getarg(0)
        arg1 = op.getarg(1)
        imm_a0 = self._check_imm_arg(arg0, imm_size, allow_zero=allow_zero)
        imm_a1 = self._check_imm_arg(arg1, imm_size, allow_zero=allow_zero)
        if commutative and imm_a0:
            l0 = regalloc.make_sure_var_in_reg(arg0, imm_fine=imm_a0)
            l1 = regalloc.make_sure_var_in_reg(arg1, [arg0])
            res = regalloc.force_allocate_reg(op.result, [arg0, arg1])
            ri_op(res.value, l1.value, imm=l0.getint(), cond=fcond)
        elif imm_a1:
            l0 = regalloc.make_sure_var_in_reg(arg0, imm_fine=False)
            l1 = regalloc.make_sure_var_in_reg(arg1, [arg0], imm_fine=True)
            res = regalloc.force_allocate_reg(op.result, [arg0, arg1])
            ri_op(res.value, l0.value, imm=l1.getint(), cond=fcond)
        else:
            l0 = regalloc.make_sure_var_in_reg(arg0, imm_fine=False)
            l1 = regalloc.make_sure_var_in_reg(arg1, [arg0], imm_fine=False)
            res = regalloc.force_allocate_reg(op.result, [arg0, arg1])
            rr_op(res.value, l0.value, l1.value)
        regalloc.possibly_free_vars_for_op(op)
        return fcond
    return f

def gen_emit_op_by_helper_call(opname):
    def f(self, op, regalloc, fcond):
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        arg1 = regalloc.make_sure_var_in_reg(a0, selected_reg=r.r0, imm_fine=False)
        arg2 = regalloc.make_sure_var_in_reg(a1, [a0], selected_reg=r.r1, imm_fine=False)
        assert arg1 == r.r0
        assert arg2 == r.r1
        res = regalloc.force_allocate_reg(op.result, selected_reg=r.r0)
        getattr(self.mc, opname)(fcond)
        regalloc.possibly_free_vars_for_op(op)
        return fcond
    return f

def gen_emit_cmp_op(condition, inverse=False):
    def f(self, op, regalloc, fcond):
        if not inverse:
            arg0 = op.getarg(0)
            arg1 = op.getarg(1)
        else:
            arg0 = op.getarg(1)
            arg1 = op.getarg(0)
        # XXX consider swapping argumentes if arg0 is const
        imm_a0 = self._check_imm_arg(arg0)
        imm_a1 = self._check_imm_arg(arg1)
        if imm_a1 and not imm_a0:
            l0 = regalloc.make_sure_var_in_reg(arg0, imm_fine=False)
            l1 = regalloc.make_sure_var_in_reg(arg1, [l0])
            res = regalloc.force_allocate_reg(op.result)
            self.mc.CMP_ri(l0.value, imm=l1.getint(), cond=fcond)
        else:
            l0 = regalloc.make_sure_var_in_reg(arg0, imm_fine=False)
            l1 = regalloc.make_sure_var_in_reg(arg1, [l0], imm_fine=False)
            res = regalloc.force_allocate_reg(op.result)
            self.mc.CMP_rr(l0.value, l1.value, cond=fcond)

        inv = c.get_opposite_of(condition)
        self.mc.MOV_ri(res.value, 1, cond=condition)
        self.mc.MOV_ri(res.value, 0, cond=inv)
        regalloc.possibly_free_vars_for_op(op)
        return fcond
    return f

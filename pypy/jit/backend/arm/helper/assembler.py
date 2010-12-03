from pypy.jit.backend.arm import conditions as c
from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm.codebuilder import AbstractARMv7Builder
from pypy.jit.metainterp.history import ConstInt, BoxInt

def gen_emit_op_unary_cmp(true_cond, false_cond):
    def f(self, op, regalloc, fcond):
        assert fcond is not None
        a0 = op.getarg(0)
        reg, box = self._ensure_value_is_boxed(a0, regalloc)
        res = regalloc.force_allocate_reg(op.result, [box])
        regalloc.possibly_free_vars([a0, box, op.result])

        self.mc.CMP_ri(reg.value, 0)
        self.mc.MOV_ri(res.value, 1, true_cond)
        self.mc.MOV_ri(res.value, 0, false_cond)
        return fcond
    return f

def gen_emit_op_ri(opname, imm_size=0xFF, commutative=True, allow_zero=True):
    ri_op = getattr(AbstractARMv7Builder, '%s_ri' % opname)
    rr_op = getattr(AbstractARMv7Builder, '%s_rr' % opname)
    def f(self, op, regalloc, fcond):
        assert fcond is not None
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        boxes = list(op.getarglist())
        imm_a0 = self._check_imm_arg(a0, imm_size, allow_zero=allow_zero)
        imm_a1 = self._check_imm_arg(a1, imm_size, allow_zero=allow_zero)
        if not imm_a0 and imm_a1:
            l0, box = self._ensure_value_is_boxed(a0, regalloc)
            boxes.append(box)
            l1 = regalloc.make_sure_var_in_reg(a1, boxes)
        elif commutative and imm_a0 and not imm_a1:
            l1 = regalloc.make_sure_var_in_reg(a0, boxes)
            l0, box = self._ensure_value_is_boxed(a1, regalloc, boxes)
            boxes.append(box)
        else:
            l0, box = self._ensure_value_is_boxed(a0, regalloc, boxes)
            boxes.append(box)
            l1, box = self._ensure_value_is_boxed(a1, regalloc, boxes)
            boxes.append(box)
        res = regalloc.force_allocate_reg(op.result, boxes)
        regalloc.possibly_free_vars(boxes)
        regalloc.possibly_free_var(op.result)

        if l1.is_imm():
            ri_op(self.mc, res.value, l0.value, imm=l1.value, cond=fcond)
        else:
            rr_op(self.mc, res.value, l0.value, l1.value)
        return fcond
    return f

def gen_emit_op_by_helper_call(opname):
    def f(self, op, regalloc, fcond):
        assert fcond is not None
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        arg1 = regalloc.make_sure_var_in_reg(a0, selected_reg=r.r0, imm_fine=False)
        arg2 = regalloc.make_sure_var_in_reg(a1, selected_reg=r.r1, imm_fine=False)
        assert arg1 == r.r0
        assert arg2 == r.r1
        regalloc.before_call()
        getattr(self.mc, opname)(fcond)
        regalloc.after_call(op.result)

        regalloc.possibly_free_var(a0)
        regalloc.possibly_free_var(a1)
        if op.result:
            regalloc.possibly_free_var(op.result)
        return fcond
    return f

def gen_emit_cmp_op(condition, inverse=False):
    def f(self, op, regalloc, fcond):
        assert fcond is not None
        boxes = list(op.getarglist())
        if not inverse:
            arg0, arg1 = boxes
        else:
            arg1, arg0 = boxes
        # XXX consider swapping argumentes if arg0 is const
        imm_a0 = self._check_imm_arg(arg0)
        imm_a1 = self._check_imm_arg(arg1)

        l0, box = self._ensure_value_is_boxed(arg0, regalloc, forbidden_vars=boxes)
        boxes.append(box)
        if imm_a1 and not imm_a0:
            l1 = regalloc.make_sure_var_in_reg(arg1, boxes)
        else:
            l1, box = self._ensure_value_is_boxed(arg1, regalloc, forbidden_vars=boxes)
            boxes.append(box)
        res = regalloc.force_allocate_reg(op.result)
        regalloc.possibly_free_vars(boxes)
        regalloc.possibly_free_var(op.result)

        inv = c.get_opposite_of(condition)
        if l1.is_imm():
            self.mc.CMP_ri(l0.value, imm=l1.getint(), cond=fcond)
        else:
            self.mc.CMP_rr(l0.value, l1.value, cond=fcond)
        self.mc.MOV_ri(res.value, 1, cond=condition)
        self.mc.MOV_ri(res.value, 0, cond=inv)
        return fcond
    return f

from pypy.jit.backend.arm import conditions as c
from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm.codebuilder import AbstractARMv7Builder
from pypy.jit.metainterp.history import ConstInt, BoxInt

def gen_emit_op_unary_cmp(true_cond, false_cond):
    def f(self, op, arglocs, regalloc, fcond):
        assert fcond is not None
        reg, res = arglocs
        self.mc.CMP_ri(reg.value, 0)
        self.mc.MOV_ri(res.value, 1, true_cond)
        self.mc.MOV_ri(res.value, 0, false_cond)
        return fcond
    return f

def gen_emit_op_ri(opname, imm_size=0xFF, commutative=True, allow_zero=True):
    ri_op = getattr(AbstractARMv7Builder, '%s_ri' % opname)
    rr_op = getattr(AbstractARMv7Builder, '%s_rr' % opname)
    def f(self, op, arglocs, regalloc, fcond):
        assert fcond is not None
        l0, l1, res = arglocs
        if l1.is_imm():
            ri_op(self.mc, res.value, l0.value, imm=l1.value, cond=fcond)
        else:
            rr_op(self.mc, res.value, l0.value, l1.value)
        return fcond
    return f

def gen_emit_op_by_helper_call(opname):
    helper = getattr(AbstractARMv7Builder, opname)
    def f(self, op, arglocs, regalloc, fcond):
        assert fcond is not None
        self.mc.PUSH([reg.value for reg in r.caller_resp][1:])
        helper(self.mc, fcond)
        self.mc.POP([reg.value for reg in r.caller_resp][1:])
        return fcond
    return f

def gen_emit_cmp_op(condition):
    def f(self, op, arglocs, regalloc, fcond):
        l0, l1, res = arglocs

        inv = c.get_opposite_of(condition)
        if l1.is_imm():
            self.mc.CMP_ri(l0.value, imm=l1.getint(), cond=fcond)
        else:
            self.mc.CMP_rr(l0.value, l1.value, cond=fcond)
        self.mc.MOV_ri(res.value, 1, cond=condition)
        self.mc.MOV_ri(res.value, 0, cond=inv)
        return fcond
    return f

def gen_emit_float_op(opname):
    op_rr = getattr(AbstractARMv7Builder, opname)
    def f(self, op, arglocs, regalloc, fcon):
        arg1, arg2, result = arglocs
        op_rr(self.mc, result.value, arg1.value, arg2.value)
    return f

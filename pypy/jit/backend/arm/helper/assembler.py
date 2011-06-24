from __future__ import with_statement
from pypy.jit.backend.arm import conditions as c
from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm.codebuilder import AbstractARMv7Builder
from pypy.jit.metainterp.history import ConstInt, BoxInt, FLOAT
from pypy.rlib.rarithmetic import r_uint, r_longlong, intmask

def gen_emit_op_unary_cmp(true_cond, false_cond):
    def f(self, op, arglocs, regalloc, fcond):
        assert fcond is not None
        reg, res = arglocs
        self.mc.CMP_ri(reg.value, 0)
        self.mc.MOV_ri(res.value, 1, true_cond)
        self.mc.MOV_ri(res.value, 0, false_cond)
        return fcond
    return f

def gen_emit_op_ri(opname):
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
        if op.result:
            regs = r.caller_resp[1:]
        else:
            regs = r.caller_resp
        with saved_registers(self.mc, regs, r.caller_vfp_resp, regalloc=regalloc):
            helper(self.mc, fcond)
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
    def f(self, op, arglocs, regalloc, fcond):
        arg1, arg2, result = arglocs
        op_rr(self.mc, result.value, arg1.value, arg2.value)
        return fcond
    return f
def gen_emit_unary_float_op(opname):
    op_rr = getattr(AbstractARMv7Builder, opname)
    def f(self, op, arglocs, regalloc, fcond):
        arg1, result = arglocs
        op_rr(self.mc, result.value, arg1.value)
        return fcond
    return f

def gen_emit_float_cmp_op(cond):
    def f(self, op, arglocs, regalloc, fcond):
        arg1, arg2, res = arglocs
        inv = c.get_opposite_of(cond)
        self.mc.VCMP(arg1.value, arg2.value)
        self.mc.VMRS(cond=fcond)
        self.mc.MOV_ri(res.value, 1, cond=cond)
        self.mc.MOV_ri(res.value, 0, cond=inv)
        return fcond
    return f

class saved_registers(object):
    def __init__(self, assembler, regs_to_save, vfp_regs_to_save=None, regalloc=None):
        self.assembler = assembler
        self.regalloc = regalloc
        if vfp_regs_to_save is None:
            vfp_regs_to_save = []
        if self.regalloc:
            self._filter_regs(regs_to_save, vfp_regs_to_save)
        else:
            self.regs = regs_to_save
            self.vfp_regs = vfp_regs_to_save

    def __enter__(self):
        if len(self.regs) > 0:
            self.assembler.PUSH([r.value for r in self.regs])
        if len(self.vfp_regs) > 0:
            self.assembler.VPUSH([r.value for r in self.vfp_regs])

    def __exit__(self, *args):
        if len(self.vfp_regs) > 0:
            self.assembler.VPOP([r.value for r in self.vfp_regs])
        if len(self.regs) > 0:
            self.assembler.POP([r.value for r in self.regs])

    def _filter_regs(self, regs_to_save, vfp_regs_to_save):
        regs = []
        for box, reg in self.regalloc.rm.reg_bindings.iteritems():
            if reg is r.ip or (reg in regs_to_save and self.regalloc.stays_alive(box)):
                regs.append(reg)
        self.regs = regs
        regs = []
        for box, reg in self.regalloc.vfprm.reg_bindings.iteritems():
            if reg in vfp_regs_to_save and self.regalloc.stays_alive(box):
                regs.append(reg)
        self.vfp_regs = regs
def count_reg_args(args):
    reg_args = 0
    words = 0
    count = 0
    for x in range(min(len(args), 4)):
        if args[x].type == FLOAT:
            words += 2
            if count % 2 != 0:
                words += 1
                count = 0
        else:
            count += 1
            words += 1
        reg_args += 1
        if words > 4:
            reg_args = x
            break
    return reg_args

def decode32(mem, index):
    return intmask(ord(mem[index])
            | ord(mem[index+1]) << 8
            | ord(mem[index+2]) << 16
            | ord(mem[index+3]) << 24)

def decode64(mem, index):
    low = decode32(mem, index)
    index += 4
    high = decode32(mem, index)
    return (r_longlong(high) << 32) | r_longlong(r_uint(low))

def encode32(mem, i, n):
    mem[i] = chr(n & 0xFF)
    mem[i+1] = chr((n >> 8) & 0xFF)
    mem[i+2] = chr((n >> 16) & 0xFF)
    mem[i+3] = chr((n >> 24) & 0xFF)

def encode64(mem, i, n):
    for x in range(8):
        mem[i+x] = chr((n >> (x*8)) & 0xFF)

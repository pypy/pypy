#!/usr/bin/env python

from rpython.jit.backend.llsupport.assembler import BaseAssembler
from rpython.jit.backend.riscv import registers as r
from rpython.jit.metainterp.resoperation import rop


class OpAssembler(BaseAssembler):
    def emit_op_int_add(self, op, arglocs):
        l0, l1, res = arglocs
        assert not l0.is_imm()
        if l1.is_imm():
            self.mc.ADDI(res.value, l0.value, l1.value)
        else:
            self.mc.ADD(res.value, l0.value, l1.value)

    def emit_op_int_sub(self, op, arglocs):
        l0, l1, res = arglocs
        assert not l0.is_imm()
        if l1.is_imm():
            self.mc.ADDI(res.value, l0.value, -l1.value)
        else:
            self.mc.SUB(res.value, l0.value, l1.value)

    def emit_op_int_mul(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.MUL(res.value, l0.value, l1.value)

    def emit_op_uint_mul_high(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.MULHU(res.value, l0.value, l1.value)

    def emit_op_int_and(self, op, arglocs):
        l0, l1, res = arglocs
        assert not l0.is_imm()
        if l1.is_imm():
            self.mc.ANDI(res.value, l0.value, l1.value)
        else:
            self.mc.AND(res.value, l0.value, l1.value)

    def emit_op_int_or(self, op, arglocs):
        l0, l1, res = arglocs
        assert not l0.is_imm()
        if l1.is_imm():
            self.mc.ORI(res.value, l0.value, l1.value)
        else:
            self.mc.OR(res.value, l0.value, l1.value)

    def emit_op_int_xor(self, op, arglocs):
        l0, l1, res = arglocs
        assert not l0.is_imm()
        if l1.is_imm():
            self.mc.XORI(res.value, l0.value, l1.value)
        else:
            self.mc.XOR(res.value, l0.value, l1.value)

    def emit_op_int_lshift(self, op, arglocs):
        l0, l1, res = arglocs
        assert not l0.is_imm()
        if l1.is_imm():
            self.mc.SLLI(res.value, l0.value, l1.value)
        else:
            self.mc.SLL(res.value, l0.value, l1.value)

    def emit_op_int_rshift(self, op, arglocs):
        l0, l1, res = arglocs
        assert not l0.is_imm()
        if l1.is_imm():
            self.mc.SRAI(res.value, l0.value, l1.value)
        else:
            self.mc.SRA(res.value, l0.value, l1.value)

    def emit_op_uint_rshift(self, op, arglocs):
        l0, l1, res = arglocs
        assert not l0.is_imm()
        if l1.is_imm():
            self.mc.SRLI(res.value, l0.value, l1.value)
        else:
            self.mc.SRL(res.value, l0.value, l1.value)

    def _emit_op_int_lt(self, op, arglocs):
        l0, l1, res = arglocs
        assert not l0.is_imm()
        if l1.is_imm():
            self.mc.SLTI(res.value, l0.value, l1.value)
        else:
            self.mc.SLT(res.value, l0.value, l1.value)

    emit_op_int_lt = _emit_op_int_lt
    emit_op_int_gt = _emit_op_int_lt

    def _emit_op_int_le(self, op, arglocs):
        l0, l1, res = arglocs
        if l1.is_imm():
            self.mc.SLTI(res.value, l0.value, l1.value + 1)
        else:
            if l0.is_imm():
                self.mc.SLTI(res.value, l1.value, l0.value)
            else:
                self.mc.SLT(res.value, l1.value, l0.value)
            self.mc.XORI(res.value, res.value, 1)

    emit_op_int_le = _emit_op_int_le
    emit_op_int_ge = _emit_op_int_le

    def _emit_op_uint_lt(self, op, arglocs):
        l0, l1, res = arglocs
        assert not l0.is_imm()
        if l1.is_imm():
            self.mc.SLTIU(res.value, l0.value, l1.value)
        else:
            self.mc.SLTU(res.value, l0.value, l1.value)

    emit_op_uint_lt = _emit_op_uint_lt
    emit_op_uint_gt = _emit_op_uint_lt

    def _emit_op_uint_le(self, op, arglocs):
        l0, l1, res = arglocs
        if l1.is_imm():
            if l1.value == -1:
                # uint_le(x, -1) is always true.
                self.mc.load_int_imm(res.value, 1)
            else:
                self.mc.SLTIU(res.value, l0.value, l1.value + 1)
        else:
            if l0.is_imm():
                self.mc.SLTIU(res.value, l1.value, l0.value)
            else:
                self.mc.SLTU(res.value, l1.value, l0.value)
            self.mc.XORI(res.value, res.value, 1)

    emit_op_uint_le = _emit_op_uint_le
    emit_op_uint_ge = _emit_op_uint_le

    def emit_op_int_eq(self, op, arglocs):
        l0, l1, res = arglocs
        assert not l0.is_imm()
        if l1.is_imm():
            if l1.value == 0:
                self.mc.SEQZ(res.value, l0.value)
            else:
                self.mc.XORI(res.value, l0.value, l1.value)
                self.mc.SEQZ(res.value, res.value)
        else:
            self.mc.XOR(res.value, l0.value, l1.value)
            self.mc.SEQZ(res.value, res.value)

    def emit_op_int_ne(self, op, arglocs):
        l0, l1, res = arglocs
        assert not l0.is_imm()
        if l1.is_imm():
            if l1.value == 0:
                self.mc.SNEZ(res.value, l0.value)
            else:
                self.mc.XORI(res.value, l0.value, l1.value)
                self.mc.SNEZ(res.value, res.value)
        else:
            self.mc.XOR(res.value, l0.value, l1.value)
            self.mc.SNEZ(res.value, res.value)

    def emit_op_int_is_true(self, op, arglocs):
        l0, res = arglocs
        self.mc.SNEZ(res.value, l0.value)

    def emit_op_int_neg(self, op, arglocs):
        l0, res = arglocs
        self.mc.NEG(res.value, l0.value)

    def emit_op_int_invert(self, op, arglocs):
        l0, res = arglocs
        self.mc.NOT(res.value, l0.value)

    def emit_op_int_is_zero(self, op, arglocs):
        l0, res = arglocs
        self.mc.SEQZ(res.value, l0.value)

    def emit_op_float_add(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.FADD_D(res.value, l0.value, l1.value)

    def emit_op_float_sub(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.FSUB_D(res.value, l0.value, l1.value)

    def emit_op_float_mul(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.FMUL_D(res.value, l0.value, l1.value)

    def emit_op_float_truediv(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.FDIV_D(res.value, l0.value, l1.value)

    def _emit_op_float_lt(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.FLT_D(res.value, l0.value, l1.value)

    emit_op_float_lt = _emit_op_float_lt
    emit_op_float_gt = _emit_op_float_lt

    def _emit_op_float_le(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.FLE_D(res.value, l0.value, l1.value)

    emit_op_float_le = _emit_op_float_le
    emit_op_float_ge = _emit_op_float_le

    def emit_op_float_eq(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.FEQ_D(res.value, l0.value, l1.value)

    def emit_op_float_ne(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.FEQ_D(res.value, l0.value, l1.value)
        self.mc.XORI(res.value, res.value, 1)

    def emit_op_finish(self, op, arglocs):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if len(arglocs) > 0:
            [return_val] = arglocs
            if return_val.is_fp_reg():
                self.mc.store_float(return_val.value, r.jfp.value, base_ofs)
            else:
                self.mc.store_int(return_val.value, r.jfp.value, base_ofs)

        faildescrindex = self.get_gcref_from_faildescr(op.getdescr())
        self.store_jf_descr(faildescrindex)

        self._call_footer(self.mc)


def not_implemented_op(self, op, arglocs):
    print "[riscv/asm] %s not implemented" % op.getopname()
    raise NotImplementedError(op)

def not_implemented_comp_op(self, op, arglocs):
    print "[riscv/asm] %s not implemented" % op.getopname()
    raise NotImplementedError(op)

def not_implemented_guard_op(self, op, guard_op, arglocs, guard_branch_inst):
    print "[riscv/asm] %s not implemented" % op.getopname()
    raise NotImplementedError(op)

asm_operations = [not_implemented_op] * (rop._LAST + 1)
asm_guard_operations = [not_implemented_guard_op] * (rop._LAST + 1)
asm_comp_operations = [not_implemented_comp_op] * (rop._LAST + 1)

for name, value in OpAssembler.__dict__.iteritems():
    if name.startswith('emit_op_'):
        opname = name[len('emit_op_'):]
        num = getattr(rop, opname.upper())
        asm_operations[num] = value
    elif name.startswith('emit_guard_op_'):
        opname = name[len('emit_guard_op_'):]
        num = getattr(rop, opname.upper())
        asm_guard_operations[num] = value
    elif name.startswith('emit_comp_op_'):
        opname = name[len('emit_comp_op_'):]
        num = getattr(rop, opname.upper())
        asm_comp_operations[num] = value

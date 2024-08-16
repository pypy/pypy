#!/usr/bin/env python

from rpython.jit.backend.llsupport.assembler import BaseAssembler, GuardToken
from rpython.jit.backend.llsupport.descr import CallDescr, unpack_arraydescr
from rpython.jit.backend.llsupport.gcmap import allocate_gcmap
from rpython.jit.backend.riscv import registers as r
from rpython.jit.backend.riscv.arch import (
    ABI_STACK_ALIGN, FLEN, INST_SIZE, JITFRAME_FIXED_SIZE, XLEN)
from rpython.jit.backend.riscv.callbuilder import RISCVCallBuilder
from rpython.jit.backend.riscv.codebuilder import (
    AbstractRISCVBuilder, BRANCH_BUILDER, OverwritingBuilder)
from rpython.jit.backend.riscv.instruction_util import (
    COND_BEQ, COND_BNE, COND_INVALID, check_imm_arg, check_simm21_arg)
from rpython.jit.backend.riscv.rounding_modes import DYN, RTZ
from rpython.jit.metainterp.history import (
    AbstractFailDescr, ConstInt, FLOAT, INT, REF, TargetToken, VOID)
from rpython.jit.metainterp.resoperation import rop
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.rarithmetic import r_uint
from rpython.rtyper import rclass
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.lltypesystem.lloperation import llop


class OpAssembler(BaseAssembler):
    def emit_op_int_add(self, op, arglocs):
        l0, l1, res = arglocs
        assert not l0.is_imm()
        if l1.is_imm():
            self.mc.ADDI(res.value, l0.value, l1.value)
        else:
            self.mc.ADD(res.value, l0.value, l1.value)

    emit_op_nursery_ptr_increment = emit_op_int_add

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

    emit_comp_op_int_lt = emit_op_int_lt
    emit_comp_op_int_gt = emit_op_int_gt

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

    emit_comp_op_int_le = emit_op_int_le
    emit_comp_op_int_ge = emit_op_int_ge

    def _emit_op_uint_lt(self, op, arglocs):
        l0, l1, res = arglocs
        assert not l0.is_imm()
        if l1.is_imm():
            self.mc.SLTIU(res.value, l0.value, l1.value)
        else:
            self.mc.SLTU(res.value, l0.value, l1.value)

    emit_op_uint_lt = _emit_op_uint_lt
    emit_op_uint_gt = _emit_op_uint_lt

    emit_comp_op_uint_lt = emit_op_uint_lt
    emit_comp_op_uint_gt = emit_op_uint_gt

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

    emit_comp_op_uint_le = emit_op_uint_le
    emit_comp_op_uint_ge = emit_op_uint_ge

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

    emit_op_ptr_eq = emit_op_instance_ptr_eq = emit_op_int_eq

    emit_comp_op_int_eq = emit_op_int_eq
    emit_comp_op_ptr_eq = emit_op_int_eq

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

    emit_op_ptr_ne = emit_op_instance_ptr_ne = emit_op_int_ne

    emit_comp_op_int_ne = emit_op_int_ne
    emit_comp_op_ptr_ne = emit_op_int_ne

    def emit_op_int_is_true(self, op, arglocs):
        l0, res = arglocs
        self.mc.SNEZ(res.value, l0.value)

    emit_comp_op_int_is_true = emit_op_int_is_true

    def emit_op_int_neg(self, op, arglocs):
        l0, res = arglocs
        self.mc.NEG(res.value, l0.value)

    def emit_op_int_invert(self, op, arglocs):
        l0, res = arglocs
        self.mc.NOT(res.value, l0.value)

    def emit_op_int_is_zero(self, op, arglocs):
        l0, res = arglocs
        self.mc.SEQZ(res.value, l0.value)

    emit_comp_op_int_is_zero = emit_op_int_is_zero

    def emit_op_int_force_ge_zero(self, op, arglocs):
        l0, res = arglocs
        self.mc.MV(res.value, l0.value)
        self.mc.BGEZ(l0.value, 8)  # Skip next instruction if l0 >= 0
        self.mc.MV(res.value, r.zero.value)

    def emit_op_int_signext(self, op, arglocs):
        l0, l1, res = arglocs

        assert l1.is_imm()
        num_bytes = l1.value

        if l0.is_stack():
            offset = l0.value
            if num_bytes == 1:
                self.mc.LB(res.value, r.jfp.value, offset)
            elif num_bytes == 2:
                self.mc.LH(res.value, r.jfp.value, offset)
            elif num_bytes == 4:
                self.mc.LW(res.value, r.jfp.value, offset)
            else:
                assert 0, 'unexpected int_signext number of bytes'
        else:
            # Register-to-register sign extension
            assert l0.is_core_reg()

            assert num_bytes == 1 or num_bytes == 2 or num_bytes == 4
            shift_amount = (XLEN - num_bytes) * 8

            self.mc.SLLI(res.value, l0.value, shift_amount)
            self.mc.SRAI(res.value, res.value, shift_amount)

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

    emit_comp_op_float_lt = emit_op_float_lt
    emit_comp_op_float_gt = emit_op_float_gt

    def _emit_op_float_le(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.FLE_D(res.value, l0.value, l1.value)

    emit_op_float_le = _emit_op_float_le
    emit_op_float_ge = _emit_op_float_le

    emit_comp_op_float_le = emit_op_float_le
    emit_comp_op_float_ge = emit_op_float_ge

    def emit_op_float_eq(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.FEQ_D(res.value, l0.value, l1.value)

    emit_comp_op_float_eq = emit_op_float_eq

    def emit_op_float_ne(self, op, arglocs):
        l0, l1, res = arglocs
        self.mc.FEQ_D(res.value, l0.value, l1.value)
        self.mc.XORI(res.value, res.value, 1)

    emit_comp_op_float_ne = emit_op_float_ne

    def emit_op_float_neg(self, op, arglocs):
        l0, res = arglocs
        self.mc.FNEG_D(res.value, l0.value)

    def emit_op_float_abs(self, op, arglocs):
        l0, res = arglocs
        self.mc.FABS_D(res.value, l0.value)

    def emit_op_cast_float_to_int(self, op, arglocs):
        l0, res = arglocs
        self.mc.FCVT_L_D(res.value, l0.value, RTZ.value)

    def emit_op_cast_int_to_float(self, op, arglocs):
        l0, res = arglocs
        self.mc.FCVT_D_L(res.value, l0.value, DYN.value)

    def emit_op_convert_float_bytes_to_longlong(self, op, arglocs):
        l0, res = arglocs
        self.mc.FMV_X_D(res.value, l0.value)

    def emit_op_convert_longlong_bytes_to_float(self, op, arglocs):
        l0, res = arglocs
        self.mc.FMV_D_X(res.value, l0.value)

    def emit_op_gc_store(self, op, arglocs):
        value_loc, base_loc, ofs_loc, size_loc = arglocs
        self._store_to_mem(value_loc, base_loc, ofs_loc, size_loc.value)

    def _emit_op_gc_load(self, op, arglocs):
        base_loc, ofs_loc, res_loc, nsize_loc = arglocs
        nsize = nsize_loc.value
        signed = (nsize < 0)
        self._load_from_mem(res_loc, base_loc, ofs_loc, abs(nsize), signed)

    emit_op_gc_load_i = _emit_op_gc_load
    emit_op_gc_load_r = _emit_op_gc_load
    emit_op_gc_load_f = _emit_op_gc_load

    def _emit_gc_indexed_full_offset(self, index_loc, ofs_loc):
        # Compute the full offset.
        #
        # Note: result = (index * scale) + ofs, where scale == 1

        scratch_reg = r.x31
        assert index_loc.is_core_reg()

        if ofs_loc.is_imm():
            if ofs_loc.value == 0:
                return index_loc
            if check_imm_arg(ofs_loc.value):
                self.mc.ADDI(scratch_reg.value, index_loc.value, ofs_loc.value)
            else:
                assert index_loc is not scratch_reg
                self.mc.load_int_imm(scratch_reg.value, ofs_loc.value)
                self.mc.ADD(scratch_reg.value, scratch_reg.value,
                            index_loc.value)
            return scratch_reg

        self.mc.ADD(scratch_reg.value, index_loc.value, ofs_loc.value)
        return scratch_reg

    def emit_op_gc_store_indexed(self, op, arglocs):
        value_loc, base_loc, index_loc, ofs_loc, size_loc = arglocs

        full_ofs_loc = self._emit_gc_indexed_full_offset(index_loc, ofs_loc)
        self._store_to_mem(value_loc, base_loc, full_ofs_loc, size_loc.value)

    def _emit_op_gc_load_indexed(self, op, arglocs):
        base_loc, index_loc, ofs_loc, res_loc, nsize_loc = arglocs

        nsize = nsize_loc.value
        signed = (nsize < 0)

        full_ofs_loc = self._emit_gc_indexed_full_offset(index_loc, ofs_loc)
        self._load_from_mem(res_loc, base_loc, full_ofs_loc, abs(nsize),
                            signed)

    emit_op_gc_load_indexed_i = _emit_op_gc_load_indexed
    emit_op_gc_load_indexed_r = _emit_op_gc_load_indexed
    emit_op_gc_load_indexed_f = _emit_op_gc_load_indexed

    def _normalize_base_offset(self, base_loc, ofs_loc, scratch_reg):
        # Normalize the calculation of `base + offset`.

        if ofs_loc.is_core_reg():
            self.mc.ADD(scratch_reg.value, base_loc.value, ofs_loc.value)
            return (scratch_reg, 0)

        assert ofs_loc.is_imm()
        if check_imm_arg(ofs_loc.value):
            return (base_loc, ofs_loc.value)
        else:
            assert base_loc is not scratch_reg
            self.mc.load_int_imm(scratch_reg.value, ofs_loc.value)
            self.mc.ADD(scratch_reg.value, scratch_reg.value,
                        base_loc.value)
            return (scratch_reg, 0)

    def _store_to_mem(self, value_loc, base_loc, ofs_loc, type_size):
        # Store a value of size `type_size` at the address
        # `base_ofs + ofs_loc`.
        #
        # Note: `ofs_loc` can be `scratch_reg`. Use with caution.

        assert XLEN == 8 and FLEN == 8, 'implementation below assumes 64-bit'
        assert base_loc.is_core_reg()

        scratch_reg = r.x31
        base_loc, ofs_int = self._normalize_base_offset(base_loc, ofs_loc,
                                                        scratch_reg)

        if type_size == 8:
            # 64-bit
            if value_loc.is_float():
                # 64-bit float
                self.mc.FSD(value_loc.value, base_loc.value, ofs_int)
                return
            # 64-bit int
            self.mc.SD(value_loc.value, base_loc.value, ofs_int)
            return

        if type_size == 4:
            # 32-bit int
            self.mc.SW(value_loc.value, base_loc.value, ofs_int)
            return

        if type_size == 2:
            # 16-bit int
            self.mc.SH(value_loc.value, base_loc.value, ofs_int)
            return

        assert type_size == 1
        self.mc.SB(value_loc.value, base_loc.value, ofs_int)

    def _load_from_mem(self, res_loc, base_loc, ofs_loc, type_size, signed):
        # Load a value of `type_size` bytes, from the memory location
        # `base_loc + ofs_loc`.

        assert XLEN == 8 and FLEN == 8, 'implementation below assumes 64-bit'
        assert base_loc.is_core_reg()

        scratch_reg = r.x31
        base_loc, ofs_int = self._normalize_base_offset(base_loc, ofs_loc,
                                                        scratch_reg)

        if type_size == 8:
            # 64-bit
            if res_loc.is_float():
                # 64-bit float
                self.mc.FLD(res_loc.value, base_loc.value, ofs_int)
                return
            # 64-bit int
            self.mc.LD(res_loc.value, base_loc.value, ofs_int)
            return

        if type_size == 4:
            # 32-bit int
            if signed:
                self.mc.LW(res_loc.value, base_loc.value, ofs_int)
            else:
                self.mc.LWU(res_loc.value, base_loc.value, ofs_int)
            return

        if type_size == 2:
            # 16-bit int
            if signed:
                self.mc.LH(res_loc.value, base_loc.value, ofs_int)
            else:
                self.mc.LHU(res_loc.value, base_loc.value, ofs_int)
            return

        assert type_size == 1
        # 8-bit int
        if signed:
            self.mc.LB(res_loc.value, base_loc.value, ofs_int)
        else:
            self.mc.LBU(res_loc.value, base_loc.value, ofs_int)

    def _build_guard_token(self, op, frame_depth, arglocs, offset):
        descr = op.getdescr()
        assert isinstance(descr, AbstractFailDescr)

        gcmap = allocate_gcmap(self, frame_depth, JITFRAME_FIXED_SIZE)
        faildescrindex = self.get_gcref_from_faildescr(descr)
        return GuardToken(self.cpu, gcmap, descr,
                          failargs=op.getfailargs(), fail_locs=arglocs,
                          guard_opnum=op.getopnum(), frame_depth=frame_depth,
                          faildescrindex=faildescrindex)

    def _emit_pending_guard(self, op, arglocs, is_guard_not_invalidated=False):
        pos = self.mc.get_relative_pos()
        guardtok = self._build_guard_token(op, arglocs[0].value, arglocs[1:],
                                           pos)
        guardtok.offset = pos
        self.pending_guards.append(guardtok)
        assert guardtok.guard_not_invalidated() == is_guard_not_invalidated
        if is_guard_not_invalidated:
            # For `GUARD_NOT_INVALIDATED`, just emit an no-op.  It will be
            # patched by `invalidate_loop` (in `runner.py`) when invalidation
            # is needed.
            self.mc.NOP()
        else:
            # Emit an `EBREAK` here and `process_pending_guards` will patch it
            # with a branch to a recovery stub.
            self.mc.EBREAK()

    def emit_op_guard_true(self, op, arglocs):
        l0 = arglocs[0]
        self.mc.BNEZ(l0.value, 8)
        self._emit_pending_guard(op, arglocs[1:])

    emit_op_guard_nonnull = emit_op_guard_true

    def emit_op_guard_false(self, op, arglocs):
        l0 = arglocs[0]
        self.mc.BEQZ(l0.value, 8)
        self._emit_pending_guard(op, arglocs[1:])

    emit_op_guard_isnull = emit_op_guard_false

    def emit_op_guard_value(self, op, arglocs):
        l0 = arglocs[0]
        l1 = arglocs[1]
        if l0.is_fp_reg():
            self.mc.FEQ_D(r.x31.value, l0.value, l1.value)
            self.mc.BNEZ(r.x31.value, 8)
        else:
            self.mc.BEQ(l0.value, l1.value, 8)
        self._emit_pending_guard(op, arglocs[2:])

    def _emit_guard_op_guard_bool_op(self, op, guard_op, arglocs,
                                     guard_branch_inst):
        l0 = arglocs[0]
        l1 = arglocs[1]
        BRANCH_BUILDER[guard_branch_inst](self.mc, l0.value, l1.value, 8)
        self._emit_pending_guard(guard_op, arglocs[2:])

    emit_guard_op_guard_true  = _emit_guard_op_guard_bool_op
    emit_guard_op_guard_false = _emit_guard_op_guard_bool_op

    def _emit_guard_op_guard_overflow_op(self, op, guard_op, arglocs,
                                         guard_branch_inst):
        l0 = arglocs[0]
        l1 = arglocs[1]
        res = arglocs[2]
        tmp0 = arglocs[3]
        tmp1 = arglocs[4]

        opnum = op.getopnum()
        if opnum == rop.INT_ADD_OVF:
            self.mc.ADD(res.value, l0.value, l1.value)
            self.mc.SLT(tmp0.value, res.value, l0.value)
            self.mc.SLTI(tmp1.value, l1.value, 0)
        elif opnum == rop.INT_SUB_OVF:
            self.mc.SUB(res.value, l0.value, l1.value)
            self.mc.SLT(tmp0.value, res.value, l0.value)
            self.mc.SGTZ(tmp1.value, l1.value)
        elif opnum == rop.INT_MUL_OVF:
            self.mc.MUL(res.value, l0.value, l1.value)
            self.mc.MULH(tmp0.value, l0.value, l1.value)
            self.mc.SRAI(tmp1.value, res.value, XLEN * 8 - 1)
        else:
            assert 0, 'unexpected overflow op'

        BRANCH_BUILDER[guard_branch_inst](self.mc, tmp0.value, tmp1.value, 8)
        self._emit_pending_guard(guard_op, arglocs[5:])

    emit_guard_op_guard_overflow    = _emit_guard_op_guard_overflow_op
    emit_guard_op_guard_no_overflow = _emit_guard_op_guard_overflow_op

    def _emit_load_typeid_from_obj(self, dest_loc, obj_loc):
        # Note that the typeid half-word is at offset 0 on a little-endian
        # machine; it would be at offset 2 or 4 on a big-endian machine.
        if XLEN == 8:
            self.mc.LWU(dest_loc.value, obj_loc.value, 0)
        else:
            self.mc.LHU(dest_loc.value, obj_loc.value, 0)

    def _emit_cmp_guard_gc_type(self, obj_loc, expected_typeid,
                                success_branch_offset):
        assert self.cpu.supports_guard_gc_type

        scratch_reg = r.x31
        scratch2_reg = r.ra
        self._emit_load_typeid_from_obj(scratch_reg, obj_loc)
        self.mc.load_int_imm(scratch2_reg.value, expected_typeid)
        self.mc.BEQ(scratch_reg.value, scratch2_reg.value,
                    success_branch_offset)

    def emit_op_guard_class(self, op, arglocs):
        # Implements guard_class(obj, cls):
        #
        #     if type(obj) != cls:
        #         goto guard_fail

        obj_loc, cls_loc = arglocs[:2]
        failargs = arglocs[2:]

        scratch_reg = r.x31
        scratch2_reg = r.ra
        offset = self.cpu.vtable_offset
        if offset is not None:
            self.mc.load_int_from_base_plus_offset(scratch_reg.value,
                                                   obj_loc.value, offset)
            self.mc.load_int_imm(scratch2_reg.value, cls_loc.value)
            self.mc.BEQ(scratch_reg.value, scratch2_reg.value, 8)
        else:
            expected_typeid = (self.cpu.gc_ll_descr
                               .get_typeid_from_classptr_if_gcremovetypeptr(
                                   cls_loc.value))
            self._emit_cmp_guard_gc_type(obj_loc, expected_typeid,
                                         success_branch_offset=8)
        self._emit_pending_guard(op, failargs)

    def emit_op_guard_nonnull_class(self, op, arglocs):
        # Implements guard_nonnull_class(obj, cls):
        #
        #     if !obj:
        #         goto guard_fail
        #     if type(obj) != cls:
        #         goto guard_fail

        obj_loc, cls_loc = arglocs[:2]
        failargs = arglocs[2:]

        scratch_reg = r.x31
        scratch2_reg = r.ra

        # LABEL[guard_nonnull]:
        # Patch Location: BEQZ obj, guard_fail
        branch_inst_location = self.mc.get_relative_pos()
        self.mc.EBREAK()

        offset = self.cpu.vtable_offset
        if offset is not None:
            # Test `type(obj) == cls`
            self.mc.load_int_from_base_plus_offset(scratch_reg.value,
                                                   obj_loc.value, offset)
            self.mc.load_int_imm(scratch2_reg.value, cls_loc.value)
            self.mc.BEQ(scratch_reg.value, scratch2_reg.value, 8)
        else:
            expected_typeid = (self.cpu.gc_ll_descr
                               .get_typeid_from_classptr_if_gcremovetypeptr(
                                   cls_loc.value))
            self._emit_cmp_guard_gc_type(obj_loc, expected_typeid,
                                         success_branch_offset=8)

        # LABEL[guard_fail]:
        currpos = self.mc.get_relative_pos()
        pmc = OverwritingBuilder(self.mc, branch_inst_location, INST_SIZE)
        pmc.BEQZ(obj_loc.value, currpos - branch_inst_location)

        self._emit_pending_guard(op, failargs)

    def emit_op_guard_gc_type(self, op, arglocs):
        obj_loc = arglocs[0]
        expected_typeid_imm = arglocs[1]
        failargs = arglocs[2:]

        self._emit_cmp_guard_gc_type(obj_loc, expected_typeid_imm.value,
                                     success_branch_offset=8)
        self._emit_pending_guard(op, failargs)

    def emit_op_guard_subclass(self, op, arglocs):
        assert self.cpu.supports_guard_gc_type
        obj_loc = arglocs[0]
        check_against_class_loc = arglocs[1]
        failargs = arglocs[2:]

        scratch_reg = r.x31
        scratch2_reg = r.ra

        offset = self.cpu.vtable_offset
        subclassrange_min_offset = self.cpu.subclassrange_min_offset
        if offset is not None:
            # Read this field to get the vtable pointer
            self.mc.load_int_from_base_plus_offset(scratch_reg.value,
                                                   obj_loc.value, offset)
            # Read the vtable's subclassrange_min field
            self.mc.load_int_from_base_plus_offset(scratch_reg.value,
                                                   scratch_reg.value,
                                                   subclassrange_min_offset,
                                                   tmp=scratch2_reg)
        else:
            # Read the typeid
            self._emit_load_typeid_from_obj(scratch_reg, obj_loc)
            # Read the vtable's subclassrange_min field, as a single step with
            # the correct offset.
            base_type_info, shift_by, sizeof_ti = (
                self.cpu.gc_ll_descr.get_translated_info_for_typeinfo())

            self.mc.load_int_imm(scratch2_reg.value,
                                 base_type_info + sizeof_ti +
                                 subclassrange_min_offset)
            if shift_by > 0:
                self.mc.SLLI(scratch_reg.value, scratch_reg.value, shift_by)
            self.mc.ADD(scratch_reg.value, scratch_reg.value,
                        scratch2_reg.value)
            self.mc.load_int(scratch_reg.value, scratch_reg.value, 0)

        # Get the two bounds to check against
        vtable_ptr = check_against_class_loc.value
        vtable_ptr = rffi.cast(rclass.CLASSTYPE, vtable_ptr)
        check_min = vtable_ptr.subclassrange_min
        check_max = vtable_ptr.subclassrange_max
        assert check_max > check_min
        check_diff = check_max - check_min - 1

        # Check by doing the unsigned comparison (max - min - 1) >= (tmp - min)
        self.mc.load_int_imm(scratch2_reg.value, check_min)
        self.mc.SUB(scratch_reg.value, scratch_reg.value, scratch2_reg.value)
        self.mc.load_int_imm(scratch2_reg.value, check_diff)
        self.mc.BGEU(scratch2_reg.value, scratch_reg.value, 8)

        self._emit_pending_guard(op, failargs)

    def emit_op_guard_is_object(self, op, arglocs):
        assert self.cpu.supports_guard_gc_type

        obj_loc = arglocs[0]
        failargs = arglocs[1:]

        scratch_reg = r.x31
        scratch2_reg = r.ra

        # Read the typeid, fetch one byte of the field 'infobits' from the big
        # typeinfo table, and check the flag 'T_IS_RPYTHON_INSTANCE'.
        self._emit_load_typeid_from_obj(scratch_reg, obj_loc)

        base_type_info, shift_by, sizeof_ti = (
            self.cpu.gc_ll_descr.get_translated_info_for_typeinfo())
        infobits_offset, IS_OBJECT_FLAG = (
            self.cpu.gc_ll_descr.get_translated_info_for_guard_is_object())

        self.mc.load_int_imm(scratch2_reg.value,
                             base_type_info + infobits_offset)
        if shift_by > 0:
            self.mc.SLLI(scratch_reg.value, scratch_reg.value, shift_by)
        self.mc.ADD(scratch_reg.value, scratch_reg.value, scratch2_reg.value)
        self.mc.LBU(scratch_reg.value, scratch_reg.value, 0)
        self.mc.ANDI(scratch_reg.value, scratch_reg.value,
                     IS_OBJECT_FLAG & 0xff)
        self.mc.BNEZ(scratch_reg.value, 8)
        self._emit_pending_guard(op, failargs)

    def emit_op_guard_not_invalidated(self, op, arglocs):
        self._emit_pending_guard(op, arglocs, is_guard_not_invalidated=True)

    def emit_op_guard_exception(self, op, arglocs):
        expected_exc_tp_loc, res_exc_val_loc = arglocs[:2]
        failargs = arglocs[2:]

        # Load the type of the pending exception.
        scratch_reg = r.x31
        self.mc.load_int_imm(scratch_reg.value, self.cpu.pos_exception())
        self.mc.load_int(scratch_reg.value, scratch_reg.value, 0)

        # Compare the expected type and pending type.
        self.mc.BEQ(scratch_reg.value, expected_exc_tp_loc.value, 8)
        self._emit_pending_guard(op, failargs)

        # Copy the exception value.
        self._store_and_reset_exception(self.mc, res_exc_val_loc)

    def emit_op_guard_no_exception(self, op, arglocs):
        failargs = arglocs  # All arglocs are for failargs

        scratch_reg = r.x31
        self.mc.load_int_imm(scratch_reg.value, self.cpu.pos_exception())
        self.mc.load_int(scratch_reg.value, scratch_reg.value, 0)

        self.mc.BEQZ(scratch_reg.value, 8)
        self._emit_pending_guard(op, failargs)

        # If the previous operation was a `COND_CALL`, overwrite its
        # conditional jump to jump over this GUARD_NO_EXCEPTION as well.
        if self._find_nearby_operation(-1).getopnum() == rop.COND_CALL:
            cond_branch_addr, branch_inst, arg = self.previous_cond_call_branch
            new_offset = self.mc.get_relative_pos() - cond_branch_addr
            pmc = OverwritingBuilder(self.mc, cond_branch_addr, INST_SIZE)
            BRANCH_BUILDER[branch_inst](pmc, arg.value, r.x0.value, new_offset)

    def emit_op_save_exc_class(self, op, arglocs):
        res = arglocs[0]
        self.mc.load_int_imm(res.value, self.cpu.pos_exception())
        self.mc.load_int(res.value, res.value, 0)

    def emit_op_save_exception(self, op, arglocs):
        self._store_and_reset_exception(self.mc, arglocs[0])

    def emit_op_restore_exception(self, op, arglocs):
        exc_tp_loc, exc_val_loc = arglocs
        self._restore_exception(self.mc, exc_val_loc, exc_tp_loc)

    def emit_op_check_memory_error(self, op, arglocs):
        self.propagate_memoryerror_if_reg_is_null(arglocs[0])

    def _emit_op_same_as(self, op, arglocs):
        l0, res = arglocs
        if l0 is not res:
            self.regalloc_mov(l0, res)

    emit_op_same_as_i = _emit_op_same_as
    emit_op_same_as_r = _emit_op_same_as
    emit_op_same_as_f = _emit_op_same_as
    emit_op_cast_ptr_to_int = _emit_op_same_as
    emit_op_cast_int_to_ptr = _emit_op_same_as

    def math_sqrt(self, op, arglocs):
        l1, res = arglocs
        self.mc.FSQRT_D(res.value, l1.value)

    def threadlocalref_get(self, op, arglocs):
        res_loc = arglocs[0]

        # Use `r.ra` as a scratch register.
        #
        # Note: Don't use `r.x31` here because `_load_from_mem` uses `r.x31` as
        # a scratch register when it must add large offset immediate.
        tls_reg = r.ra

        # Load TLS address
        self.mc.load_int(tls_reg.value, r.sp.value,
                         self.saved_threadlocal_addr)

        # TLS field offset as an immediate
        ofs_loc = self.imm(op.getarg(1).getint())

        # TLS field type
        calldescr = op.getdescr()
        type_size = calldescr.get_result_size()
        signed = calldescr.is_result_signed()

        self._load_from_mem(res_loc, tls_reg, ofs_loc, type_size, signed)

    def _emit_op_call(self, op, arglocs):
        is_call_release_gil = rop.is_call_release_gil(op.getopnum())

        # arglocs = [resloc, size, sign, funcloc, args...]
        # -- or --
        # arglocs = [resloc, size, sign, save_err_loc, funcloc, args...]

        resloc = arglocs[0]
        sizeloc = arglocs[1]
        signloc = arglocs[2]
        func_index = 3 + is_call_release_gil
        funcloc = arglocs[func_index]

        assert sizeloc.is_imm()
        assert signloc.is_imm()

        descr = op.getdescr()
        assert isinstance(descr, CallDescr)

        cb = RISCVCallBuilder(self, funcloc, arglocs[func_index + 1:], resloc,
                              descr.get_result_type(), sizeloc.value)
        cb.callconv = descr.get_call_conv()
        cb.argtypes = descr.get_arg_types()
        cb.restype  = descr.get_result_type()
        cb.ressize = sizeloc.value
        cb.ressign = signloc.value

        if is_call_release_gil:
            save_err_loc = arglocs[3]
            assert save_err_loc.is_imm()
            cb.emit_call_release_gil(save_err_loc.value)
        else:
            effectinfo = descr.get_extra_info()
            if effectinfo is None or effectinfo.check_can_collect():
                cb.emit()
            else:
                cb.emit_no_collect()

    emit_op_call_i = _emit_op_call
    emit_op_call_f = _emit_op_call
    emit_op_call_r = _emit_op_call
    emit_op_call_n = _emit_op_call

    def _emit_op_cond_call(self, op, arglocs):
        """Emit instructions for COND_CALL and COND_CALL_VALUE_I/R.

            # cond_call(cond, func, *args)
            cond = arglocs[0]
            if cond != 0:
                func(*args)

            # res = cond_call_value(cond, func, *args)
            # res = cond or func(*args)
            cond, res = arglocs
            if cond == 0:
                res = func(*args)
        """

        if len(arglocs) == 2:
            res_loc = arglocs[1]     # cond_call_value
        else:
            res_loc = None           # cond_call

        # see x86.regalloc for why we skip res_loc in the gcmap
        gcmap = self._regalloc.get_gcmap([res_loc])

        # Save the conditional branch position (will be overwritten after we
        # generate the instructions in the middle).
        cond_branch_addr = self.mc.get_relative_pos()
        self.mc.EBREAK()

        self.push_gcmap(self.mc, gcmap)

        # Load callee function address.
        callee_func_addr_reg = r.x30
        callee_func_addr = rffi.cast(lltype.Signed, op.getarg(1).getint())
        self.mc.load_int_imm(callee_func_addr_reg.value, callee_func_addr)

        # Check whether there are alive registers that we must reload after
        # cond_call.
        callee_only = False
        floats = False
        if self._regalloc is not None:
            for reg in self._regalloc.rm.reg_bindings.values():
                if reg not in self._regalloc.rm.save_around_call_regs:
                    break
            else:
                callee_only = True
            if self._regalloc.fprm.reg_bindings:
                floats = True

        # Jump to cond_call trampoline.
        trampoline_addr = self.cond_call_slowpath[floats * 2 + callee_only]
        assert trampoline_addr
        self.mc.load_int_imm(r.ra.value, trampoline_addr)
        self.mc.JALR(r.ra.value, r.ra.value, 0)

        # If this is a COND_CALL_VALUE, we need to move the result in place
        # from its current location
        if res_loc is not None:
            self.mc.MV(res_loc.value, r.x30.value)

        self.pop_gcmap(self.mc)

        # Overwrite the conditional branch offset.
        branch_dest_addr = self.mc.get_relative_pos()
        branch_offset = branch_dest_addr - cond_branch_addr
        pmc = OverwritingBuilder(self.mc, cond_branch_addr, INST_SIZE)
        if res_loc is None:
            pmc.BEQZ(arglocs[0].value, branch_offset)
            self.previous_cond_call_branch = (cond_branch_addr, COND_BEQ,
                                              arglocs[0])
        else:
            pmc.BNEZ(arglocs[0].value, branch_offset)
            self.previous_cond_call_branch = (cond_branch_addr, COND_BNE,
                                              arglocs[0])

    emit_op_cond_call = _emit_op_cond_call
    emit_op_cond_call_value_i = _emit_op_cond_call
    emit_op_cond_call_value_r = _emit_op_cond_call

    def emit_guard_op_cond_call(self, cond_op, op, arglocs, guard_branch_inst):
        # TODO: Optimize guard_branch_inst when cond_op is using integer
        # comparison.
        assert guard_branch_inst == COND_INVALID

        self._emit_op_cond_call(op, arglocs)

    def _write_barrier_fastpath(self, mc, descr, arglocs, tmplocs, array=False,
                                is_frame=False):
        # Emits the fast path for a GC write barrier.
        #
        # This function emits instructions that is equivalent to
        # `write_barrier` or `write_barrier_from_array` in
        # `rpython/memory/gc/incminimark.py`.
        #
        # This fast path `GCFLAG_TRACK_YOUNG_PTRS` (`jit_wb_if_flag`) and
        # `GCFLAG_CARDS_SET` (`jit_wb_cards_set`).  This is the overall
        # structure of this function:
        #
        #     if GCFLAG_TRACK_YOUNG_PTRS | GCFLAG_CARDS_SET:
        #       if GCFLAG_CARDS_SET:
        #         update_card_table()
        #         return
        #       write_barrier_slowpath()
        #       if GCFLAG_CARDS_SET:
        #         update_card_table()
        #
        # The card table is a utility data structure to assist generational GC.
        # It is prepended to *large* arrays so that the garbage collector
        # doesn't have to scan the complete array object if only some of them
        # are updated.  The card table maps `card_page_indices` (default: 128)
        # indices into one bit, thus we need the byte/bit index calculation.
        #
        # The `write_barrier_slowpath` (`jit_remember_young_pointer_from_array`)
        # only updates the `GCFLAGS_CARDS_SET` bit in its fast path, thus we
        # must update card table afterward.
        #
        # OTOH, small arrays don't have card tables, thus we need the second
        # `if GCFLAG_CARDS_SET` after returning from `write_barrier_slowpath`.

        if we_are_translated():
            cls = self.cpu.gc_ll_descr.has_write_barrier_class()
            assert cls is not None and isinstance(descr, cls)

        card_marking = 0
        mask = descr.jit_wb_if_flag_singlebyte
        if array and descr.jit_wb_cards_set != 0:
            # Asserts the assumptions the rest of the `_write_barrier_fastpath`
            # function and `self.wb_slowpath[n]`.
            assert (descr.jit_wb_cards_set_byteofs ==
                    descr.jit_wb_if_flag_byteofs)
            assert descr.jit_wb_cards_set_singlebyte == -0x80
            card_marking = 1
            mask |= -0x80

        loc_base = arglocs[0]
        assert loc_base.is_core_reg()
        assert not is_frame or loc_base is r.jfp

        scratch_reg = r.x31
        mc.LBU(scratch_reg.value, loc_base.value, descr.jit_wb_if_flag_byteofs)
        mc.ANDI(scratch_reg.value, scratch_reg.value, mask & 0xff)

        # Patch Location: BEQZ scratch_reg, end
        jz_location = mc.get_relative_pos()
        mc.EBREAK()

        # For `cond_call_gc_wb_array`, also add another fast path:
        # If `GCFLAG_CARDS_SET`, then we can just update the card table (set
        # one bit) and done.
        js_location = 0
        if card_marking:
            # GCFLAG_CARDS_SET is in this byte at 0x80
            mc.ANDI(scratch_reg.value, scratch_reg.value, 0x80)

            # Patch Location: BNEZ scratch_reg, update_card_table
            js_location = mc.get_relative_pos()
            mc.EBREAK()

        # Write only a CALL to the helper prepared in advance, passing it as
        # argument the address of the structure we are writing into
        # (the first argument to COND_CALL_GC_WB).
        helper_num = card_marking
        if is_frame:
            helper_num = 4
        elif self._regalloc is not None and self._regalloc.fprm.reg_bindings:
            helper_num += 2  # Slowpath must spill float registers

        if self.wb_slowpath[helper_num] == 0:  # Tests only
            assert not we_are_translated()
            self.cpu.gc_ll_descr.write_barrier_descr = descr
            self._build_wb_slowpath(card_marking,
                                    bool(self._regalloc.fprm.reg_bindings))
            assert self.wb_slowpath[helper_num] != 0

        # Save `r.x10` to stack.
        stack_size = 0
        if loc_base is not r.x10:
            stack_size = ((XLEN * 1) + ABI_STACK_ALIGN - 1) // \
                    ABI_STACK_ALIGN * ABI_STACK_ALIGN
            mc.ADDI(r.sp.value, r.sp.value, -stack_size)
            mc.store_int(r.x10.value, r.sp.value, 0)
            mc.MV(r.x10.value, loc_base.value)
            if is_frame:
                assert loc_base is r.jfp

        # Call the slow path of the write barrier.
        mc.load_int_imm(r.ra.value, self.wb_slowpath[helper_num])
        mc.JALR(r.ra.value, r.ra.value, 0)

        # Restore `r.x10` from stack.
        if loc_base is not r.x10:
            mc.load_int(r.x10.value, r.sp.value, 0)
            mc.ADDI(r.sp.value, r.sp.value, stack_size)

        jns_location = 0
        if card_marking:
            # The helper ends again with a check of the flag in the object.

            # After the `wb_slowpath`, we check `GCFLAG_CARDS_SET` again.  If
            # `GCFLAG_CARDS_SET` isn't set, it implies that the object doesn't
            # have a card table (e.g. small array) and we can skip to the end.

            # Patch Location: BEQZ x31, end_update_card_table
            jns_location = mc.get_relative_pos()
            mc.EBREAK()

            # LABEL[update_card_table]:

            # Patch the `js_location` above.
            offset = mc.get_relative_pos() - js_location
            pmc = OverwritingBuilder(mc, js_location, INST_SIZE)
            pmc.BNEZ(scratch_reg.value, offset)

            # Update the card table if `GCFLAG_CARDS_SET` is set.
            loc_index = arglocs[1]
            assert loc_index.is_core_reg()

            # Allocate scratch registers.
            scratch2_reg = r.ra
            scratch3_reg = tmplocs[0]

            # byte_index:
            # scratch_reg = ~(index >> (descr.jit_wb_card_page_shift + lg2(8)))
            mc.SRLI(scratch_reg.value, loc_index.value,
                    descr.jit_wb_card_page_shift + 3)
            mc.XORI(scratch_reg.value, scratch_reg.value, -1)

            # byte_addr:
            mc.ADD(scratch_reg.value, loc_base.value, scratch_reg.value)

            # bit_index:
            # scratch2_reg = (index >> descr.jit_wb_card_page_shift) & 0x7
            mc.SRLI(scratch2_reg.value, loc_index.value,
                    descr.jit_wb_card_page_shift)
            mc.ANDI(scratch2_reg.value, scratch2_reg.value, 0x07)

            # bit_mask:
            # scratch2_reg = (1 << scratch2_reg)
            mc.load_int_imm(scratch3_reg.value, 1)
            mc.SLL(scratch2_reg.value, scratch3_reg.value, scratch2_reg.value)

            # Set the bit
            mc.LBU(scratch3_reg.value, scratch_reg.value, 0)
            mc.OR(scratch3_reg.value, scratch3_reg.value, scratch2_reg.value)
            mc.SB(scratch3_reg.value, scratch_reg.value, 0)

            # LABEL[end_update_card_table]:

            # Patch the `jns_location` above.
            offset = mc.get_relative_pos() - jns_location
            pmc = OverwritingBuilder(mc, jns_location, INST_SIZE)
            pmc.BEQZ(r.x31.value, offset)

        # LABEL[end]:

        # Patch `jz_location` above.
        offset = mc.get_relative_pos() - jz_location
        pmc = OverwritingBuilder(mc, jz_location, INST_SIZE)
        pmc.BEQZ(scratch_reg.value, offset)

    def emit_op_cond_call_gc_wb(self, op, arglocs):
        tmplocs = arglocs[:1]
        arglocs = arglocs[1:]
        self._write_barrier_fastpath(self.mc, op.getdescr(), arglocs, tmplocs)

    def emit_op_cond_call_gc_wb_array(self, op, arglocs):
        tmplocs = arglocs[:1]
        arglocs = arglocs[1:]
        self._write_barrier_fastpath(self.mc, op.getdescr(), arglocs, tmplocs,
                                     array=True)

    def _store_force_index(self, guard_op):
        faildescr = guard_op.getdescr()
        faildescrindex = self.get_gcref_from_faildescr(faildescr)
        ofs = self.cpu.get_ofs_of_frame_field('jf_force_descr')
        scratch_reg = r.x31
        self.load_from_gc_table(scratch_reg.value, faildescrindex)
        self.mc.store_int(scratch_reg.value, r.jfp.value, ofs)

    def _find_nearby_operation(self, delta):
        regalloc = self._regalloc
        return regalloc.operations[regalloc.rm.position + delta]

    def emit_guard_op_guard_not_forced(self, call_op, guard_op, arglocs,
                                       num_arglocs):
        # arglocs is call_op_arglocs + guard_op_arglocs, split them
        if rop.is_call_assembler(call_op.getopnum()):
            if num_arglocs == 3:
                [argloc, vloc, result_loc] = arglocs[:3]
            else:
                [argloc, result_loc] = arglocs[:2]
                vloc = self.imm(0)
            guard_op_arglocs = arglocs[num_arglocs:]
            self._store_force_index(guard_op)
            # Note: In the `call_assembler` implementation:
            #
            # `tmploc` refers to the register holding the returned JITFrame
            # address, which is `r.x10` in RISC-V.
            #
            # `result_loc` refers to the register allocated for the returned
            # value of the `call_assembler` op. For now, it is the returned by
            # `after_call`, which returns `r.x10` for integers and `r.f10` for
            # floats.
            self.call_assembler(call_op, argloc, vloc, result_loc,
                                tmploc=r.x10)
        else:
            assert num_arglocs == call_op.numargs() + 3
            call_op_arglocs = arglocs[0:num_arglocs]
            guard_op_arglocs = arglocs[num_arglocs:]
            self._store_force_index(guard_op)
            self._emit_op_call(call_op, call_op_arglocs)

        # Implement guard_not_forced:
        #
        #     if frame.jf_descr != 0:
        #         goto guard_handler
        #
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        scratch_reg = r.x31
        self.mc.load_int(scratch_reg.value, r.jfp.value, ofs)
        self.mc.BEQZ(scratch_reg.value, 8)
        self._emit_pending_guard(guard_op, guard_op_arglocs)

    def simple_call(self, fnloc, arglocs, result_loc=r.x10):
        if result_loc is None:
            result_type = VOID
            result_size = 0
        elif result_loc.is_fp_reg():
            result_type = FLOAT
            result_size = FLEN
        else:
            result_type = INT
            result_size = XLEN
        cb = RISCVCallBuilder(self, fnloc, arglocs, result_loc, result_type,
                              result_size)
        cb.emit()

    # Note: Read the `call_assembler` function in
    # `rpython/jit/backend/llsupport/assembler.py` to understand how these
    # `_call_assembler_*` functions work.

    def _call_assembler_emit_call(self, addr, argloc, tmploc):
        # Move the threadlocal to r.x11.
        self.mc.load_int(r.x11.value, r.sp.value, self.saved_threadlocal_addr)

        assert argloc is r.x10
        assert tmploc is r.x10
        self.simple_call(addr, [argloc, r.x11], result_loc=tmploc)

    def _call_assembler_check_descr(self, expected_descr, tmploc):
        scratch_reg = r.x31

        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        self.mc.load_int(scratch_reg.value, tmploc.value, ofs)

        if check_imm_arg(-expected_descr):
            self.mc.ADDI(scratch_reg.value, scratch_reg.value, -expected_descr)
        else:
            scratch2_reg = r.ra
            self.mc.load_int_imm(scratch2_reg.value, expected_descr)
            self.mc.SUB(scratch_reg.value, scratch_reg.value,
                        scratch2_reg.value)

        # Patch Location: BEQZ x31, load_result_fast_path
        pos = self.mc.get_relative_pos()
        self.mc.EBREAK()
        return pos

    def _call_assembler_emit_helper_call(self, addr, arglocs, resloc):
        self.simple_call(addr, arglocs, result_loc=resloc)

    def _call_assembler_patch_je(self, result_loc, jmp_location):
        # Patch Location: J end
        pos = self.mc.get_relative_pos()
        self.mc.EBREAK()

        # LABEL[load_result_fast_path]:

        # Patch the check_descr patch location.
        currpos = self.mc.get_relative_pos()
        pmc = OverwritingBuilder(self.mc, jmp_location, INST_SIZE)
        pmc.BEQZ(r.x31.value, currpos - jmp_location)

        return pos

    def _call_assembler_load_result(self, op, result_loc):
        # LABEL[load_result_fast_path]:
        if op.type != 'v':
            # Load the return value from the returned frame.

            kind = op.type
            descr = self.cpu.getarraydescr_for_frame(kind)
            ofs = self.cpu.unpack_arraydescr(descr)
            # Note: The code above should be equivalent to
            # `ofs = self.cpu.get_baseofs_of_frame_field()` used in
            # `OP_FINISH`.

            if kind == FLOAT:
                assert result_loc.is_fp_reg()
                self.mc.load_float(result_loc.value, r.x10.value, ofs)
            else:
                assert result_loc.is_core_reg()
                self.mc.load_int(result_loc.value, r.x10.value, ofs)

    def _call_assembler_patch_jmp(self, jmp_location):
        # LABEL[end]:
        currpos = self.mc.get_relative_pos()
        pmc = OverwritingBuilder(self.mc, jmp_location, INST_SIZE)
        pmc.J(currpos - jmp_location)

    def emit_op_guard_not_forced_2(self, op, arglocs):
        frame_depth = arglocs[0].value
        fail_locs = arglocs[1:]
        pos = self.mc.get_relative_pos()
        guardtok = self._build_guard_token(op, frame_depth, fail_locs, pos)
        self._finish_gcmap = guardtok.gcmap
        self._store_force_index(op)
        self.store_info_on_descr(pos, guardtok)

    def emit_op_force_token(self, op, arglocs):
        self.mc.MV(arglocs[0].value, r.jfp.value)

    def emit_op_load_from_gc_table(self, op, arglocs):
        res = arglocs[0]
        index = op.getarg(0).getint()
        self.load_from_gc_table(res.value, index)

    def emit_op_zero_array(self, op, arglocs):
        # ZERO_ARRAY(base, start, size, scale_start, scale_size)
        #
        # Assume `base` is a byte pointer. Initialize
        # `base + (start * scale_start)` to
        # `base + (start * scale_start) + (size * scale_size)` with zeros.

        assert len(arglocs) == 0, 'regalloc should not alloc for OP_ZERO_ARRAY'
        boxes = op.getarglist()
        base, start, size, scale_start, scale_size = boxes

        # The scaling arguments should always be `ConstInt(1)` on RISC-V.
        assert isinstance(scale_start, ConstInt) and scale_start.getint() == 1
        assert isinstance(scale_size, ConstInt) and scale_size.getint() == 1

        # Trivial case: size == 0, no code needed.
        if isinstance(size, ConstInt) and size.getint() == 0:
            return

        item_size, base_ofs, _ = unpack_arraydescr(op.getdescr())

        base_loc = self._regalloc.rm.make_sure_var_in_reg(base, boxes)

        if isinstance(start, ConstInt):
            start_loc = None
            const_start = start.getint()
            assert const_start >= 0
        else:
            start_loc = self._regalloc.rm.make_sure_var_in_reg(start, boxes)
            const_start = -1

        # `base_loc` and `start_loc` are in two regs here (or start_loc is an
        # immediate).  Compute the `dstaddr_loc`, which is the raw address that
        # we will pass as first argument to `memset()`.
        dstaddr_loc = r.x31  # scratch_reg
        if const_start >= 0:
            ofs = base_ofs + const_start
            reg = base_loc
        else:
            self.mc.ADD(dstaddr_loc.value, base_loc.value, start_loc.value)
            ofs = base_ofs
            reg = dstaddr_loc

        if check_imm_arg(ofs):
            self.mc.ADDI(dstaddr_loc.value, reg.value, ofs)
        else:
            scratch2_reg = r.ra
            self.mc.load_int_imm(scratch2_reg.value, ofs)
            self.mc.ADD(dstaddr_loc.value, reg.value, scratch2_reg.value)

        # Use SB, SH, SW or SD based on whether the array item size is a
        # multiple of 1, 2, 4, or 8.
        if   item_size & 1: item_size = 1
        elif item_size & 2: item_size = 2
        elif item_size & 4: item_size = 4
        else:               item_size = XLEN

        pre_align = 0
        single_store_size = item_size
        if item_size < XLEN and const_start >= 0:
            # Optimize SB/SH/SW into SW/SD.
            #
            # Assume that all arrays are naturally aligned to `XLEN` bytes, we
            # can increase the `item_size` to `XLEN` if (1) `start` is a
            # constant and (2) we emit pre-alignment zero initialization.
            pre_align = (-(const_start + base_ofs)) & (XLEN - 1)
            single_store_size = XLEN

        # Inline limitation: An estimation on the number of instructions to be
        # emited to zero-initialize the array.
        #
        # RISC-V GCC `__builtin_memset(ptr, 0, n)` inlines up to 15
        # instructions. We decrease it by 5 if `pre_align` is not zero becuase
        # we need more pre/post-alignment store instructions.
        inline_limit = (15 if pre_align == 0 else 10) * single_store_size

        if isinstance(size, ConstInt) and size.getint() <= inline_limit:
            # Implement zero_array with a series of store instructions,
            # starting at 'dstaddr_loc'.

            # Note: In RISC-V, misaligned exception will only be raised when
            # the effective address (`reg[base] + imm`) is not aligned, thus we
            # don't have to insert `ADDI` to align `dstaddr` or `dst_i`.

            total_size = size.getint()

            # Pre-alignment zero initialization
            dst_i = 0
            if pre_align > 0:
                pre_align = min(pre_align, total_size)
                if pre_align & 1:
                    self.mc.SB(r.x0.value, dstaddr_loc.value, dst_i)
                    dst_i += 1
                if pre_align & 2:
                    self.mc.SH(r.x0.value, dstaddr_loc.value, dst_i)
                    dst_i += 2
                if pre_align & 4:
                    self.mc.SW(r.x0.value, dstaddr_loc.value, dst_i)
                    dst_i += 4
                total_size -= pre_align

            # Zero initialization
            if single_store_size == 8:
                emit_store_inst = AbstractRISCVBuilder.SD
            elif single_store_size == 4:
                emit_store_inst = AbstractRISCVBuilder.SW
            elif single_store_size == 2:
                emit_store_inst = AbstractRISCVBuilder.SH
            else:
                emit_store_inst = AbstractRISCVBuilder.SB

            while total_size >= single_store_size:
                emit_store_inst(self.mc, r.x0.value, dstaddr_loc.value, dst_i)
                dst_i += single_store_size
                total_size -= single_store_size

            # Post-alignment zero initialization
            post_align = total_size
            if post_align & 4:
                self.mc.SW(r.x0.value, dstaddr_loc.value, dst_i)
                dst_i += 4
            if post_align & 2:
                self.mc.SH(r.x0.value, dstaddr_loc.value, dst_i)
                dst_i += 2
            if post_align & 1:
                self.mc.SB(r.x0.value, dstaddr_loc.value, dst_i)
                dst_i += 1
        else:
            if isinstance(size, ConstInt):
                size_loc = self.imm(size.getint())
            else:
                size_loc = self._regalloc.rm.make_sure_var_in_reg(size, boxes)

            # Call `memset(dstaddr, 0, size)`
            malloc_func_adr = self.imm(self.memset_addr)
            malloc_arglocs = [dstaddr_loc, self.imm(0), size_loc]
            self._regalloc.before_call()
            cb = RISCVCallBuilder(self, malloc_func_adr, malloc_arglocs,
                                  resloc=None, restype=VOID, ressize=0)
            cb.emit_no_collect()

    def emit_op_enter_portal_frame(self, op, arglocs):
        self.enter_portal_frame(op)

    def emit_op_leave_portal_frame(self, op, arglocs):
        self.leave_portal_frame(op)

    def emit_op_keepalive(self, op, arglocs):
        pass

    def emit_op_jit_debug(self, op, arglocs):
        pass

    def emit_op_increment_debug_counter(self, op, arglocs):
        base_loc = arglocs[0]
        scratch_reg = r.x31
        self.mc.load_int(scratch_reg.value, base_loc.value, 0)
        self.mc.ADDI(scratch_reg.value, scratch_reg.value, 1)
        self.mc.store_int(scratch_reg.value, base_loc.value, 0)

    def emit_op_label(self, op, arglocs):
        pass

    def emit_op_jump(self, op, arglocs):
        target_token = op.getdescr()
        assert isinstance(target_token, TargetToken)
        target = target_token._ll_loop_code
        if target_token in self.target_tokens_currently_compiling:
            relative_offset = target - self.mc.get_relative_pos()
            assert check_simm21_arg(relative_offset)
            self.mc.J(relative_offset)
        else:
            # Jump to the destination (absolute address).
            scratch_reg = r.x31
            self.mc.load_int_imm(scratch_reg.value, target)
            self.mc.JR(scratch_reg.value)

    def emit_op_finish(self, op, arglocs):
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if len(arglocs) > 0:
            [return_val] = arglocs
            if return_val.is_fp_reg():
                self.mc.store_float(return_val.value, r.jfp.value, base_ofs)
            else:
                self.mc.store_int(return_val.value, r.jfp.value, base_ofs)

        # Store `op.getdescr()` to `jf_descr`.
        faildescrindex = self.get_gcref_from_faildescr(op.getdescr())
        self.store_jf_descr(faildescrindex)

        # Update `jf_gcmap`.
        if op.numargs() > 0 and op.getarg(0).type == REF:
            if self._finish_gcmap:
                # We're returning with a `op_guard_not_forced_2`. We need to
                # say that frame slot 0 (stored above) contains a reference
                # too.
                self._finish_gcmap[0] |= r_uint(1) << 0
                gcmap = self._finish_gcmap
            else:
                gcmap = self.gcmap_for_finish
            self.push_gcmap(self.mc, gcmap)
        elif self._finish_gcmap:
            # We're returning with a `op_guard_not_forced_2`.
            gcmap = self._finish_gcmap
            self.push_gcmap(self.mc, gcmap)
        else:
            # Note that 0 here is redundant, but I would rather keep that one
            # and kill all the others.
            ofs = self.cpu.get_ofs_of_frame_field('jf_gcmap')
            self.mc.store_int(r.x0.value, r.jfp.value, ofs)

        self._call_footer(self.mc)


def not_implemented_op(self, op, arglocs):
    llop.debug_print(lltype.Void,
                     '[riscv/asm] %s not implemented' % op.getopname())
    raise NotImplementedError(op)

def not_implemented_comp_op(self, op, arglocs):
    llop.debug_print(lltype.Void,
                     '[riscv/asm] %s not implemented' % op.getopname())
    raise NotImplementedError(op)

def not_implemented_guard_op(self, op, guard_op, arglocs, guard_branch_inst):
    llop.debug_print(lltype.Void,
                     '[riscv/asm] %s not implemented' % op.getopname())
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

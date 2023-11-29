#!/usr/bin/env python

from rpython.jit.backend.llsupport.assembler import BaseAssembler, GuardToken
from rpython.jit.backend.llsupport.descr import CallDescr
from rpython.jit.backend.llsupport.gcmap import allocate_gcmap
from rpython.jit.backend.riscv import registers as r
from rpython.jit.backend.riscv.arch import INST_SIZE, JITFRAME_FIXED_SIZE, XLEN
from rpython.jit.backend.riscv.callbuilder import RISCVCallBuilder
from rpython.jit.backend.riscv.codebuilder import (
    BRANCH_BUILDER, OverwritingBuilder)
from rpython.jit.backend.riscv.instruction_util import (
    COND_INVALID, check_simm21_arg)
from rpython.jit.backend.riscv.rounding_modes import DYN, RTZ
from rpython.jit.metainterp.history import AbstractFailDescr, TargetToken
from rpython.jit.metainterp.resoperation import rop
from rpython.rtyper.lltypesystem import lltype, rffi


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

    emit_comp_op_int_eq = emit_op_int_eq

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

    emit_comp_op_int_ne = emit_op_int_ne

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

    def _build_guard_token(self, op, frame_depth, arglocs, offset):
        descr = op.getdescr()
        assert isinstance(descr, AbstractFailDescr)

        gcmap = allocate_gcmap(self, frame_depth, JITFRAME_FIXED_SIZE)
        faildescrindex = self.get_gcref_from_faildescr(descr)
        return GuardToken(self.cpu, gcmap, descr,
                          failargs=op.getfailargs(), fail_locs=arglocs,
                          guard_opnum=op.getopnum(), frame_depth=frame_depth,
                          faildescrindex=faildescrindex)

    def _emit_pending_guard(self, op, arglocs):
        pos = self.mc.get_relative_pos()
        guardtok = self._build_guard_token(op, arglocs[0].value, arglocs[1:],
                                           pos)
        guardtok.offset = pos
        self.pending_guards.append(guardtok)
        if guardtok.guard_not_invalidated():
            self.mc.NOP()
        else:
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

    def emit_op_guard_no_exception(self, op, arglocs):
        # TODO: Implement guard_no_exception properly.
        pass

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
        callee_func_addr_reg = r.x31
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
            self.mc.MV(res_loc.value, r.x31.value)

        self.pop_gcmap(self.mc)

        # Overwrite the conditional branch offset.
        branch_dest_addr = self.mc.get_relative_pos()
        branch_offset = branch_dest_addr - cond_branch_addr
        pmc = OverwritingBuilder(self.mc, cond_branch_addr, INST_SIZE)
        if res_loc is None:
            pmc.BEQZ(arglocs[0].value, branch_offset)
        else:
            pmc.BNEZ(arglocs[0].value, branch_offset)

    emit_op_cond_call = _emit_op_cond_call
    emit_op_cond_call_value_i = _emit_op_cond_call
    emit_op_cond_call_value_r = _emit_op_cond_call

    def emit_guard_op_cond_call(self, cond_op, op, arglocs, guard_branch_inst):
        # TODO: Optimize guard_branch_inst when cond_op is using integer
        # comparison.
        assert guard_branch_inst == COND_INVALID

        self._emit_op_cond_call(op, arglocs)

    def emit_op_load_from_gc_table(self, op, arglocs):
        res = arglocs[0]
        index = op.getarg(0).getint()
        self.load_from_gc_table(res.value, index)

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

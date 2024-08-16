#!/usr/bin/env python

from rpython.jit.backend.llsupport import jitframe, rewrite
from rpython.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from rpython.jit.backend.llsupport.descr import ArrayDescr
from rpython.jit.backend.model import CompiledLoopToken
from rpython.jit.backend.riscv import registers as r
from rpython.jit.backend.riscv.arch import (
    ABI_STACK_ALIGN, FLEN, INST_SIZE, JITFRAME_FIXED_SIZE,
    SCRATCH_STACK_SLOT_SIZE, XLEN)
from rpython.jit.backend.riscv.codebuilder import (
    InstrBuilder, MAX_NUM_INSTS_FOR_LOAD_INT_IMM, OverwritingBuilder)
from rpython.jit.backend.riscv.instruction_util import (
    can_fuse_into_compare_and_branch, check_imm_arg, check_simm21_arg)
from rpython.jit.backend.riscv.opassembler import (
    OpAssembler, asm_guard_operations, asm_operations)
from rpython.jit.backend.riscv.regalloc import (
    Regalloc, regalloc_guard_operations, regalloc_operations)
from rpython.jit.backend.riscv.locations import (
    ImmLocation, StackLocation, get_fp_offset)
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.history import AbstractFailDescr, FLOAT
from rpython.jit.metainterp.resoperation import rop
from rpython.rlib import rgc, rmmap
from rpython.rlib.debug import debug_print, debug_start, debug_stop
from rpython.rlib.jit import AsmInfo
from rpython.rlib.objectmodel import compute_unique_id, we_are_translated
from rpython.rlib.rarithmetic import r_uint
from rpython.rlib.rjitlog import rjitlog as jl
from rpython.rtyper.annlowlevel import cast_instance_to_gcref
from rpython.rtyper.lltypesystem import lltype, rffi


# Maximum size for an absolute branch stub (load addr + jalr).
_REDIRECT_BRANCH_STUB_SIZE = (MAX_NUM_INSTS_FOR_LOAD_INT_IMM + 1) * INST_SIZE

def _emit_nop_until_larger(mc, start, end):
    for i in range(start, end, INST_SIZE):
        mc.NOP()

class AssemblerRISCV(OpAssembler):
    def __init__(self, cpu, translate_support_code=False):
        OpAssembler.__init__(self, cpu, translate_support_code)
        self.failure_recovery_code = [0, 0, 0, 0]
        self.propagate_exception_path = 0
        self.wb_slowpath = [0, 0, 0, 0, 0]
        self.stack_check_slowpath = 0
        self._frame_realloc_slowpath = 0

    @rgc.no_release_gil
    def assemble_loop(self, jd_id, unique_id, logger, loopname, inputargs,
                      operations, looptoken, log):
        rmmap.enter_assembler_writing()
        try:
            return self._assemble_loop(jd_id, unique_id, logger, loopname,
                                       inputargs, operations, looptoken, log)
        finally:
            rmmap.leave_assembler_writing()

    def _assemble_loop(self, jd_id, unique_id, logger, loopname, inputargs,
                       operations, looptoken, log):
        if not we_are_translated():
            # Arguments should be unique
            assert len(set(inputargs)) == len(inputargs)

        clt = CompiledLoopToken(self.cpu, looptoken.number)
        clt._debug_nbargs = len(inputargs)
        looptoken.compiled_loop_token = clt

        self.setup(looptoken)
        if self.cpu.HAS_CODEMAP:
            self.codemap_builder.enter_portal_frame(jd_id, unique_id,
                                                    self.mc.get_relative_pos())

        frame_info = self.datablockwrapper.malloc_aligned(
            jitframe.JITFRAMEINFO_SIZE, alignment=XLEN)
        clt.frame_info = rffi.cast(jitframe.JITFRAMEINFOPTR, frame_info)
        clt.frame_info.clear()

        if log:
            operations = self._inject_debugging_code(looptoken, operations,
                                                     'e', looptoken.number)

        regalloc = Regalloc(self)
        allgcrefs = []
        operations = regalloc.prepare_loop(inputargs, operations, looptoken,
                                           allgcrefs)
        self.reserve_gcref_table(allgcrefs)
        function_pos = self.mc.get_relative_pos()

        self._call_header_with_stack_check()

        loop_head = self.mc.get_relative_pos()
        looptoken._ll_loop_code = loop_head

        frame_depth_no_fixed_size = self._assemble(regalloc, inputargs,
                                                   operations)
        frame_depth = frame_depth_no_fixed_size + JITFRAME_FIXED_SIZE
        self.update_frame_depth(frame_depth)
        self.patch_frame_depth_checks(frame_depth)

        # Generate extra NOPs if the size is too small. We need this because
        # `redirect_call_assembler` may want to patch the beginning with a far
        # branch to another loop or bridge.
        _emit_nop_until_larger(self.mc, self.mc.get_relative_pos(),
                               function_pos + _REDIRECT_BRANCH_STUB_SIZE)

        size_excluding_failure_stuff = self.mc.get_relative_pos()

        self.write_pending_failure_recoveries()

        const_pos = self.mc.get_relative_pos()
        self.mc.emit_pending_constants()

        full_size = self.mc.get_relative_pos()
        rawstart = self.materialize_loop(looptoken)
        looptoken._ll_function_addr = rawstart + function_pos

        self.patch_gcref_table(looptoken, rawstart)
        self.process_pending_guards(rawstart)
        self.fixup_target_tokens(rawstart)

        if log and not we_are_translated():
            self.mc._dump_trace(rawstart, 'loop.asm')

        ops_offset = self.mc.ops_offset

        if logger:
            log = logger.log_trace(jl.MARK_TRACE_ASM, None, self.mc)
            log.write(inputargs, operations, ops_offset=ops_offset)

            if logger.logger_ops:
                logger.logger_ops.log_loop(inputargs, operations, 0,
                                           'rewritten', name=loopname,
                                           ops_offset=ops_offset)

        debug_start('jit-backend-addr')
        debug_print('Loop %d (%s) has address 0x%x to 0x%x (bootstrap 0x%x)' % (
            looptoken.number, loopname,
            r_uint(rawstart + loop_head),
            r_uint(rawstart + size_excluding_failure_stuff),
            r_uint(rawstart + function_pos)))
        debug_print('       gc table: 0x%x' % r_uint(rawstart))
        debug_print('       function: 0x%x' % r_uint(rawstart + function_pos))
        debug_print('         resops: 0x%x' % r_uint(rawstart + loop_head))
        debug_print('       failures: 0x%x' % r_uint(rawstart +
                                                 size_excluding_failure_stuff))
        debug_print("     const pool: 0x%x" % r_uint(rawstart + const_pos))
        debug_print('            end: 0x%x' % r_uint(rawstart + full_size))
        debug_stop('jit-backend-addr')

        self.teardown()

        return AsmInfo(ops_offset, rawstart + loop_head,
                       size_excluding_failure_stuff - loop_head)

    @rgc.no_release_gil
    def assemble_bridge(self, logger, faildescr, inputargs, operations,
                        original_loop_token, log):
        rmmap.enter_assembler_writing()
        try:
            return self._assemble_bridge(logger, faildescr, inputargs,
                                         operations, original_loop_token, log)
        finally:
            rmmap.leave_assembler_writing()

    def _assemble_bridge(self, logger, faildescr, inputargs, operations,
                         original_loop_token, log):
        if not we_are_translated():
            # Arguments should be unique
            assert len(set(inputargs)) == len(inputargs)

        self.setup(original_loop_token)
        if self.cpu.HAS_CODEMAP:
            self.codemap_builder.inherit_code_from_position(
                faildescr.adr_jump_offset)

        descr_number = compute_unique_id(faildescr)
        if log:
            operations = self._inject_debugging_code(faildescr, operations,
                                                     'b', descr_number)

        assert isinstance(faildescr, AbstractFailDescr)

        arglocs = self.rebuild_faillocs_from_descr(faildescr, inputargs)

        regalloc = Regalloc(self)
        allgcrefs = []
        operations = regalloc.prepare_bridge(inputargs, arglocs, operations,
                                             allgcrefs,
                                             self.current_clt.frame_info)
        self.reserve_gcref_table(allgcrefs)
        start_pos = self.mc.get_relative_pos()

        self._check_frame_depth(self.mc, regalloc.get_gcmap(),
                                expected_size=-1)

        bridge_start_pos = self.mc.get_relative_pos()
        frame_depth_no_fixed_size = self._assemble(regalloc, inputargs,
                                                   operations)

        # Patch frame depth check.
        bridge_frame_depth = frame_depth_no_fixed_size + JITFRAME_FIXED_SIZE
        self.patch_frame_depth_checks(bridge_frame_depth)

        # Generate extra NOPs if the size is too small. We need this because
        # `redirect_call_assembler` may want to patch the beginning with a far
        # branch to another loop or bridge.
        _emit_nop_until_larger(self.mc, self.mc.get_relative_pos(),
                               start_pos + _REDIRECT_BRANCH_STUB_SIZE)

        code_end_pos = self.mc.get_relative_pos()

        self.write_pending_failure_recoveries()

        const_pos = self.mc.get_relative_pos()
        self.mc.emit_pending_constants()

        fullsize = self.mc.get_relative_pos()
        rawstart = self.materialize_loop(original_loop_token)

        self.patch_gcref_table(original_loop_token, rawstart)
        self.process_pending_guards(rawstart)

        # Update the frame depth in compiled_loop_token.
        frame_depth = max(self.current_clt.frame_info.jfi_frame_depth,
                          bridge_frame_depth)
        self.update_frame_depth(frame_depth)

        # Replace _ll_loop_code relative offset with an absolute address.
        self.fixup_target_tokens(rawstart)

        # Patch the jump from original guard.
        self.patch_trace(faildescr, original_loop_token, rawstart + start_pos,
                         regalloc)

        if log and not we_are_translated():
            self.mc._dump_trace(rawstart, 'bridge.asm')

        ops_offset = self.mc.ops_offset

        if logger:
            log = logger.log_trace(jl.MARK_TRACE_ASM, None, self.mc)
            log.write(inputargs, operations, ops_offset)
            # Log that the already written bridge is stitched to a descr.
            logger.log_patch_guard(descr_number, rawstart)

            # Legacy
            if logger.logger_ops:
                logger.logger_ops.log_bridge(inputargs, operations,
                                             'rewritten', faildescr,
                                             ops_offset=ops_offset)

        debug_start("jit-backend-addr")
        debug_print("bridge out of Guard 0x%x has address 0x%x to 0x%x" %
                    (r_uint(descr_number), r_uint(rawstart + start_pos),
                        r_uint(rawstart + code_end_pos)))
        debug_print("       gc table: 0x%x" % r_uint(rawstart))
        debug_print("    jump target: 0x%x" % r_uint(rawstart + start_pos))
        debug_print("         resops: 0x%x" % r_uint(rawstart +
                                                     bridge_start_pos))
        debug_print("       failures: 0x%x" % r_uint(rawstart + code_end_pos))
        debug_print("     const pool: 0x%x" % r_uint(rawstart + const_pos))
        debug_print("            end: 0x%x" % r_uint(rawstart + fullsize))
        debug_stop("jit-backend-addr")

        self.teardown()

        return AsmInfo(ops_offset, start_pos + rawstart,
                       code_end_pos - start_pos)

    @rgc.no_release_gil
    def redirect_call_assembler(self, oldlooptoken, newlooptoken):
        rmmap.enter_assembler_writing()
        try:
            self._redirect_call_assembler(oldlooptoken, newlooptoken)
        finally:
            rmmap.leave_assembler_writing()

    def _redirect_call_assembler(self, oldlooptoken, newlooptoken):
        # Some minimal sanity checking
        old_nbargs = oldlooptoken.compiled_loop_token._debug_nbargs
        new_nbargs = newlooptoken.compiled_loop_token._debug_nbargs
        assert old_nbargs == new_nbargs

        # We overwrite the instructions at the old `_ll_function_addr` to start
        # with a jump to the new _ll_function_addr.
        oldadr = oldlooptoken._ll_function_addr
        target = newlooptoken._ll_function_addr

        # Copy frame info
        baseofs = self.cpu.get_baseofs_of_frame_field()
        newlooptoken.compiled_loop_token.update_frame_info(
            oldlooptoken.compiled_loop_token, baseofs)

        mc = InstrBuilder()
        scratch_reg = r.x31  # Pick a caller-saved reg excluding x10-17 & ra
        mc.load_int_imm(scratch_reg.value, target)
        mc.JALR(r.x0.value, scratch_reg.value, 0)
        mc.emit_pending_constants()
        mc.copy_to_raw_memory(oldadr)

        jl.redirect_assembler(oldlooptoken, newlooptoken, newlooptoken.number)

    def _assemble(self, regalloc, inputargs, operations):
        # Fill in the frame location hints so that we can reduce stack-to-stack
        # data movement in `remap_frame_layout_mixed`.
        regalloc.compute_hint_frame_locations(operations)

        # Visit all operations and regalloc/assemble the operations.
        self._walk_operations(inputargs, operations, regalloc)
        frame_depth = regalloc.get_final_frame_depth()

        # If the jump target (of the current loop) requires larger frame,
        # update the frame depth.
        jump_target_descr = regalloc.jump_target_descr
        if jump_target_descr is not None:
            tgt_depth = jump_target_descr._riscv_clt.frame_info.jfi_frame_depth
            target_frame_depth = tgt_depth - JITFRAME_FIXED_SIZE
            frame_depth = max(frame_depth, target_frame_depth)

        return frame_depth

    def _walk_operations(self, inputargs, operations, regalloc):
        self._regalloc = regalloc
        regalloc.operations = operations

        while regalloc.position() < len(operations) - 1:
            regalloc.next_instruction()
            i = regalloc.position()
            op = operations[i]
            self.mc.mark_op(op)
            opnum = op.getopnum()

            if rop.has_no_side_effect(opnum) and op not in regalloc.longevity:
                # If this op does not have side effects and its result is
                # unused, it is safe to ignore this op.
                pass
            elif not we_are_translated() and op.getopnum() == rop.FORCE_SPILL:
                regalloc.force_spill_var(op.getarg(0))
            elif (i < len(operations) - 1 and
                  ((can_fuse_into_compare_and_branch(opnum) and
                    regalloc.next_op_can_accept_cc(operations, i)) or
                   (op.is_ovf() and
                    rop.is_guard_overflow(operations[i + 1].getopnum())))):
                guard_op = operations[i + 1]  # guard_* or cond_call*
                guard_num = guard_op.getopnum()
                arglocs, guard_branch_inst = \
                        regalloc_guard_operations[guard_num](regalloc, op,
                                                             guard_op)
                if arglocs is not None:
                    asm_guard_operations[guard_num](self, op, guard_op, arglocs,
                                                    guard_branch_inst)
                regalloc.next_instruction()  # Advance one more
                # Free argument vars of the guard op (if no longer used).
                if guard_op.is_guard():
                    regalloc.possibly_free_vars(guard_op.getfailargs())
                regalloc.possibly_free_vars_for_op(guard_op)
                # Free the return var of the guard op (if no longer used).
                regalloc.possibly_free_var(guard_op)
            elif (rop.is_call_may_force(op.getopnum()) or
                  rop.is_call_release_gil(op.getopnum()) or
                  rop.is_call_assembler(op.getopnum())):
                guard_op = operations[i + 1]
                guard_num = guard_op.getopnum()
                assert guard_num in (rop.GUARD_NOT_FORCED,
                                     rop.GUARD_NOT_FORCED_2)

                # `arglocs` contains the locations for `op` and `guard_op`.
                # The first `num_arglocs` locations are for `op` and the
                # remainings are for `guard_op`.
                arglocs, num_arglocs = \
                        regalloc_guard_operations[guard_num](regalloc, op,
                                                             guard_op)
                if arglocs is not None:
                    asm_guard_operations[guard_num](self, op, guard_op, arglocs,
                                                    num_arglocs)
                regalloc.next_instruction()  # Advance one more

                # Free argument vars of the guard op (if no longer used).
                regalloc.possibly_free_vars(guard_op.getfailargs())
                regalloc.possibly_free_vars_for_op(guard_op)
            else:
                arglocs = regalloc_operations[opnum](regalloc, op)
                if arglocs is not None:
                    asm_operations[opnum](self, op, arglocs)

            # Free argument vars of the op (if no longer used).
            regalloc.possibly_free_vars_for_op(op)
            if rop.is_guard(opnum):
                regalloc.possibly_free_vars(op.getfailargs())

            # Free the return var of the op (if no longer used).
            #
            # Note: This can happen when we want the side-effect of an op (e.g.
            # `call_assembler_i` or `call_i`) but want to discard the returned
            # value.
            if op.type != 'v':
                regalloc.possibly_free_var(op)

            regalloc.free_temp_vars()
            regalloc._check_invariants()

        if not we_are_translated():
            self.mc.EBREAK()
        self.mc.mark_op(None)  # End of the loop
        regalloc.operations = None

    def _call_header_with_stack_check(self):
        self._call_header()

        if self.stack_check_slowpath == 0:
            pass  # No stack check (e.g. not translated)
        else:
            endaddr, lengthaddr, _ = self.cpu.insert_stack_check()

            # hi: endaddr
            #     stack pointer
            # lo: startaddr = endaddr - lengthaddr

            scratch_reg = r.x31
            scratch2_reg = r.x30

            # Load stack end
            self.mc.load_int_imm(scratch_reg.value, endaddr)
            self.mc.load_int(scratch_reg.value, scratch_reg.value, 0)

            # Load stack length
            self.mc.load_int_imm(scratch2_reg.value, lengthaddr)
            self.mc.load_int(scratch2_reg.value, scratch2_reg.value, 0)

            # Calculate stack_start = stack_end - stack_len
            self.mc.SUB(scratch_reg.value, scratch_reg.value,
                        scratch2_reg.value)

            # Patch Location: BGEU sp, stack_start, end
            pos = self.mc.get_relative_pos()
            self.mc.EBREAK()

            self.mc.load_int_imm(r.ra.value, self.stack_check_slowpath)
            self.mc.JALR(r.ra.value, r.ra.value, 0)

            # LABEL[end]:
            offset = self.mc.get_relative_pos() - pos
            pmc = OverwritingBuilder(self.mc, pos, INST_SIZE)
            pmc.BGEU(r.sp.value, scratch_reg.value, offset)

    def _call_header(self):
        self._push_callee_save_regs_to_stack(self.mc)

        if self.cpu.translate_support_code:
            self._call_header_vmprof()

        # Save the thread local address to tls[0].
        self.saved_threadlocal_addr = 0 * XLEN
        self.mc.store_int(r.x11.value, r.sp.value, 0 * XLEN)

        self.mc.MV(r.jfp.value, r.x10.value)

        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self.gen_shadowstack_header(gcrootmap)

    def _call_footer(self, mc):
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self.gen_shadowstack_footer(gcrootmap, mc)

        if self.cpu.translate_support_code:
            self._call_footer_vmprof(mc)

        mc.MV(r.x10.value, r.jfp.value)
        self._pop_callee_save_regs_from_stack(mc)
        mc.RET()

    def gen_shadowstack_header(self, gcrootmap):
        scratch_reg = r.x31
        scratch2_reg = r.x30
        scratch3_reg = r.x29

        # scratch_reg = &root_stack_top_addr (address to pointer to stack top)
        rst = gcrootmap.get_root_stack_top_addr()
        self.mc.load_int_imm(scratch_reg.value, rst)
        # scratch2_reg = root_stack_top_addr (address to stack top)
        self.mc.load_int(scratch2_reg.value, scratch_reg.value, 0)

        # We push two words, like the x86 backend does:
        # The '1' is to benefit from the shadowstack 'is_minor' optimization

        # scratch2_reg[0] = 1
        self.mc.load_int_imm(scratch3_reg.value, 1)
        self.mc.store_int(scratch3_reg.value, scratch2_reg.value, 0)
        # scratch2_reg[1] = r.jfp
        self.mc.store_int(r.jfp.value, scratch2_reg.value, XLEN)

        # scratch2_reg += 2 * XLEN
        self.mc.ADDI(scratch2_reg.value, scratch2_reg.value, 2 * XLEN)
        # root_stack_top_addr = scratch2_reg
        self.mc.store_int(scratch2_reg.value, scratch_reg.value, 0)

    def gen_shadowstack_footer(self, gcrootmap, mc):
        scratch_reg = r.x31
        scratch2_reg = r.x30

        # scratch_reg = &root_stack_top_addr
        rst = gcrootmap.get_root_stack_top_addr()
        mc.load_int_imm(scratch_reg.value, rst)
        # scratch2_reg = root_stack_top_addr
        mc.load_int(scratch2_reg.value, scratch_reg.value, 0)

        # scratch2_reg -= 2 * XLEN
        mc.ADDI(scratch2_reg.value, scratch2_reg.value, -(2 * XLEN))
        # root_stack_top_addr = scratch2_reg
        mc.store_int(scratch2_reg.value, scratch_reg.value, 0)

    def _call_header_vmprof(self):
        from rpython.rlib.rvmprof.rvmprof import cintf, VMPROF_JITTED_TAG

        # tloc = &pypy_threadlocal_s
        tloc = r.x11
        scratch_reg = r.x31
        scratch2_reg = r.x30

        # scratch_reg = &vmprof_tl_stack (old vmprof_tl_stack top)
        offset = rffi.cast(lltype.Signed, cintf.vmprof_tl_stack.getoffset())
        self.mc.load_int_from_base_plus_offset(scratch_reg.value, tloc.value,
                                               offset)
        # stack->next = old vmprof_tl_stack top
        self.mc.store_int(scratch_reg.value, r.sp.value, 1 * XLEN)
        # stack->value = sp
        self.mc.store_int(r.sp.value, r.sp.value, 2 * XLEN)
        # stack->kind = VMPROF_JITTED_TAG
        self.mc.load_int_imm(scratch_reg.value, VMPROF_JITTED_TAG)
        self.mc.store_int(scratch_reg.value, r.sp.value, 3 * XLEN)
        # Set vmprof_tl_stack top to the new entry.
        self.mc.ADDI(scratch_reg.value, r.sp.value, 1 * XLEN)
        self.mc.store_int_to_base_plus_offset(scratch_reg.value, tloc.value,
                                              offset, tmp=scratch2_reg.value)

    def _call_footer_vmprof(self, mc):
        from rpython.rlib.rvmprof.rvmprof import cintf

        tloc = r.x11
        scratch_reg = r.x31
        scratch2_reg = r.x30

        # tloc = &pypy_threadlocal_s
        mc.load_int(tloc.value, r.sp.value, 0 * XLEN)
        # scratch_reg = thread local vmprof_tl_stack->next
        mc.load_int(scratch_reg.value, r.sp.value, 1 * XLEN)
        # Set vmprof_tl_stack top to vmprof_tl_stack->next (pop stack)
        offset = rffi.cast(lltype.Signed, cintf.vmprof_tl_stack.getoffset())
        mc.store_int_to_base_plus_offset(scratch_reg.value, tloc.value,
                                         offset, tmp=scratch2_reg.value)

    def _calculate_callee_save_area_size(self):
        # Extra thread local storage.
        #
        # tls[0 * XLEN]: saved_threadlocal_addr (_call_header)
        # tls[1 * XLEN]: VMPROFSTACK->next  (vmprof)
        # tls[2 * XLEN]: VMPROFSTACK->value (vmprof)
        # tls[3 * XLEN]: VMPROFSTACK->kind  (vmprof)
        tls_size = XLEN * 4

        core_reg_begin = tls_size
        core_reg_size = XLEN * len(r.callee_saved_registers_except_ra_sp_fp)

        fp_reg_begin = core_reg_begin + core_reg_size
        fp_reg_begin = (fp_reg_begin + FLEN - 1) // FLEN * FLEN
        fp_reg_size = FLEN * len(r.callee_saved_fp_registers)

        # fp = old_sp
        # frame_record[0 * XLEN] (or fp[-2 * XLEN]): fp (old)
        # frame_record[1 * XLEN] (or fp[-1 * XLEN]): ra
        frame_record_begin = fp_reg_begin + fp_reg_size
        frame_record_begin = (frame_record_begin + XLEN - 1) // XLEN * XLEN
        frame_record_size = 2 * XLEN

        area_size = frame_record_begin + frame_record_size
        area_size = ((area_size + ABI_STACK_ALIGN - 1)
                         // ABI_STACK_ALIGN * ABI_STACK_ALIGN)

        frame_record_begin = area_size - frame_record_size

        return area_size, core_reg_begin, fp_reg_begin, frame_record_begin

    def _push_callee_save_regs_to_stack(self, mc):
        area_size, core_reg_begin, fp_reg_begin, frame_record_begin = \
                self._calculate_callee_save_area_size()

        # Subtract stack pointer
        mc.ADDI(r.sp.value, r.sp.value, -area_size)

        # Frame record
        mc.store_int(r.fp.value, r.sp.value, frame_record_begin)
        mc.store_int(r.ra.value, r.sp.value, frame_record_begin + XLEN)
        mc.ADDI(r.fp.value, r.sp.value, area_size)

        for i, reg in enumerate(r.callee_saved_registers_except_ra_sp_fp):
            mc.store_int(reg.value, r.sp.value, i * XLEN + core_reg_begin)
        for i, reg in enumerate(r.callee_saved_fp_registers):
            mc.store_float(reg.value, r.sp.value, i * FLEN + fp_reg_begin)

    def _pop_callee_save_regs_from_stack(self, mc):
        area_size, core_reg_begin, fp_reg_begin, frame_record_begin = \
                self._calculate_callee_save_area_size()
        for i, reg in enumerate(r.callee_saved_fp_registers):
            mc.load_float(reg.value, r.sp.value, i * FLEN + fp_reg_begin)
        for i, reg in enumerate(r.callee_saved_registers_except_ra_sp_fp):
            mc.load_int(reg.value, r.sp.value, i * XLEN + core_reg_begin)

        # Frame record
        mc.load_int(r.ra.value, r.sp.value, frame_record_begin + XLEN)
        mc.load_int(r.fp.value, r.sp.value, frame_record_begin)

        # Add (restore) stack pointer
        mc.ADDI(r.sp.value, r.sp.value, area_size)

    def _push_all_regs_to_jitframe(self, mc, ignored_regs, withfloats,
                                   callee_only=False):
        # Push general purpose registers
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if callee_only:
            regs = r.caller_saved_registers
        else:
            regs = r.registers_except_zero

        if not ignored_regs:
            for reg in regs:
                mc.store_int(reg.value, r.jfp.value,
                             base_ofs +
                             self.cpu.all_reg_indexes[reg.value] * XLEN)
        else:
            for reg in ignored_regs:
                assert reg.is_core_reg()
            for reg in regs:
                if reg in ignored_regs:
                    continue
                mc.store_int(reg.value, r.jfp.value,
                             base_ofs +
                             self.cpu.all_reg_indexes[reg.value] * XLEN)

        if withfloats:
            # Push floating point registers
            ofs = base_ofs + len(r.registers) * XLEN
            for reg in r.fp_registers:
                mc.store_float(reg.value, r.jfp.value, ofs + reg.value * FLEN)

    def _pop_all_regs_from_jitframe(self, mc, ignored_regs, withfloats,
                                    callee_only=False):
        # Pop general purpose registers
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        if callee_only:
            regs = r.caller_saved_registers
        else:
            regs = r.registers_except_zero

        if not ignored_regs:
            for reg in regs:
                mc.load_int(reg.value, r.jfp.value,
                            base_ofs +
                            self.cpu.all_reg_indexes[reg.value] * XLEN)
        else:
            for reg in ignored_regs:
                assert reg.is_core_reg()
            for reg in regs:
                if reg in ignored_regs:
                    continue
                mc.load_int(reg.value, r.jfp.value,
                            base_ofs +
                            self.cpu.all_reg_indexes[reg.value] * XLEN)

        if withfloats:
            # Pop floating point registers
            ofs = base_ofs + len(r.registers) * XLEN
            for reg in r.fp_registers:
                mc.load_float(reg.value, r.jfp.value, ofs + reg.value * FLEN)

    def _push_regs_to_jitframe(self, mc, selected_regs):
        # Push specified regs to JITFrame.
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        fp_ofs = base_ofs + len(r.registers) * XLEN
        for reg in selected_regs:
            if reg.is_core_reg():
                mc.store_int(reg.value, r.jfp.value,
                             base_ofs +
                             self.cpu.all_reg_indexes[reg.value] * XLEN)
            else:
                assert reg.is_fp_reg()
                mc.store_float(reg.value, r.jfp.value,
                               fp_ofs + reg.value * FLEN)

    def _pop_regs_from_jitframe(self, mc, selected_regs):
        # Pop specified regs from JITFrame.
        base_ofs = self.cpu.get_baseofs_of_frame_field()
        fp_ofs = base_ofs + len(r.registers) * XLEN
        for reg in selected_regs:
            if reg.is_core_reg():
                mc.load_int(reg.value, r.jfp.value,
                            base_ofs +
                            self.cpu.all_reg_indexes[reg.value] * XLEN)
            else:
                assert reg.is_fp_reg()
                mc.load_float(reg.value, r.jfp.value,
                              fp_ofs + reg.value * FLEN)

    def store_jf_descr(self, descrindex):
        scratch_reg = r.x31
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        self.load_from_gc_table(scratch_reg.value, descrindex)
        self.mc.store_int(scratch_reg.value, r.jfp.value, ofs)

    def push_gcmap(self, mc, gcmap, store=True):
        # Set gcmap address to jf_gcmap field.

        # rpython/jit/backend/llsupport/callbuilder.py passes a `store`
        # argument as keyword args. For RISC-V backend, we only support
        # `store=True` version.
        assert store

        scratch_reg = r.x31
        new_gcmap_adr = rffi.cast(lltype.Signed, gcmap)
        mc.load_int_imm(scratch_reg.value, new_gcmap_adr)

        ofs = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        mc.store_int(scratch_reg.value, r.jfp.value, ofs)

    def pop_gcmap(self, mc):
        # Clear gcmap address from jf_gcmap field.
        ofs = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        mc.store_int(r.x0.value, r.jfp.value, ofs)

    def patch_trace(self, faildescr, looptoken, bridge_addr, regalloc):
        # Patch the quick failure stub to jump to the bridge.

        # Before:
        #
        #     old_trace:
        #
        #         ... instructions  ...
        #
        #         if guard_fails:
        #             goto quick_failure_stub_i
        #
        #         ... instructions  ...
        #
        #         quick_failure_stub_i:
        #             push_gcmap()
        #             goto failure_recovery_code
        #
        # After:
        #
        #     old_trace:
        #
        #         ... instructions  ...
        #
        #         if guard_fails:
        #             goto quick_failure_stub_i
        #
        #         ... instructions  ...
        #
        #         quick_failure_stub_i:
        #             bridge_addr = ...
        #             goto bridge_addr

        patch_addr = faildescr.adr_jump_offset
        assert patch_addr != 0

        pmc = InstrBuilder()
        pmc.load_int_imm(r.x31.value, bridge_addr)
        pmc.JR(r.x31.value)
        pmc.emit_pending_constants()
        pmc.copy_to_raw_memory(patch_addr)

        faildescr.adr_jump_offset = 0

    def generate_quick_failure(self, guardtok):
        startpos = self.mc.get_relative_pos()
        faildescrindex, target = self.store_info_on_descr(startpos, guardtok)

        self.store_jf_descr(faildescrindex)
        self.push_gcmap(self.mc, guardtok.gcmap)
        assert target
        self.mc.jal_abs(r.zero.value, target)

        # Generate extra NOPs if this stub size is too small. We need this
        # padding because `patch_trace` will patch this stub to jump to the
        # compiled bridge.
        _emit_nop_until_larger(self.mc, self.mc.get_relative_pos(),
                               startpos + _REDIRECT_BRANCH_STUB_SIZE)
        return startpos

    def write_pending_failure_recoveries(self):
        for guardtok in self.pending_guards:
            guardtok.pos_recovery_stub = self.generate_quick_failure(guardtok)

    def process_pending_guards(self, rawstart):
        clt = self.current_clt
        for guardtok in self.pending_guards:
            descr = guardtok.faildescr
            assert isinstance(descr, AbstractFailDescr)

            failure_recovery_pos = rawstart + guardtok.pos_recovery_stub
            descr.adr_jump_offset = failure_recovery_pos
            relative_offset = guardtok.pos_recovery_stub - guardtok.offset
            guard_pos = rawstart + guardtok.offset

            if guardtok.guard_not_invalidated():
                clt.invalidate_positions.append((guard_pos, relative_offset))
            else:
                # Patch the guard jump to the stub
                assert check_simm21_arg(relative_offset)
                mc = InstrBuilder()
                mc.J(relative_offset)
                mc.copy_to_raw_memory(guard_pos)

    def fixup_target_tokens(self, rawstart):
        for targettoken in self.target_tokens_currently_compiling:
            targettoken._ll_loop_code += rawstart
        self.target_tokens_currently_compiling = None

    def reserve_gcref_table(self, allgcrefs):
        gcref_table_size = len(allgcrefs) * XLEN
        gcref_table_size = (gcref_table_size + 15) & ~15  # Align to 16

        # Reserve space at the beginning of the machine code for the gc table.
        # This lets us access gc table with pc-relative addressing.
        mc = self.mc
        assert mc.get_relative_pos() == 0
        for i in range(gcref_table_size):
            mc.writechar('\x00')

        self.setup_gcrefs_list(allgcrefs)

    def patch_gcref_table(self, looptoken, rawstart):
        self.gc_table_addr = rawstart
        tracer = self.cpu.gc_ll_descr.make_gcref_tracer(rawstart,
                                                        self._allgcrefs)
        gcreftracers = self.get_asmmemmgr_gcreftracers(looptoken)
        gcreftracers.append(tracer)  # Keepalive
        self.teardown_gcrefs_list()

    def load_from_gc_table(self, reg_num, index):
        address_in_buffer = index * XLEN  # at the start of the buffer
        p_location = self.mc.get_relative_pos(break_basic_block=False)
        offset = address_in_buffer - p_location
        self.mc.load_int_pc_rel(reg_num, offset)

    def setup(self, looptoken):
        OpAssembler.setup(self, looptoken)
        assert self.memcpy_addr != 0, 'setup_once() not called?'

        self.current_clt = looptoken.compiled_loop_token
        self.mc = InstrBuilder()
        self.pending_guards = []
        self.target_tokens_currently_compiling = {}

        allblocks = self.get_asmmemmgr_blocks(looptoken)
        self.datablockwrapper = MachineDataBlockWrapper(self.cpu.asmmemmgr,
                                                        allblocks)
        self.mc.datablockwrapper = self.datablockwrapper

        self._frame_depth_to_patch = []
        self._finish_gcmap = jitframe.NULLGCMAP

    def teardown(self):
        self.current_clt = None
        self._regalloc = None
        self.mc = None
        self.pending_guards = None

    def materialize_loop(self, looptoken):
        # Finalizes data block
        self.datablockwrapper.done()
        self.datablockwrapper = None

        # Finalizes instruction builder, combines the code buffers, and copy
        # them to an executable memory region.
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        size = self.mc.get_relative_pos()
        rawstart = self.mc.materialize(self.cpu, allblocks,
                                       self.cpu.gc_ll_descr.gcrootmap)
        # Registers the materialized loop to the codemap.
        self.cpu.codemap.register_codemap(
            self.codemap_builder.get_final_bytecode(rawstart, size))
        return rawstart

    def _build_failure_recovery(self, exc, withfloats=False):
        mc = InstrBuilder()
        self._push_all_regs_to_jitframe(mc, [], withfloats)

        if exc:
            # Move the exception from `self.cpu.pos_exc_value()` to JITFrame
            # `jf_guard_exc` and then reset the data in
            # `self.cpu.pos_exc_value()` and `self.cpu.pos_exception()`.

            scratch_reg = r.x31
            scratch2_reg = r.x10  # Will be set by `_call_footer` soon.

            # Load exc_value from `self.cpu.pos_exc_value()`.
            mc.load_int_imm(scratch_reg.value, self.cpu.pos_exc_value())
            mc.load_int(scratch2_reg.value, scratch_reg.value, 0)

            # Clear `self.cpu.pos_exc_value()`.
            mc.store_int(r.x0.value, scratch_reg.value, 0)

            # Store exc_value to `jf_guard_exc`.
            ofs = self.cpu.get_ofs_of_frame_field('jf_guard_exc')
            mc.store_int(scratch2_reg.value, r.jfp.value, ofs)

            # Clear `self.cpu.pos_exception()`.
            mc.load_int_imm(scratch_reg.value, self.cpu.pos_exception())
            mc.store_int(r.x0.value, scratch_reg.value, 0)

        self._call_footer(mc)
        mc.emit_pending_constants()

        rawstart = mc.materialize(self.cpu, [])
        self.failure_recovery_code[exc + 2 * withfloats] = rawstart

    def propagate_memoryerror_if_reg_is_null(self, reg_loc):
        # Patch Location: BNEZ reg_loc, end
        cond_branch_addr = self.mc.get_relative_pos()
        self.mc.EBREAK()

        # Branch to `propagate_exception_path`
        self.mc.load_int_imm(r.ra.value, self.propagate_exception_path)
        self.mc.JR(r.ra.value)

        # LABEL[end]:
        offset = self.mc.get_relative_pos() - cond_branch_addr
        pmc = OverwritingBuilder(self.mc, cond_branch_addr, INST_SIZE)
        pmc.BNEZ(reg_loc.value, offset)

    def _build_wb_slowpath(self, withcards, withfloats=False, for_frame=False):
        # Build a slow path to call GC write barrier.
        #
        # This builds a helper function called from the fast path of write
        # barriers.  It must save all registers, and optionally all fp
        # registers.  It takes a single argument which is in `r.x10`.  It must
        # keep stack alignment accordingly.

        descr = self.cpu.gc_ll_descr.write_barrier_descr
        if descr is None:
            return

        if not withcards:
            func = descr.get_write_barrier_fn(self.cpu)
        else:
            if descr.jit_wb_cards_set == 0:
                return
            func = descr.get_write_barrier_from_array_fn(self.cpu)
            if func == 0:
                return

        mc = InstrBuilder()

        # Allocate two callee-save scratch registers to handle exception
        # save and restore.
        exc0 = r.x24
        exc1 = r.x25
        fp_align_size = 0
        stack_size = 0
        core_regs_to_be_spilled = []

        if not for_frame:
            self._push_all_regs_to_jitframe(mc, [], withfloats,
                                            callee_only=True)
        else:
            # NOTE: Don't save registers to the jitframe here!  It might
            # override already-saved values that will be restored later.
            #
            # we're possibly called from the slowpath of malloc.  save the
            # caller saved registers assuming GC does not collect here.

            core_regs_to_be_spilled = r.caller_saved_registers + [exc0, exc1]

            core_reg_size = len(core_regs_to_be_spilled) * XLEN
            core_reg_size_aligned = (core_reg_size + FLEN - 1) // FLEN * FLEN
            fp_align_size = core_reg_size_aligned - core_reg_size
            fp_reg_size = len(r.caller_saved_fp_registers) * FLEN
            stack_size = (core_reg_size_aligned + fp_reg_size +
                          ABI_STACK_ALIGN - 1) \
                    // ABI_STACK_ALIGN * ABI_STACK_ALIGN

            mc.ADDI(r.sp.value, r.sp.value, -stack_size)

            # Spill caller-saved registers.
            cur_stack = 0
            for reg in core_regs_to_be_spilled:
                mc.store_int(reg.value, r.sp.value, cur_stack)
                cur_stack += XLEN

            # Spill caller-saved float registers.
            cur_stack += fp_align_size
            for reg in r.caller_saved_fp_registers:
                mc.store_float(reg.value, r.sp.value, cur_stack)
                cur_stack += FLEN

            self._store_and_reset_exception(mc, exc0, exc1)

        func = rffi.cast(lltype.Signed, func)
        mc.load_int_imm(r.ra.value, func)
        mc.JALR(r.ra.value, r.ra.value, 0)

        if not for_frame:
            self._pop_all_regs_from_jitframe(mc, [], withfloats,
                                             callee_only=True)
        else:
            self._restore_exception(mc, exc0, exc1)

            # Restore caller-saved registers.
            cur_stack = 0
            for reg in core_regs_to_be_spilled:
                mc.load_int(reg.value, r.sp.value, cur_stack)
                cur_stack += XLEN

            # Restore caller-saved float registers.
            cur_stack += fp_align_size
            for reg in r.caller_saved_fp_registers:
                mc.load_float(reg.value, r.sp.value, cur_stack)
                cur_stack += FLEN

            mc.ADDI(r.sp.value, r.sp.value, stack_size)

        if withcards:
            # Load and mask the `jit_wb_cards_set_singlebyte` to `x31`, so that
            # the caller of the `wb_slowpath` can emit a simple
            # `BEQZ x31, end_update_card_table`.  This helps us save 2
            # instructions per `COND_CALL_GC_WB_ARRAY`.
            mc.LBU(r.x31.value, r.x10.value, descr.jit_wb_if_flag_byteofs)
            mc.ANDI(r.x31.value, r.x31.value, 0x80)

        mc.RET()
        mc.emit_pending_constants()

        rawstart = mc.materialize(self.cpu, [])
        if for_frame:
            self.wb_slowpath[4] = rawstart
        else:
            self.wb_slowpath[withcards + 2 * withfloats] = rawstart

    def build_frame_realloc_slowpath(self):
        # Build a frame realloc slowpath, which reallocates the frame if the
        # existing frame is smaller than the new size.
        #
        # The slowpath assumes:
        # 1. `r.jfp` holds the old frame address.
        # 2. `r.x31` holds the new frame size.
        # 3. `r.ra` holds the return address

        # Overview: This code should do the following steps:
        #
        # 1. Save all registers to the JITFrame
        # 2. Save exceptions to JITFrame
        # 3. call realloc_frame
        # 4. Set the jfp to point to the new JITFrame
        # 5. Update the JITFrame address on the shadow stack
        # 6. Set the `jf_gcmap` to 0
        # 7. Restore registers
        # 8. Return

        mc = InstrBuilder()

        # Save all registers (except `r.jfp`).
        self._push_all_regs_to_jitframe(mc, [r.jfp], self.cpu.supports_floats)

        # Allocate one callee-saved scratch register for
        # `_store_and_reset_exception`.
        exc_type_reg = r.x25

        # Note: Other backends save the gcmap to `jf_gcmap` here. But in RISCV
        # implementation, we require the caller of this slowpath to set the
        # gcmap so that we don't have to spill another register in the fast
        # path.

        # Set up arguments for `realloc_frame(old_jitframe, new_size)`.
        mc.MV(r.x10.value, r.jfp.value)
        mc.MV(r.x11.value, r.x31.value)

        # Store a possibly present exception.
        self._store_and_reset_exception(mc, None, exc_type_reg,
                                        on_frame=True) # Clobber r.x31 & r.ra

        # Call `realloc_frame(old_jitframe, new_size)`.
        #
        # See also. `rpython/jit/backend/llsupport/llmodel.py` for
        # `realloc_frame`.
        func = rffi.cast(lltype.Signed, self.cpu.realloc_frame)
        mc.load_int_imm(r.ra.value, func)
        mc.JALR(r.ra.value, r.ra.value, 0)

        # Set `r.jfp` to the new JITFrame returned from the previous call.
        mc.MV(r.jfp.value, r.x10.value)

        # Restore a possibly present exception.
        self._restore_exception(mc, None, exc_type_reg)  # Clobber r.ra & r.x31

        # Updates the address at the top of the shadow stack.
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            scratch_reg = r.x31
            rst = gcrootmap.get_root_stack_top_addr()
            mc.load_int_imm(scratch_reg.value, rst)
            mc.load_int(scratch_reg.value, scratch_reg.value, 0)

            # Update the JITFrame address on the shadow stack.
            mc.store_int(r.jfp.value, scratch_reg.value, -XLEN)

        # Reset the `jf_gcmap`.
        gcmap_ofs = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        mc.store_int(r.x0.value, r.jfp.value, gcmap_ofs)

        # Restore all registers (except `r.jfp`).
        self._pop_all_regs_from_jitframe(mc, [r.jfp], self.cpu.supports_floats)

        # Return
        mc.RET()
        mc.emit_pending_constants()

        rawstart = mc.materialize(self.cpu, [])
        self._frame_realloc_slowpath = rawstart

    def _check_frame_depth(self, mc, gcmap, expected_size):
        # Check if the frame is of enough depth to follow this bridge.
        #
        # If the frame isn't large enough, call `_frame_realloc_slowpath` to
        # enlarge the frame.

        scratch_reg = r.x31
        scratch2_reg = r.ra

        # Load the frame depth from the JITFrame.
        descrs = self.cpu.gc_ll_descr.getframedescrs(self.cpu)
        ofs = self.cpu.unpack_fielddescr(descrs.arraydescr.lendescr)
        mc.load_int(scratch2_reg.value, r.jfp.value, ofs)

        # Load the target for the frame depth.
        if expected_size == -1:
            stack_check_cmp_ofs = mc.get_relative_pos()
            mc.EBREAK()  # Patch Location: LOAD_INT scratch_reg, expected_size
            mc.NOP()
            self._frame_depth_to_patch.append(stack_check_cmp_ofs)
        else:
            mc.load_int_imm(scratch_reg.value, expected_size)

        # Patch Location: `BGE scratch2_reg, scratch_reg, end`
        jg_location = mc.get_relative_pos()
        mc.EBREAK()

        # Store gcmap to frame.
        gcmap_ofs = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        mc.load_int_imm(scratch2_reg.value, rffi.cast(lltype.Signed, gcmap))
        mc.store_int(scratch2_reg.value, r.jfp.value, gcmap_ofs)

        # Call `_frame_realloc_slowpath(x31=new_size)`
        mc.load_int_imm(r.ra.value, self._frame_realloc_slowpath)
        mc.JALR(r.ra.value, r.ra.value, 0)

        # LABEL[end]:

        # Patch the `jg_location` above.
        currpos = mc.get_relative_pos()
        pmc = OverwritingBuilder(mc, jg_location, INST_SIZE)
        pmc.BGE(scratch2_reg.value, scratch_reg.value, currpos - jg_location)

    def check_frame_depth_before_jump(self, target_token):
        if target_token in self.target_tokens_currently_compiling:
            return
        if target_token._riscv_clt is self.current_clt:
            return

        # If we are jumping to another loop or bridge, their frame depth
        # requirement can be larger than what we currently have. Thus, emit
        # `_check_frame_depth` sequence, which enlarges JITFrame if necessary.
        expected_size = target_token._riscv_clt.frame_info.jfi_frame_depth
        gcmap = self._regalloc.get_gcmap()
        self._check_frame_depth(self.mc, gcmap, expected_size)

    def patch_frame_depth_checks(self, frame_depth):
        for ofs in self._frame_depth_to_patch:
            pmc = OverwritingBuilder(self.mc, ofs, INST_SIZE * 2)
            pmc.load_int_imm(r.x31.value, frame_depth)

    def update_frame_depth(self, frame_depth):
        baseofs = self.cpu.get_baseofs_of_frame_field()
        self.current_clt.frame_info.update_frame_depth(baseofs, frame_depth)

    def _store_and_reset_exception(self, mc, exc_val_loc=None,
                                   exc_tp_loc=None, on_frame=False):
        # Move the exception object and type from the addresses provided by
        # `self.cpu.pos_exc_value()` and `self.cpu.pos_excption()` to (1) the
        # specified registers and/or (2) `JITFrame.jf_guard_exc` and then
        # reset the data at the addresses provided by `self.cpu.pos_*()`.

        scratch_reg = r.x31
        assert exc_val_loc is not scratch_reg
        assert exc_tp_loc is not scratch_reg

        # Move the data at `self.cpu.pos_exc_value()` to specified location.
        mc.load_int_imm(scratch_reg.value, self.cpu.pos_exc_value())
        if exc_val_loc is not None:
            assert exc_val_loc.is_core_reg()
            mc.load_int(exc_val_loc.value, scratch_reg.value, 0)
        if on_frame:
            # Store exc_value to the JITFRAME.jf_guard_exc
            scratch2_reg = r.ra  # Clobber r.ra is fine when `on_frame=True`.
            ofs = self.cpu.get_ofs_of_frame_field('jf_guard_exc')
            mc.load_int(scratch2_reg.value, scratch_reg.value, 0)
            mc.store_int(scratch2_reg.value, r.jfp.value, ofs)

        # Reset `self.cpu.pos_exc_value()`.
        mc.store_int(r.x0.value, scratch_reg.value, 0)

        # Move the data at `self.cpu.pos_exception()` to specified location.
        mc.load_int_imm(scratch_reg.value, self.cpu.pos_exception())
        if exc_tp_loc is not None:
            assert exc_tp_loc.is_core_reg()
            mc.load_int(exc_tp_loc.value, scratch_reg.value, 0)

        # Reset `self.cpu.pos_exception()`.
        mc.store_int(r.x0.value, scratch_reg.value, 0)

    def _restore_exception(self, mc, exc_val_loc, exc_tp_loc):
        # Restore `self.cpu.pos_exc_value()` and `self.cpu.pos_exception()`
        # from `exc_val_loc` (or `jf_guard_exc`) and `exc_tp_loc` registers.

        # Allocate scratch registeres.
        scratch_reg = r.x31
        scratch2_reg = r.ra
        assert (exc_val_loc is not scratch_reg and
                exc_val_loc is not scratch2_reg)
        assert (exc_tp_loc is not scratch_reg and
                exc_tp_loc is not scratch2_reg)

        # Restore `pos_exc_value`.
        mc.load_int_imm(scratch_reg.value, self.cpu.pos_exc_value())
        if exc_val_loc is not None:
            mc.store_int(exc_val_loc.value, scratch_reg.value, 0)
        else:
            # Load `exc_value` from JITFRAME and put it in `pos_exc_value`.
            ofs = self.cpu.get_ofs_of_frame_field('jf_guard_exc')
            mc.load_int(scratch2_reg.value, r.jfp.value, ofs)
            mc.store_int(scratch2_reg.value, scratch_reg.value, 0)

            # Reset `jf_guard_exc` in the JITFRAME.
            mc.store_int(r.x0.value, r.jfp.value, ofs)

        # Restore `pos_exception` from `exc_tp_loc`.
        mc.load_int_imm(scratch_reg.value, self.cpu.pos_exception())
        mc.store_int(exc_tp_loc.value, scratch_reg.value, 0)

    def _build_propagate_exception_path(self):
        mc = InstrBuilder()

        # Allocate scratch registers.
        #
        # Note: Use `r.x29` instead of `r.x31` because
        # `_store_and_reset_exception` uses `r.x31` internally.
        scratch_reg = r.x29

        self._store_and_reset_exception(mc, scratch_reg)

        ofs = self.cpu.get_ofs_of_frame_field('jf_guard_exc')
        mc.store_int(scratch_reg.value, r.jfp.value, ofs)

        # Store propagate_exception_descr into frame
        propagate_exception_descr = rffi.cast(
            lltype.Signed,
            cast_instance_to_gcref(self.cpu.propagate_exception_descr))
        ofs = self.cpu.get_ofs_of_frame_field('jf_descr')
        mc.load_int_imm(scratch_reg.value, propagate_exception_descr)
        mc.store_int(scratch_reg.value, r.jfp.value, ofs)

        self._call_footer(mc)
        mc.emit_pending_constants()

        rawstart = mc.materialize(self.cpu, [])
        self.propagate_exception_path = rawstart

    def _build_cond_call_slowpath(self, supports_floats, callee_only):
        """ This builds a general call slowpath, for whatever call happens to
        come.

        The address of the callee function comes in r.x30.
        The returning value is stored in r.x30.
        """
        mc = InstrBuilder()

        # Spill registers to JITFRAME
        #
        # Ignore jfp for _reload_frame_if_necessary, x30 for return, x31 for
        # scratch.
        ignore_regs_for_push_pop = [r.jfp, r.x30, r.x31]
        self._push_all_regs_to_jitframe(mc, ignore_regs_for_push_pop,
                                        supports_floats,
                                        callee_only)  # Spills r.ra

        # Branch to the callee function.
        mc.JALR(r.ra.value, r.x30.value, 0)

        # Move return value to r.x30.
        mc.MV(r.x30.value, r.x10.value)

        # Restore registers from JITFRAME
        tmplocs = [r.x29]  # Use callee-saved register as scratch regs
        self._reload_frame_if_necessary(mc, tmplocs)
        self._pop_all_regs_from_jitframe(mc, ignore_regs_for_push_pop,
                                         supports_floats,
                                         callee_only)  # Restores r.ra
        mc.RET()
        mc.emit_pending_constants()
        return mc.materialize(self.cpu, [])

    def _reload_frame_if_necessary(self, mc, tmplocs):
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            stack_top_ptr_addr = gcrootmap.get_root_stack_top_addr()
            mc.load_int_imm(r.jfp.value, stack_top_ptr_addr)
            mc.load_int(r.jfp.value, r.jfp.value, 0)
            mc.load_int(r.jfp.value, r.jfp.value, -XLEN)
        wbdescr = self.cpu.gc_ll_descr.write_barrier_descr
        if gcrootmap and wbdescr:
            # Frame never uses card marking, so we enforce this is not an
            # array.
            self._write_barrier_fastpath(mc, wbdescr, [r.jfp], tmplocs,
                                         array=False, is_frame=True)

    def _build_malloc_slowpath(self, kind):
        # malloc_slowpath for various kinds (fixed, str, unicode, var):
        #
        # x10, x11 = malloc_slowpath_fixed(x10=nursery_free_adr,
        #                                  x11=(nursery_free_adr + size)
        #                                  x31=gcmap)
        #
        # x10, x11 = malloc_slowpath_str/unicode(x10=length_of_string,
        #                                        x31=gcmap)
        #
        # x10, x11 = malloc_slowpath_var(x10=itemsize,
        #                                x11=tid,
        #                                x12=length_of_array,
        #                                x31=gcmap)
        #
        # Returns:
        # x10 = new_object_adr
        # X11 = new_nursery_free_adr

        assert kind in ['fixed', 'str', 'unicode', 'var']
        mc = InstrBuilder()

        # Push registers to JITFrame.

        # Ignore fp for _reload_frame_if_necessary, x10-12 for args, x31 for
        # scratch.
        if kind == 'var':
            ignore_regs_for_push_pop = [r.jfp, r.x10, r.x11, r.x12, r.x31]
        else:
            ignore_regs_for_push_pop = [r.jfp, r.x10, r.x11, r.x31]

        self._push_all_regs_to_jitframe(mc, ignore_regs_for_push_pop,
                                        self.cpu.supports_floats)

        # Select the callee function according to the `kind`.
        if kind == 'fixed':
            addr = self.cpu.gc_ll_descr.get_malloc_slowpath_addr()
        elif kind == 'str':
            addr = self.cpu.gc_ll_descr.get_malloc_fn_addr('malloc_str')
        elif kind == 'unicode':
            addr = self.cpu.gc_ll_descr.get_malloc_fn_addr('malloc_unicode')
        else:
            addr = self.cpu.gc_ll_descr.get_malloc_slowpath_array_addr()

        # Setup the arguments.
        if kind == 'fixed':
            # malloc_slowpath_addr(x10=size)
            # malloc_slowpath_addr(x10=size, x11=jfp)

            # At this point we know that the values we need to compute the size
            # are stored in `r.x10` and `r.x11`.
            mc.SUB(r.x10.value, r.x11.value, r.x10.value)
            if hasattr(self.cpu.gc_ll_descr, 'passes_frame'):
                mc.MV(r.x11.value, r.jfp.value)
        elif kind == 'str' or kind == 'unicode':
            # malloc_str(x10=len), malloc_unicode(x10=len)
            pass
        else:  # var
            # malloc_slowpath_array_addr(x10=itemsize, x11=tid, x12=len)
            pass

        # Store `gcmap` to `jf_gcmap`.
        jf_gcmap_ofs = self.cpu.get_ofs_of_frame_field('jf_gcmap')
        mc.store_int(r.x31.value, r.jfp.value, jf_gcmap_ofs)

        # Call the callee function
        mc.load_int_imm(r.ra.value, rffi.cast(lltype.Signed, addr))
        mc.JALR(r.ra.value, r.ra.value, 0)

        # Patch Loation: BNEZ x10, succeeded
        branch_inst_pos = mc.get_relative_pos()
        mc.EBREAK()

        # If the slowpath malloc failed, we raise a MemoryError that always
        # interrupts the current loop, as a "good enough" approximation.
        mc.load_int_imm(r.ra.value, self.propagate_exception_path)
        mc.JR(r.ra.value)

        # LABEL[succeeded]:
        currpos = mc.get_relative_pos()
        pmc = OverwritingBuilder(mc, branch_inst_pos, INST_SIZE)
        pmc.BNEZ(r.x10.value, currpos - branch_inst_pos)

        # Allocate another caller-save as a scratch register.
        #
        # This must not be `r.ra` nor `r.x31` because `_write_barrier_fastpath`
        # has used them. This can be any other register saved by
        # `_push_all_regs_to_jitframe`.
        scratch2_reg = r.x30

        # Reload the frame.
        self._reload_frame_if_necessary(mc, tmplocs=[scratch2_reg])

        # Pop registers from JITFrame.
        self._pop_all_regs_from_jitframe(mc, ignore_regs_for_push_pop,
                                         self.cpu.supports_floats)

        # Load the nursery_free_adr back to r.x11 because the fast path will
        # store the value in `r.x11` to `&nursery_free_adr`.
        nursery_free_adr = self.cpu.gc_ll_descr.get_nursery_free_addr()
        mc.load_int_imm(r.x11.value, nursery_free_adr)
        mc.load_int(r.x11.value, r.x11.value, 0)

        # Clear the `jf_gcmap`.
        mc.store_int(r.x0.value, r.jfp.value, jf_gcmap_ofs)

        mc.RET()
        mc.emit_pending_constants()

        rawstart = mc.materialize(self.cpu, [])
        return rawstart

    def malloc_cond(self, nursery_free_adr, nursery_top_adr, size, gcmap):
        assert size & (XLEN - 1) == 0

        # Load nursery_free_adr
        self.mc.load_int_imm(r.x10.value, nursery_free_adr)
        self.mc.load_int(r.x10.value, r.x10.value, 0)

        # Add the size to be allocated
        if check_imm_arg(size):
            self.mc.ADDI(r.x11.value, r.x10.value, size)
        else:
            self.mc.load_int_imm(r.x11.value, size)
            self.mc.ADD(r.x11.value, r.x10.value, r.x11.value)

        # Load nursery_top_adr
        scratch_reg = r.x31
        self.mc.load_int_imm(scratch_reg.value, nursery_top_adr)
        self.mc.load_int(scratch_reg.value, scratch_reg.value, 0)

        # Patch Location: BGEU scratch_reg, x11, end
        branch_inst_pos = self.mc.get_relative_pos()
        self.mc.EBREAK()

        # x10, x11 = malloc_slowpath(x10=nursery_free_addr,
        #                            x11=(nursery_free_addr + size),
        #                            x31=gcmap)
        #
        # Returns:
        #
        # x10: new object address
        # X11: new nursery_free_adr

        self.mc.load_int_imm(r.x31.value, rffi.cast(lltype.Signed, gcmap))

        self.mc.load_int_imm(r.ra.value, self.malloc_slowpath)
        self.mc.JALR(r.ra.value, r.ra.value, 0)

        # LABEL[end]:
        currpos = self.mc.get_relative_pos()
        pmc = OverwritingBuilder(self.mc, branch_inst_pos, INST_SIZE)
        pmc.BGEU(scratch_reg.value, r.x11.value, currpos - branch_inst_pos)

        # Update `nursery_free_adr` after allocation.
        self.mc.load_int_imm(scratch_reg.value, nursery_free_adr)
        self.mc.store_int(r.x11.value, scratch_reg.value, 0)

    def malloc_cond_varsize_frame(self, nursery_free_adr, nursery_top_adr,
                                  size_loc, gcmap):
        assert size_loc.is_core_reg()
        assert size_loc is not r.x10 and size_loc is not r.x11

        # Load nursery_free_adr
        self.mc.load_int_imm(r.x10.value, nursery_free_adr)
        self.mc.load_int(r.x10.value, r.x10.value, 0)

        # Add the size to be allocated
        self.mc.ADD(r.x11.value, r.x10.value, size_loc.value)

        # Load nursery_top_adr
        scratch_reg = r.x31
        self.mc.load_int_imm(scratch_reg.value, nursery_top_adr)
        self.mc.load_int(scratch_reg.value, scratch_reg.value, 0)

        # Patch Location: BGEU scratch_reg, x11, end
        branch_inst_pos = self.mc.get_relative_pos()
        self.mc.EBREAK()

        # x10, x11 = malloc_slowpath(x10=nursery_free_addr,
        #                            x11=(nursery_free_addr + size),
        #                            x31=gcmap)

        self.mc.load_int_imm(r.x31.value, rffi.cast(lltype.Signed, gcmap))

        self.mc.load_int_imm(r.ra.value, self.malloc_slowpath)
        self.mc.JALR(r.ra.value, r.ra.value, 0)

        # LABEL[end]:
        currpos = self.mc.get_relative_pos()
        pmc = OverwritingBuilder(self.mc, branch_inst_pos, INST_SIZE)
        pmc.BGEU(scratch_reg.value, r.x11.value, currpos - branch_inst_pos)

        self.mc.load_int_imm(scratch_reg.value, nursery_free_adr)
        self.mc.store_int(r.x11.value, scratch_reg.value, 0)

    def malloc_cond_varsize(self, kind, nursery_free_adr, nursery_top_adr,
                            length_loc, itemsize, max_length, gcmap,
                            arraydescr):
        assert isinstance(arraydescr, ArrayDescr)

        scratch_reg = r.x31

        self.mc.load_int_imm(scratch_reg.value, max_length)

        # Patch Location: BLT scratch_reg, length, call_slowpath
        jmp_adr0 = self.mc.get_relative_pos()
        self.mc.EBREAK()

        # Load nursery_free_adr to r.x10
        self.mc.load_int_imm(r.x10.value, nursery_free_adr)
        self.mc.load_int(r.x10.value, r.x10.value, 0)

        # Calculate total size (header_size + itemsize * len) to be allocated
        self.mc.load_int_imm(scratch_reg.value, itemsize)
        # x11 = length * itemsize
        self.mc.MUL(r.x11.value, length_loc.value, scratch_reg.value)

        assert arraydescr.basesize >= self.gc_minimal_size_in_nursery
        constsize = arraydescr.basesize + self.gc_size_of_header
        force_realignment = (itemsize % XLEN) != 0
        if force_realignment:
            constsize += XLEN - 1
        # x11 = x11 + constsize
        if check_imm_arg(constsize):
            self.mc.ADDI(r.x11.value, r.x11.value, constsize)
        else:
            self.mc.load_int_imm(scratch_reg.value, constsize)
            self.mc.ADD(r.x11.value, r.x11.value, scratch_reg.value)

        # Calculate new nursery_free_adr
        self.mc.ADD(r.x11.value, r.x11.value, r.x10.value)
        if force_realignment:
            self.mc.ANDI(r.x11.value, r.x11.value, -XLEN)

        # Load nursery_top_adr
        self.mc.load_int_imm(scratch_reg.value, nursery_top_adr)
        self.mc.load_int(scratch_reg.value, scratch_reg.value, 0)

        # Patch Location: BGEU scratch_reg, x11, finish_fast_alloc
        jmp_adr1 = self.mc.get_relative_pos()
        self.mc.EBREAK()

        # LABEL[call_slowpath]:
        currpos = self.mc.get_relative_pos()
        pmc = OverwritingBuilder(self.mc, jmp_adr0, INST_SIZE)
        pmc.BLT(scratch_reg.value, length_loc.value, currpos - jmp_adr0)

        # Setup the arguments to slowpaths (see also. _build_malloc_slowpath)
        if kind == rewrite.FLAG_ARRAY:
            self.mc.load_int_imm(r.x10.value, itemsize)
            self.mc.load_int_imm(r.x11.value, arraydescr.tid)
            self.regalloc_mov(length_loc, r.x12)
            addr = self.malloc_slowpath_varsize
        else:
            if kind == rewrite.FLAG_STR:
                addr = self.malloc_slowpath_str
            else:
                assert kind == rewrite.FLAG_UNICODE
                addr = self.malloc_slowpath_unicode
            self.regalloc_mov(length_loc, r.x10)

        # Load the gcmap to r.x31
        self.mc.load_int_imm(r.x31.value, rffi.cast(lltype.Signed, gcmap))

        # Call the callee
        self.mc.load_int_imm(r.ra.value, addr)
        self.mc.JALR(r.ra.value, r.ra.value, 0)

        # Patch Location: J done
        jmp_location = self.mc.get_relative_pos()
        self.mc.EBREAK()

        # LABEL[finish_fast_alloc]:
        currpos = self.mc.get_relative_pos()
        pmc = OverwritingBuilder(self.mc, jmp_adr1, INST_SIZE)
        pmc.BGEU(scratch_reg.value, r.x11.value, currpos - jmp_adr1)

        # Write down the tid.
        self.mc.load_int_imm(scratch_reg.value, arraydescr.tid)
        self.mc.store_int(scratch_reg.value, r.x10.value, 0)

        # Write the new `nursery_free_adr`.
        self.mc.load_int_imm(scratch_reg.value, nursery_free_adr)
        self.mc.store_int(r.x11.value, scratch_reg.value, 0)

        # LABEL[done]:
        currpos = self.mc.get_relative_pos()
        pmc = OverwritingBuilder(self.mc, jmp_location, INST_SIZE)
        pmc.J(currpos - jmp_location)

    def _build_stack_check_slowpath(self):
        _, _, slowpathaddr = self.cpu.insert_stack_check()
        if slowpathaddr == 0 or not self.cpu.propagate_exception_descr:
            return  # No stack check (for tests, or non-translated)

        # Make a "function" that is called immediately at the start of
        # an assembler function.  In particular, the stack looks like:
        #
        #    | saved argument regs |
        #    | retaddr             |  <-- sp
        #    +---------------------+
        #
        mc = InstrBuilder()

        # Save argument registers and return address
        stack_size = (((len(r.argument_regs) + 1) * XLEN + ABI_STACK_ALIGN - 1)
                      // ABI_STACK_ALIGN * ABI_STACK_ALIGN)

        mc.ADDI(r.sp.value, r.sp.value, -stack_size)
        mc.store_int(r.ra.value, r.sp.value, 0)
        for i in range(len(r.argument_regs)):
            mc.store_int(r.argument_regs[i].value, r.sp.value, (i + 1) * XLEN)

        # Pass current stack pointer as argument to the call
        mc.MV(r.x10.value, r.sp.value)
        mc.load_int_imm(r.ra.value, slowpathaddr)
        mc.JALR(r.ra.value, r.ra.value, 0)

        # Check for an exception
        mc.load_int_imm(r.x10.value, self.cpu.pos_exception())
        mc.load_int(r.x10.value, r.x10.value, 0)

        # Patch Location: BNEZ r.x10, propagate_exc
        jmp = mc.get_relative_pos()
        mc.EBREAK()

        # Restore registers and return
        for i in range(len(r.argument_regs)):
            mc.load_int(r.argument_regs[i].value, r.sp.value, (i + 1) * XLEN)
        mc.load_int(r.ra.value, r.sp.value, 0)
        mc.ADDI(r.sp.value, r.sp.value, stack_size)
        mc.RET()

        # LABEL[propagate_exc]:
        pmc = OverwritingBuilder(mc, jmp, INST_SIZE)
        pmc.BNEZ(r.x10.value, mc.get_relative_pos() - jmp)

        mc.ADDI(r.sp.value, r.sp.value, stack_size)
        mc.load_int_imm(r.ra.value, self.propagate_exception_path)
        mc.JR(r.ra.value)
        mc.emit_pending_constants()

        rawstart = mc.materialize(self.cpu, [])
        self.stack_check_slowpath = rawstart

    def load_imm(self, loc, imm):
        """Load an immediate value into a register"""
        if loc.is_core_reg():
            assert imm.is_imm()
            self.mc.load_int_imm(loc.value, imm.value)
        else:
            assert loc.is_fp_reg() and imm.is_imm_float()
            self.mc.load_float_imm(loc.value, imm.value)

    def regalloc_mov(self, prev_loc, loc):
        """Moves a value from a previous location to some other location"""
        if prev_loc.is_imm():
            return self._mov_imm_to_loc(prev_loc, loc)
        elif prev_loc.is_stack():
            self._mov_stack_to_loc(prev_loc, loc)
        elif prev_loc.is_core_reg():
            self._mov_reg_to_loc(prev_loc, loc)
        elif prev_loc.is_fp_reg():
            self._mov_fp_reg_to_loc(prev_loc, loc)
        elif prev_loc.is_imm_float():
            self._mov_imm_float_to_loc(prev_loc, loc)
        else:
            assert 0, 'unsupported case'
    mov_loc_loc = regalloc_mov

    def _mov_imm_to_loc(self, prev_loc, loc):
        if loc.is_core_reg():
            self.mc.load_int_imm(loc.value, prev_loc.value)
        else:
            assert 0, 'unsupported case'

    def _mov_stack_to_loc(self, prev_loc, loc):
        offset = prev_loc.value
        if loc.is_core_reg():
            self.mc.load_int_from_base_plus_offset(loc.value, r.jfp.value,
                                                   offset)
        elif loc.is_fp_reg():
            self.mc.load_float_from_base_plus_offset(loc.value, r.jfp.value,
                                                     offset, tmp=r.x31.value)
        else:
            assert 0, 'unsupported case'

    def _mov_reg_to_loc(self, prev_loc, loc):
        if loc.is_core_reg():
            self.mc.MV(loc.value, prev_loc.value)
        elif loc.is_stack():
            # Use `r.shadow_old` as `scratch_reg`.  We can't use `r.x31`
            # because `prev_loc` can be `r.x31` (see also.
            # `regalloc_prepare_move`).  We can't use `r.ra` because `r.ra` is
            # allocated for the callee function address in `callbuiler.py`
            # and its lifetime overlaps with `remap_frame_layout`.
            scratch_reg = r.shadow_old
            self.mc.store_int_to_base_plus_offset(prev_loc.value, r.jfp.value,
                                                  loc.value,
                                                  tmp=scratch_reg.value)
        else:
            assert 0, 'unsupported case'

    def _mov_fp_reg_to_loc(self, prev_loc, loc):
        if loc.is_fp_reg():
            self.mc.FMV_D(loc.value, prev_loc.value)
        elif loc.is_core_reg():
            assert XLEN == 8 and FLEN == 8
            self.mc.FMV_X_D(loc.value, prev_loc.value)
        elif loc.is_stack():
            self.mc.store_float_to_base_plus_offset(prev_loc.value,
                                                    r.jfp.value, loc.value,
                                                    tmp=r.x31.value)
        else:
            assert 0, 'unsupported case'

    def _mov_imm_float_to_loc(self, prev_loc, loc):
        if loc.is_fp_reg():
            self.mc.load_float_imm(loc.value, prev_loc.value)
        elif loc.is_stack():
            self.mc.load_float_imm(r.f31.value, prev_loc.value)
            self.mc.store_float_to_base_plus_offset(r.f31.value, r.jfp.value,
                                                    loc.value, tmp=r.x31.value)
        else:
            assert 0, 'unsupported case'

    def mov_loc_to_raw_stack(self, loc, sp_offset):
        # Move a value to sp[sp_offset], which is usually for foreign function
        # calls.
        if loc.is_core_reg():
            self.mc.store_int(loc.value, r.sp.value, sp_offset)
        elif loc.is_stack():
            # Move a value from JITFRAME stack to raw stack.
            scratch_reg = r.x31
            self.mc.load_int_from_base_plus_offset(scratch_reg.value,
                                                   r.jfp.value, loc.value)
            self.mc.store_int(scratch_reg.value, r.sp.value, sp_offset)
        elif loc.is_fp_reg():
            self.mc.store_float(loc.value, r.sp.value, sp_offset)
        elif loc.is_imm():
            scratch_reg = r.x31
            self.mc.load_int_imm(scratch_reg.value, loc.value)
            self.mc.store_int(scratch_reg.value, r.sp.value, sp_offset)
        else:
            assert 0, 'unsupported case'

    def regalloc_push(self, loc, already_pushed):
        """Push the value stored in `loc` to the stack top.

        Side effect: r.x31 or r.f31 may be overwritten."""

        offset = SCRATCH_STACK_SLOT_SIZE * (~already_pushed)

        if loc.type == FLOAT:
            if not loc.is_fp_reg():
                self.regalloc_mov(loc, r.f31)
                loc = r.f31
            self.mc.store_float(loc.value, r.sp.value, offset)
        else:
            if not loc.is_core_reg():
                self.regalloc_mov(loc, r.x31)
                loc = r.x31
            self.mc.store_int(loc.value, r.sp.value, offset)

    def regalloc_pop(self, loc, already_pushed):
        """Pop the value from the top of the stack to `loc`.

        Side effect: r.x31 or r.f31 may be overwritten."""

        offset = SCRATCH_STACK_SLOT_SIZE * (~already_pushed)

        if loc.type == FLOAT:
            if loc.is_fp_reg():
                self.mc.load_float(loc.value, r.sp.value, offset)
            else:
                self.mc.load_float(r.f31.value, r.sp.value, offset)
                self.regalloc_mov(r.f31, loc)
        else:
            if loc.is_core_reg():
                self.mc.load_int(loc.value, r.sp.value, offset)
            else:
                self.mc.load_int(r.x31.value, r.sp.value, offset)
                self.regalloc_mov(r.x31, loc)

    def regalloc_prepare_move(self, src, dst, tmp):
        """Move `src` to `tmp` and return `tmp` if `src`-to-`dst` is a
        stack-to-stack or imm-to-stack move."""
        if dst.is_stack() and (src.is_stack() or src.is_imm()):
            self.regalloc_mov(src, tmp)
            return tmp
        return src

    def imm(self, value):
        return ImmLocation(value)

    def new_stack_loc(self, i, tp):
        # Create a StackLocation at `i` of type `tp`.
        #
        # Note: This function is called by rebuild_faillocs_from_descr()

        base_ofs = self.cpu.get_baseofs_of_frame_field()
        return StackLocation(i, get_fp_offset(base_ofs, i), tp)

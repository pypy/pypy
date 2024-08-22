#!/usr/bin/env python

from rpython.jit.backend.llsupport import llerrno
from rpython.jit.backend.llsupport.callbuilder import AbstractCallBuilder
from rpython.jit.backend.llsupport.jump import remap_frame_layout
from rpython.jit.backend.riscv import registers as r
from rpython.jit.backend.riscv.arch import (
    ABI_STACK_ALIGN, FLEN, INST_SIZE, XLEN)
from rpython.jit.backend.riscv.codebuilder import OverwritingBuilder
from rpython.jit.backend.riscv.instructions import (
    AMO_ACQUIRE, AMO_RELEASE)
from rpython.jit.metainterp.history import FLOAT
from rpython.rlib.objectmodel import we_are_translated
from rpython.rtyper.lltypesystem import rffi


class RISCVCallBuilder(AbstractCallBuilder):
    def __init__(self, assembler, fnloc, arglocs, resloc, restype, ressize):
        AbstractCallBuilder.__init__(self, assembler, fnloc, arglocs,
                                     resloc, restype, ressize)
        self.current_sp = 0

    def prepare_arguments(self):
        arglocs = self.arglocs

        non_float_locs = []
        non_float_regs = []
        float_locs = []
        float_regs = []
        stack_locs = []

        free_regs = [r.x17, r.x16, r.x15, r.x14, r.x13, r.x12, r.x11, r.x10]
        free_float_regs = [r.f17, r.f16, r.f15, r.f14, r.f13, r.f12, r.f11,
                           r.f10]

        # Collect argument registers.
        stack_adj_offset = 0
        for arg in arglocs:
            if arg.type == FLOAT:
                if free_float_regs:
                    float_locs.append(arg)
                    float_regs.append(free_float_regs.pop())
                elif free_regs:
                    # If float registers are exhausted but integer registers
                    # are still available, use integer registers.
                    non_float_locs.append(arg)
                    non_float_regs.append(free_regs.pop())
                else:
                    stack_adj_offset += FLEN
                    stack_locs.append(arg)
            else:
                if free_regs:
                    non_float_locs.append(arg)
                    non_float_regs.append(free_regs.pop())
                else:
                    stack_adj_offset += XLEN
                    stack_locs.append(arg)

        if stack_locs:
            # Adjust the stack pointer.
            stack_adj_offset = ((stack_adj_offset + ABI_STACK_ALIGN - 1)
                                    // ABI_STACK_ALIGN * ABI_STACK_ALIGN)
            assert stack_adj_offset <= 2**11, 'too many arguments'
            self.mc.ADDI(r.sp.value, r.sp.value, -stack_adj_offset)
            self.current_sp = stack_adj_offset

            # Spill argument values to the stack offset.
            sp_offset = 0
            for loc in stack_locs:
                self.asm.mov_loc_to_raw_stack(loc, sp_offset)
                sp_offset += FLEN if loc.type == FLOAT else XLEN

        # Assign the callee function address to the `ra` register.
        #
        # Note: In the RISC-V backend, the `ra` (`x1`) register is not an
        # allocatable register, thus it is preserved between
        # `remap_frame_layout` calls.
        if self.fnloc.is_core_reg():
            self.mc.MV(r.ra.value, self.fnloc.value)
        elif self.fnloc.is_imm():
            self.mc.load_int_imm(r.ra.value, self.fnloc.value)
        else:
            assert self.fnloc.is_stack()
            self.mc.load_int(r.ra.value, r.jfp.value, self.fnloc.value)
        self.fnloc = r.ra

        # Move augment values to argument registers.
        scratch_core_reg = r.x31
        scratch_fp_reg = r.f31

        remap_frame_layout(self.asm, non_float_locs, non_float_regs,
                           scratch_core_reg)
        if float_locs:
            remap_frame_layout(self.asm, float_locs, float_regs,
                               scratch_fp_reg)

    def push_gcmap(self):
        noregs = self.asm.cpu.gc_ll_descr.is_shadow_stack()
        gcmap = self.asm._regalloc.get_gcmap([r.x10], noregs=noregs)
        self.asm.push_gcmap(self.mc, gcmap)

    def pop_gcmap(self):
        scratch_reg = r.x12  # caller-saved scratch reg other than ra, x31
        self.asm._reload_frame_if_necessary(self.mc, tmplocs=[scratch_reg])
        self.asm.pop_gcmap(self.mc)

    def emit_raw_call(self):
        assert self.fnloc is r.ra
        self.mc.JALR(self.fnloc.value, self.fnloc.value, 0)

    def restore_stack_pointer(self):
        if self.current_sp == 0:
            return
        self.mc.ADDI(r.sp.value, r.sp.value, self.current_sp)
        self.current_sp = 0

    def load_result(self):
        resloc = self.resloc
        if self.restype == 'S':
            assert False, 'unimplemented'
        elif self.restype == 'L':
            assert False, 'unimplemented'
        if resloc is not None and resloc.is_core_reg():
            self._ensure_result_bit_extension(resloc, self.ressize,
                                              self.ressign)

    def _ensure_result_bit_extension(self, resloc, size, signed):
        if size == XLEN:
            return
        assert XLEN == 8, 'implementation below assumes 64-bit backend'
        if size == 4:
            if signed:
                self.mc.SLLI(resloc.value, resloc.value, 32)
                self.mc.SRAI(resloc.value, resloc.value, 32)
            else:
                self.mc.SLLI(resloc.value, resloc.value, 32)
                self.mc.SRLI(resloc.value, resloc.value, 32)
        elif size == 2:
            if signed:
                self.mc.SLLI(resloc.value, resloc.value, 48)
                self.mc.SRAI(resloc.value, resloc.value, 48)
            else:
                self.mc.SLLI(resloc.value, resloc.value, 48)
                self.mc.SRLI(resloc.value, resloc.value, 48)
        elif size == 1:
            if not signed:
                self.mc.ANDI(resloc.value, resloc.value, 0xFF)
            else:
                self.mc.SLLI(resloc.value, resloc.value, 56)
                self.mc.SRAI(resloc.value, resloc.value, 56)

    def call_releasegil_addr_and_move_real_arguments(self, fastgil):
        assert self.is_call_release_gil
        assert not self.asm._is_asmgcc()

        # `r.thread_id` holds our thread identifier.
        # `r.shadow_old` holds the old value of the shadow stack pointer, which
        # we save here for later comparison.

        scratch_reg = r.x31

        gcrootmap = self.asm.cpu.gc_ll_descr.gcrootmap
        if gcrootmap:
            rst = gcrootmap.get_root_stack_top_addr()
            self.mc.load_int_imm(scratch_reg.value, rst)
            self.mc.load_int(r.shadow_old.value, scratch_reg.value, 0)

        # Change `rpy_fastgil` to 0 (it should be non-zero right now) and save
        # the old value of `rpy_fastgil` into `r.thread_id`.
        self.mc.load_int_imm(scratch_reg.value, fastgil)
        self.mc.load_int(r.thread_id.value, scratch_reg.value, 0)

        # atomic_store_int(0, &rpy_fastgil, mo_release)
        self.mc.atomic_swap_int(r.x0.value, r.x0.value, scratch_reg.value,
                                AMO_RELEASE)

        if not we_are_translated():
            # For testing, we should not access the jfp register any more.
            self.mc.ADDI(r.jfp.value, r.jfp.value, 1)

    def write_real_errno(self, save_err):
        # Use caller-saved registers as scratch registers.
        #
        # Note: Skip x10-x17 registers because they contain the arguments to
        # the future call.
        tls_reg = r.x31
        addr_reg = r.x30
        scratch_reg = r.x29

        if save_err & rffi.RFFI_READSAVED_ERRNO:
            # Just before a call, read `*_errno` and write it into the real
            # `errno`.

            if save_err & rffi.RFFI_ALT_ERRNO:
                rpy_errno = llerrno.get_alt_errno_offset(self.asm.cpu)
            else:
                rpy_errno = llerrno.get_rpy_errno_offset(self.asm.cpu)

            p_errno = llerrno.get_p_errno_offset(self.asm.cpu)

            # TODO: Replace saved_threadlocal_addr with RISCV architecture `tp`
            # (thread pointer) register.
            self.mc.load_int(tls_reg.value, r.sp.value,
                             self.asm.saved_threadlocal_addr + self.current_sp)
            self.mc.load_int_from_base_plus_offset(addr_reg.value,
                                                   tls_reg.value, p_errno)
            self.mc.load_rffi_int_from_base_plus_offset(scratch_reg.value,
                                                        tls_reg.value,
                                                        rpy_errno)
            self.mc.store_rffi_int(scratch_reg.value, addr_reg.value, 0)
        elif save_err & rffi.RFFI_ZERO_ERRNO_BEFORE:
            # Same, but write zero.
            p_errno = llerrno.get_p_errno_offset(self.asm.cpu)
            self.mc.load_int(tls_reg.value, r.sp.value,
                             self.asm.saved_threadlocal_addr + self.current_sp)
            self.mc.load_int_from_base_plus_offset(addr_reg.value,
                                                   tls_reg.value, p_errno)
            self.mc.store_rffi_int(r.x0.value, addr_reg.value, 0)

    def read_real_errno(self, save_err):
        if save_err & rffi.RFFI_SAVE_ERRNO:
            # Just after a call, read the real `errno` and save a copy of
            # it inside our thread-local `*_errno`.

            # Use caller-saved registers as scratch registers.
            tls_reg = r.x30
            scratch_reg = r.x31
            scratch2_reg = r.x29

            if save_err & rffi.RFFI_ALT_ERRNO:
                rpy_errno = llerrno.get_alt_errno_offset(self.asm.cpu)
            else:
                rpy_errno = llerrno.get_rpy_errno_offset(self.asm.cpu)

            p_errno = llerrno.get_p_errno_offset(self.asm.cpu)

            self.mc.load_int(tls_reg.value, r.sp.value,
                             self.asm.saved_threadlocal_addr)
            self.mc.load_int_from_base_plus_offset(scratch_reg.value,
                                                   tls_reg.value, p_errno)
            self.mc.load_rffi_int(scratch_reg.value, scratch_reg.value, 0)
            self.mc.store_rffi_int_to_base_plus_offset(scratch_reg.value,
                                                       tls_reg.value,
                                                       rpy_errno,
                                                       tmp=scratch2_reg.value)

    def move_real_result_and_call_reacqgil_addr(self, fastgil):
        # Try to reacquire the lock. The following two values are saved across
        # the call and are still alive now:
        #
        # r.thread_id   # our thread ident
        # r.shadow_old  # old value of the shadowstack pointer

        # Scratch registers (these must be caller-saved registers)
        scratch_reg = r.x31
        rpy_fastgil_adr_reg = r.x30
        old_fastgil_reg = r.x29

        # Load the address of rpy_fastgil.
        self.mc.load_int_imm(rpy_fastgil_adr_reg.value, fastgil)

        # Compare-and-swap rpy_fastgil:
        #
        # atomic_compare_exchange_strong(old=0, new=r.thread_id,
        #                                addr=&rpy_fastgil)
        self.mc.load_reserve_int(old_fastgil_reg.value,
                                 rpy_fastgil_adr_reg.value,
                                 AMO_ACQUIRE | AMO_RELEASE)
        self.mc.BNEZ(old_fastgil_reg.value, 12)
        self.mc.store_conditional_int(scratch_reg.value, r.thread_id.value,
                                      rpy_fastgil_adr_reg.value,
                                      AMO_ACQUIRE | AMO_RELEASE)
        self.mc.BNEZ(scratch_reg.value, -12)  # Re-try for spurious SC failure.

        # Now, the `old_fastgil_reg` keeps the old value of the lock, and if
        # `old_fastgil_reg == 0` then the lock now contains `r.thread_id`.

        # Patch Location:
        # - boehm: `BEQZ old_fastgil_reg, end`
        # - shadowstack: `BNEZ old_fastgil_reg, reacqgil_slowpath`
        b1_location = self.mc.get_relative_pos()
        self.mc.EBREAK()

        gcrootmap = self.asm.cpu.gc_ll_descr.gcrootmap
        if gcrootmap:
            # When doing a call_release_gil with shadowstack, there is the risk
            # that the `rpy_fastgil` was free but the current shadowstack can
            # be the one of a different thread. So here we check if the
            # shadowstack pointer is still the same as before we released the
            # GIL (saved in `r.shadow_old`), and if not, we fall back to
            # `reacqgil_addr`.
            rst = gcrootmap.get_root_stack_top_addr()
            self.mc.load_int_imm(scratch_reg.value, rst)
            self.mc.load_int(scratch_reg.value, scratch_reg.value, 0)

            # Patch Location: `BEQ scratch_reg, r.shadow_old, end`
            b3_location = self.mc.get_relative_pos()
            self.mc.EBREAK()

            # Revert the rpy_fastgil acquired above, so that the general
            # `self.asm.reacqgil_addr` below can acquire it again.
            #
            # atomic_store_int(0, &rpy_fastgil, mo_release)
            self.mc.atomic_swap_int(r.x0.value, r.x0.value,
                                    rpy_fastgil_adr_reg.value, AMO_RELEASE)

            # Patch the b1_location above.
            pmc = OverwritingBuilder(self.mc, b1_location, INST_SIZE)
            pmc.BNEZ(old_fastgil_reg.value,
                     self.mc.get_relative_pos() - b1_location)

            open_location = b3_location
        else:
            open_location = b1_location

        # LABEL[reacqgil_slowpath]:
        #
        # Save the result value across `reacqgil`.
        saved_res = r.thread_id  # Reuse `r.thread_id` to save things
        reg = self.resloc
        if reg is not None:
            if reg.is_core_reg():
                self.mc.MV(saved_res.value, reg.value)
            elif reg.is_fp_reg():
                assert XLEN == FLEN
                self.mc.FMV_X_D(saved_res.value, reg.value)

        # Call the `reacqgil` function.
        self.mc.load_int_imm(r.ra.value, self.asm.reacqgil_addr)
        self.mc.JALR(r.ra.value, r.ra.value, 0)

        # Restore the saved register
        if reg is not None:
            if reg.is_core_reg():
                self.mc.MV(reg.value, saved_res.value)
            elif reg.is_fp_reg():
                assert XLEN == FLEN
                self.mc.FMV_D_X(reg.value, saved_res.value)

        # LABEL[end]:
        #
        # Patch the `open_location` jump above:
        pmc = OverwritingBuilder(self.mc, open_location, INST_SIZE)
        offset = self.mc.get_relative_pos() - open_location
        if gcrootmap:
            pmc.BEQ(scratch_reg.value, r.shadow_old.value, offset)
        else:
            pmc.BEQZ(old_fastgil_reg.value, offset)

        if not we_are_translated():
            # For testing, now we can access the jfp register again.
            self.mc.ADDI(r.jfp.value, r.jfp.value, -1)

#!/usr/bin/env python

from rpython.jit.backend.llsupport.callbuilder import AbstractCallBuilder
from rpython.jit.backend.llsupport.jump import remap_frame_layout
from rpython.jit.backend.riscv import registers as r
from rpython.jit.backend.riscv.arch import ABI_STACK_ALIGN, FLEN, XLEN
from rpython.jit.metainterp.history import FLOAT


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
        pass

    def pop_gcmap(self):
        pass

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
        assert False, 'unimplemented'

    def write_real_errno(self, save_err):
        assert False, 'unimplemented'

    def read_real_errno(self, save_err):
        assert False, 'unimplemented'

    def move_real_result_and_call_reacqgil_addr(self, fastgil):
        assert False, 'unimplemented'

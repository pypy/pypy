#!/usr/bin/env python

from rpython.jit.backend.llsupport.llmodel import AbstractLLCPU
from rpython.jit.backend.riscv import arch
from rpython.jit.backend.riscv import registers as r
from rpython.jit.backend.riscv.assembler import AssemblerRISCV
from rpython.jit.backend.riscv.codebuilder import InstrBuilder
from rpython.rlib import rgc, rmmap
from rpython.rtyper.lltypesystem import llmemory


class AbstractRISCVCPU(AbstractLLCPU):
    supports_floats = True

    # These are required by BaseAssembler.store_info_on_descr()
    frame_reg = r.jfp
    # Map register to the indices in JITFRAME_FIXED_SIZE. We put x10 (the
    # return value register at 0 because AbstractFailDescr assumes the return
    # value is at index 0.
    all_reg_indexes = [10, 1,  2,  3,  4,  5,  6,  7,
                       8,  9,  0,  11, 12, 13, 14, 15,
                       16, 17, 18, 19, 20, 21, 22, 23,
                       24, 25, 26, 27, 28, 29, 30, 31]
    # The inverse map that maps indices back to general purpose registers.
    gen_regs = [r.x10, r.x1,  r.x2,  r.x3,  r.x4,  r.x5,  r.x6,  r.x7,
                r.x8,  r.x9,  r.x0,  r.x11, r.x12, r.x13, r.x14, r.x15,
                r.x16, r.x17, r.x18, r.x19, r.x20, r.x21, r.x22, r.x23,
                r.x24, r.x25, r.x26, r.x27, r.x28, r.x29, r.x30, r.x31]
    float_regs = r.fp_registers  # List of floating point registers

    JITFRAME_FIXED_SIZE = arch.JITFRAME_FIXED_SIZE

    HAS_CODEMAP = True

    def __init__(self, rtyper, stats, opts=None, translate_support_code=False,
                 gcdescr=None):
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)

    def setup(self):
        self.assembler = AssemblerRISCV(self, self.translate_support_code)

    @rgc.no_release_gil
    def setup_once(self):
        self.assembler.setup_once()
        if self.HAS_CODEMAP:
            self.codemap.setup()

    @rgc.no_release_gil
    def finish_once(self):
        if self.HAS_CODEMAP:
            self.codemap.finish_once()
        self.assembler.finish_once()

    def compile_bridge(self, faildescr, inputargs, operations,
                       original_loop_token, log=True, logger=None):
        clt = original_loop_token.compiled_loop_token
        clt.compiling_a_bridge()
        return self.assembler.assemble_bridge(logger, faildescr, inputargs,
                                              operations, original_loop_token,
                                              log=log)

    def redirect_call_assembler(self, oldlooptoken, newlooptoken):
        self.assembler.redirect_call_assembler(oldlooptoken, newlooptoken)

    @rgc.no_release_gil
    def invalidate_loop(self, looptoken):
        # Replace `GUARD_NOT_INVALIDATED` in the loop with a branch instruction
        # to the recovery stub.

        rmmap.enter_assembler_writing()
        try:
            for jmp, tgt in looptoken.compiled_loop_token.invalidate_positions:
                mc = InstrBuilder()
                mc.J(tgt)
                mc.copy_to_raw_memory(jmp)
        finally:
            rmmap.leave_assembler_writing()

        looptoken.compiled_loop_token.invalidate_positions = []

    def cast_ptr_to_int(x):
        adr = llmemory.cast_ptr_to_adr(x)
        return AbstractRISCVCPU.cast_adr_to_int(adr)
    cast_ptr_to_int._annspecialcase_ = 'specialize:arglltype(0)'
    cast_ptr_to_int = staticmethod(cast_ptr_to_int)


class CPU_RISCV_64(AbstractRISCVCPU):
    backend_name = 'riscv64'
    IS_64_BIT = True

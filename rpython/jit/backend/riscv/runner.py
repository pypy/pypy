#!/usr/bin/env python

from rpython.jit.backend.llsupport.llmodel import AbstractLLCPU
from rpython.jit.backend.riscv import arch
from rpython.jit.backend.riscv import registers as r
from rpython.jit.backend.riscv.assembler import AssemblerRISCV
from rpython.jit.backend.riscv.codebuilder import InstrBuilder
from rpython.rtyper.lltypesystem import llmemory


class AbstractRISCVCPU(AbstractLLCPU):
    supports_floats = True

    # These are required by BaseAssembler.store_info_on_descr()
    frame_reg = r.jfp
    all_reg_indexes = range(32)
    gen_regs = r.registers  # List of general-purpose registers
    float_regs = r.fp_registers  # List of floating point registers

    JITFRAME_FIXED_SIZE = arch.JITFRAME_FIXED_SIZE

    HAS_CODEMAP = True

    def __init__(self, rtyper, stats, opts=None, translate_support_code=False,
                 gcdescr=None):
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)

    def setup(self):
        self.assembler = AssemblerRISCV(self, self.translate_support_code)

    def setup_once(self):
        self.assembler.setup_once()
        if self.HAS_CODEMAP:
            self.codemap.setup()

    def compile_bridge(self, faildescr, inputargs, operations,
                       original_loop_token, log=True, logger=None):
        clt = original_loop_token.compiled_loop_token
        clt.compiling_a_bridge()
        return self.assembler.assemble_bridge(logger, faildescr, inputargs,
                                              operations, original_loop_token,
                                              log=log)

    def redirect_call_assembler(self, oldlooptoken, newlooptoken):
        self.assembler.redirect_call_assembler(oldlooptoken, newlooptoken)

    def invalidate_loop(self, looptoken):
        # Replace `GUARD_NOT_INVALIDATED` in the loop with a branch instruction
        # to the recovery stub.

        for jmp, tgt in looptoken.compiled_loop_token.invalidate_positions:
            mc = InstrBuilder()
            mc.J(tgt)
            mc.copy_to_raw_memory(jmp)

        looptoken.compiled_loop_token.invalidate_positions = []

    def cast_ptr_to_int(x):
        adr = llmemory.cast_ptr_to_adr(x)
        return AbstractRISCVCPU.cast_adr_to_int(adr)
    cast_ptr_to_int._annspecialcase_ = 'specialize:arglltype(0)'
    cast_ptr_to_int = staticmethod(cast_ptr_to_int)


class CPU_RISCV_64(AbstractRISCVCPU):
    backend_name = 'riscv64'
    IS_64_BIT = True

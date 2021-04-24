#!/usr/bin/env python

from rpython.jit.backend.llsupport.llmodel import AbstractLLCPU
from rpython.jit.backend.riscv.assembler import AssemblerRISCV
from rpython.rtyper.lltypesystem import llmemory


class AbstractRISCVCPU(AbstractLLCPU):
    supports_floats = True

    def __init__(self, rtyper, stats, opts=None, translate_support_code=False,
                 gcdescr=None):
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)

    def setup(self):
        self.assembler = AssemblerRISCV(self, self.translate_support_code)

    def setup_once(self):
        self.assembler.setup_once()

    def cast_ptr_to_int(x):
        adr = llmemory.cast_ptr_to_adr(x)
        return AbstractRISCVCPU.cast_adr_to_int(adr)
    cast_ptr_to_int._annspecialcase_ = 'specialize:arglltype(0)'
    cast_ptr_to_int = staticmethod(cast_ptr_to_int)


class CPU_RISCV_64(AbstractRISCVCPU):
    backend_name = 'riscv64'
    IS_64_BIT = True

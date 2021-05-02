#!/usr/bin/env python

from rpython.jit.backend.llsupport.asmmemmgr import BlockBuilderMixin
from rpython.jit.backend.riscv.instruction_builder import (
    gen_all_instr_assemblers)


class AbstractRISCVBuilder(object):
    def write32(self, word):
        self.writechar(chr(word & 0xff))
        self.writechar(chr((word >> 8) & 0xff))
        self.writechar(chr((word >> 16) & 0xff))
        self.writechar(chr((word >> 24) & 0xff))

gen_all_instr_assemblers(AbstractRISCVBuilder)


class InstrBuilder(BlockBuilderMixin, AbstractRISCVBuilder):
    def __init__(self):
        AbstractRISCVBuilder.__init__(self)
        self.init_block_builder()

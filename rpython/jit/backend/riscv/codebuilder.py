#!/usr/bin/env python

from rpython.jit.backend.llsupport.asmmemmgr import BlockBuilderMixin
from rpython.jit.backend.riscv import registers as r
from rpython.jit.backend.riscv.instruction_builder import (
    gen_all_instr_assemblers)
from rpython.rlib.objectmodel import we_are_translated
from rpython.rtyper.lltypesystem import rffi
from rpython.tool.udir import udir


class AbstractRISCVBuilder(object):
    def write32(self, word):
        self.writechar(chr(word & 0xff))
        self.writechar(chr((word >> 8) & 0xff))
        self.writechar(chr((word >> 16) & 0xff))
        self.writechar(chr((word >> 24) & 0xff))

    # Move register
    def MV(self, rd, rs1):
        self.ADDI(rd, rs1, 0)

    # Jump to a pc-relative offset (+/-1MB)
    def J(self, imm):
        self.JAL(r.zero.value, imm)

    # Jump to the address kept in the register
    def JR(self, rs1):
        self.JALR(r.zero.value, rs1, 0)

    # Return from a function
    def RET(self):
        self.JALR(r.zero.value, r.ra.value, 0)

    # Load an XLEN-bit integer from imm(rs1)
    def load_int(self, rd, rs1, imm):
        self.LD(rd, rs1, imm)

    # Store an XLEN-bit integer to imm(rs1)
    def store_int(self, rs2, rs1, imm):
        self.SD(rs2, rs1, imm)

    # Splits a pc-relative offset into an upper part for the auipc instruction
    # and a lower part for the load/store/jalr instructions.
    @staticmethod
    def _split_pc_rel_offset(offset):
        assert -2**31 - 2**11 <= offset <= 2**31 - 2**11 - 1
        lower = offset & 0xfff
        if lower >= 0x800:
            lower -= 0x1000
            offset += 0x1000
        upper = ((offset >> 12) & 0xfffff)
        return (upper, lower)

    # Load an XLEN-bit integer from pc-relative offset
    def load_int_pc_rel(self, rd, offset):
        upper, lower = self._split_pc_rel_offset(offset)
        self.AUIPC(rd, upper)
        self.load_int(rd, rd, lower)

    # Long jump (+/-2GB) to a pc-relative offset
    def jalr_pc_rel(self, rd, offset):
        assert int(rd) != 0
        upper, lower = self._split_pc_rel_offset(offset)
        self.AUIPC(rd, upper)
        self.JALR(rd, rd, lower)

gen_all_instr_assemblers(AbstractRISCVBuilder)


class InstrBuilder(BlockBuilderMixin, AbstractRISCVBuilder):
    def __init__(self):
        AbstractRISCVBuilder.__init__(self)
        self.init_block_builder()

        # ops_offset[None] represents the beginning of the code after the last
        # op (i.e., the tail of the loop)
        self.ops_offset = {}

    def mark_op(self, op):
        self.ops_offset[op] = self.get_relative_pos()

    def _dump_trace(self, addr, name, formatter=-1):
        if not we_are_translated():
            if formatter != -1:
                name = name % formatter
            dir = udir.ensure('asm', dir=True)
            f = dir.join(name).open('wb')
            data = rffi.cast(rffi.CCHARP, addr)
            for i in range(self.get_relative_pos()):
                f.write(data[i])
            f.close()

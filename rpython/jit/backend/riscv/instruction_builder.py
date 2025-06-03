#!/usr/bin/env python

from rpython.jit.backend.riscv.instructions import all_instructions
from rpython.jit.backend.riscv import rounding_modes


def _gen_r_type_instr_assembler(opcode, funct3, funct7):
    bits = (funct7 << 25) | (funct3 << 12) | opcode
    def assemble(self, rd, rs1, rs2):
        rd = int(rd) << 7
        rs1 = int(rs1) << 15
        rs2 = int(rs2) << 20
        self.write32(bits | rs2 | rs1 | rd)
    return assemble

def _gen_i_type_instr_assembler(opcode, funct3):
    bits = (funct3 << 12) | opcode
    def assemble(self, rd, rs1, imm):
        rd = int(rd) << 7
        rs1 = int(rs1) << 15
        imm = (imm & 0xfff) << 20
        self.write32(bits | imm | rs1 | rd)
    return assemble

def _gen_s_type_instr_assembler(opcode, funct3):
    bits = (funct3 << 12) | opcode
    def assemble(self, rs2, rs1, imm):
        rs1 = int(rs1) << 15
        rs2 = int(rs2) << 20
        imm5 = (imm & 0x01f) << 7
        imm7 = (imm & 0xfe0) << 20
        self.write32(bits | imm7 | rs2 | rs1 | imm5)
    return assemble

def _gen_b_type_instr_assembler(opcode, funct3):
    bits = (funct3 << 12) | opcode
    def assemble(self, rs1, rs2, imm):
        rs1 = int(rs1) << 15
        rs2 = int(rs2) << 20
        imm5 = ((imm & 0x01e) | ((imm >> 11) & 1)) << 7
        imm7 = ((imm & 0x7e0) << 20) | (((imm >> 12) & 1) << 31)
        self.write32(bits | imm7 | rs2 | rs1 | imm5)
    return assemble

def _gen_u_type_instr_assembler(opcode):
    def assemble(self, rd, imm):
        rd = int(rd) << 7
        imm20 = (imm & 0xfffff) << 12
        self.write32(imm20 | rd | opcode)
    return assemble

def _gen_j_type_instr_assembler(opcode):
    def assemble(self, rd, imm):
        rd = int(rd) << 7
        imm20 = (((imm & 0x100000) << 11) |
                 ((imm & 0x0007fe) << 20) |
                 ((imm & 0x000800) << 9) |
                 ((imm & 0x0ff000)))
        self.write32(imm20 | rd | opcode)
    return assemble

def _gen_i_shamt5_type_instr_assembler(opcode, funct3, funct7):
    bits = (funct7 << 25) | (funct3 << 12) | opcode
    def assemble(self, rd, rs1, shamt):
        rd = int(rd) << 7
        rs1 = int(rs1) << 15
        shamt = (shamt & 0x1f) << 20
        self.write32(bits | shamt | rs1 | rd)
    return assemble

def _gen_i_shamt6_type_instr_assembler(opcode, funct3, funct6):
    bits = (funct6 << 26) | (funct3 << 12) | opcode
    def assemble(self, rd, rs1, shamt):
        rd = int(rd) << 7
        rs1 = int(rs1) << 15
        shamt = (shamt & 0x3f) << 20
        self.write32(bits | shamt | rs1 | rd)
    return assemble

def _gen_r4_rm_type_instr_assembler(opcode, funct2):
    bits = (funct2 << 25) | opcode
    def assemble(self, rd, rs1, rs2, rs3, rm=rounding_modes.DYN.value):
        rd = int(rd) << 7
        rs1 = int(rs1) << 15
        rs2 = int(rs2) << 20
        rs3 = int(rs3) << 27
        rm = int(rm) << 12
        self.write32(bits | rs3 | rs2 | rs1 | rm | rd)
    return assemble

def _gen_r_rm_type_instr_assembler(opcode, funct7):
    bits = (funct7 << 25) | opcode
    def assemble(self, rd, rs1, rs2, rm=rounding_modes.DYN.value):
        rd = int(rd) << 7
        rs1 = int(rs1) << 15
        rs2 = int(rs2) << 20
        rm = int(rm) << 12
        self.write32(bits | rs2 | rs1 | rm | rd)
    return assemble

def _gen_i12_type_instr_assembler(opcode, funct3, funct12):
    bits = (funct12 << 20) | (funct3 << 12) | opcode
    def assemble(self, rd, rs1):
        rd = int(rd) << 7
        rs1 = int(rs1) << 15
        self.write32(bits | rs1 | rd)
    return assemble

def _gen_i12_rm_type_instr_assembler(opcode, funct12):
    bits = (funct12 << 20) | opcode
    def assemble(self, rd, rs1, rm=rounding_modes.DYN.value):
        rd = int(rd) << 7
        rs1 = int(rs1) << 15
        rm = int(rm) << 12
        self.write32(bits | rs1 | rm | rd)
    return assemble

def _gen_a_type_instr_assembler(opcode, funct25):
    bits = (funct25 << 7) | opcode
    def assemble(self):
        self.write32(bits)
    return assemble

def _gen_f_type_instr_assembler(opcode, funct3, fm):
    bits = (fm << 28) | (funct3 << 12) | opcode
    def assemble(self, pred, succ):
        pred = int(pred) << 24
        succ = int(succ) << 20
        self.write32(bits | pred | succ)
    return assemble

def _gen_amo2_type_instr_assembler(opcode, funct3, funct5):
    bits = (funct5 << 27) | (funct3 << 12) | opcode
    def assemble(self, rd, rs1, aqrl):
        rd = int(rd) << 7
        rs1 = int(rs1) << 15
        aqrl = int(aqrl) << 25
        self.write32(bits | aqrl | rs1 | rd)
    return assemble

def _gen_amo3_type_instr_assembler(opcode, funct3, funct5):
    bits = (funct5 << 27) | (funct3 << 12) | opcode
    def assemble(self, rd, rs2, rs1, aqrl):
        rd = int(rd) << 7
        rs1 = int(rs1) << 15
        rs2 = int(rs2) << 20
        aqrl = int(aqrl) << 25
        self.write32(bits | aqrl | rs2 | rs1 | rd)
    return assemble

_INSTR_TYPE_DICT = {
    'R': _gen_r_type_instr_assembler,
    'I': _gen_i_type_instr_assembler,
    'S': _gen_s_type_instr_assembler,
    'B': _gen_b_type_instr_assembler,
    'U': _gen_u_type_instr_assembler,
    'J': _gen_j_type_instr_assembler,
    'I_SHAMT5': _gen_i_shamt5_type_instr_assembler,
    'I_SHAMT6': _gen_i_shamt6_type_instr_assembler,
    'R4_RM': _gen_r4_rm_type_instr_assembler,
    'R_RM': _gen_r_rm_type_instr_assembler,
    'I12': _gen_i12_type_instr_assembler,
    'I12_RM': _gen_i12_rm_type_instr_assembler,
    'A': _gen_a_type_instr_assembler,
    'F': _gen_f_type_instr_assembler,
    'AMO2': _gen_amo2_type_instr_assembler,
    'AMO3': _gen_amo3_type_instr_assembler,
}

def _gen_instr_assembler(instr_type, fields):
    return _INSTR_TYPE_DICT[instr_type](*fields)

def gen_all_instr_assemblers(cls):
    for mnemonic, instr_type, op_spec, fields in all_instructions:
        setattr(cls, mnemonic, _gen_instr_assembler(instr_type, fields))

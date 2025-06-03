#!/usr/bin/env python

# Each instruction consists of:
#   (mnemonic, instr_type, operand_spec, type_specific_fields)
#
# Operand specification:
#   R: General purpose register
#   RB: General purpose register used as base address
#   F: Floating point register
#   I12: 12-bit immediate
#   I13: 13-bit even immediate (used in B-type instructions)
#   U20: 20-bit unsigned immediate
#   I21: 21-bit even immediate (used in J-type instructions)
#   SH5: 5-bit shift amount
#   SH6: 6-bit shift amount
#   RM: Rounding mode
#   FMO: Fence instruction memory order (see FMO_ constants below)
#   AMO: Acquire/release field for AMO instructions
#   AMOL: Acquire/release field for load reserve
#   AMOS: Acquire/release field for store conditional
#
# Type-specific fields are:
#   R: (opcode, funct3, funct7)
#   I: (opcode, funct3)
#   S: (opcode, funct3)
#   B: (opcode, funct3)
#   U: (opcode,)
#   J: (opcode,)
#   I_SHAMT5: (opcode, funct3, funct7)
#   I_SHAMT6: (opcode, funct3, funct6)
#   R4_RM: (opcode, funct2)
#   R_RM: (opcode, funct7)
#   I12: (opcode, funct3, funct12)
#   I12_RM: (opcode, funct12)
#   A: (opcode, funct25)
#   F: (opcode, funct3, fm)
#   AMO2/AMO3: (opcode, funct3, funct5)

rv_base_i_instructions = [
    ('LUI',       'U', 'R:U20',    (0b0110111,)),
    ('AUIPC',     'U', 'R:U20',    (0b0010111,)),
    ('JAL',       'J', 'R:I21',    (0b1101111,)),
    ('JALR',      'I', 'R:RB:I12', (0b1100111, 0b000)),
    ('BEQ',       'B', 'R:R:I13',  (0b1100011, 0b000)),
    ('BNE',       'B', 'R:R:I13',  (0b1100011, 0b001)),
    ('BLT',       'B', 'R:R:I13',  (0b1100011, 0b100)),
    ('BGE',       'B', 'R:R:I13',  (0b1100011, 0b101)),
    ('BLTU',      'B', 'R:R:I13',  (0b1100011, 0b110)),
    ('BGEU',      'B', 'R:R:I13',  (0b1100011, 0b111)),
    ('LB',        'I', 'R:RB:I12', (0b0000011, 0b000)),
    ('LH',        'I', 'R:RB:I12', (0b0000011, 0b001)),
    ('LW',        'I', 'R:RB:I12', (0b0000011, 0b010)),
    ('LBU',       'I', 'R:RB:I12', (0b0000011, 0b100)),
    ('LHU',       'I', 'R:RB:I12', (0b0000011, 0b101)),
    ('SB',        'S', 'R:RB:I12', (0b0100011, 0b000)),
    ('SH',        'S', 'R:RB:I12', (0b0100011, 0b001)),
    ('SW',        'S', 'R:RB:I12', (0b0100011, 0b010)),
    ('ADDI',      'I', 'R:R:I12',  (0b0010011, 0b000)),
    ('SLTI',      'I', 'R:R:I12',  (0b0010011, 0b010)),
    ('SLTIU',     'I', 'R:R:I12',  (0b0010011, 0b011)),
    ('XORI',      'I', 'R:R:I12',  (0b0010011, 0b100)),
    ('ORI',       'I', 'R:R:I12',  (0b0010011, 0b110)),
    ('ANDI',      'I', 'R:R:I12',  (0b0010011, 0b111)),
    ('ADD',       'R', 'R:R:R',    (0b0110011, 0b000, 0b0000000)),
    ('SUB',       'R', 'R:R:R',    (0b0110011, 0b000, 0b0100000)),
    ('SLL',       'R', 'R:R:R',    (0b0110011, 0b001, 0b0000000)),
    ('SLT',       'R', 'R:R:R',    (0b0110011, 0b010, 0b0000000)),
    ('SLTU',      'R', 'R:R:R',    (0b0110011, 0b011, 0b0000000)),
    ('XOR',       'R', 'R:R:R',    (0b0110011, 0b100, 0b0000000)),
    ('SRL',       'R', 'R:R:R',    (0b0110011, 0b101, 0b0000000)),
    ('SRA',       'R', 'R:R:R',    (0b0110011, 0b101, 0b0100000)),
    ('OR',        'R', 'R:R:R',    (0b0110011, 0b110, 0b0000000)),
    ('AND',       'R', 'R:R:R',    (0b0110011, 0b111, 0b0000000)),
    ('ECALL',     'A', '',         (0b1110011, 0b0000000000000000000000000)),
    ('EBREAK',    'A', '',         (0b1110011, 0b0000000000010000000000000)),
    ('FENCE',     'F', 'FMO:FMO',  (0b0001111, 0b000, 0b0000)),
    ('FENCE_TSO', 'A', '',         (0b0001111, 0b1000001100110000000000000)),
]

rv32_base_i_instructions = [
    ('SLLI',  'I_SHAMT5', 'R:R:SH5', (0b0010011, 0b001, 0b0000000)),
    ('SRLI',  'I_SHAMT5', 'R:R:SH5', (0b0010011, 0b101, 0b0000000)),
    ('SRAI',  'I_SHAMT5', 'R:R:SH5', (0b0010011, 0b101, 0b0100000)),
]

rv64_base_i_instructions = [
    ('LWU',   'I',        'R:RB:I12', (0b0000011, 0b110)),
    ('LD',    'I',        'R:RB:I12', (0b0000011, 0b011)),
    ('SD',    'S',        'R:RB:I12', (0b0100011, 0b011)),
    ('SLLI',  'I_SHAMT6', 'R:R:SH6',  (0b0010011, 0b001, 0b000000)),
    ('SRLI',  'I_SHAMT6', 'R:R:SH6',  (0b0010011, 0b101, 0b000000)),
    ('SRAI',  'I_SHAMT6', 'R:R:SH6',  (0b0010011, 0b101, 0b010000)),
    ('ADDIW', 'I',        'R:R:I12',  (0b0011011, 0b000)),
    ('SLLIW', 'I_SHAMT5', 'R:R:SH5',  (0b0011011, 0b001, 0b0000000)),
    ('SRLIW', 'I_SHAMT5', 'R:R:SH5',  (0b0011011, 0b101, 0b0000000)),
    ('SRAIW', 'I_SHAMT5', 'R:R:SH5',  (0b0011011, 0b101, 0b0100000)),
    ('ADDW',  'R',        'R:R:R',    (0b0111011, 0b000, 0b0000000)),
    ('SUBW',  'R',        'R:R:R',    (0b0111011, 0b000, 0b0100000)),
    ('SLLW',  'R',        'R:R:R',    (0b0111011, 0b001, 0b0000000)),
    ('SRLW',  'R',        'R:R:R',    (0b0111011, 0b101, 0b0000000)),
    ('SRAW',  'R',        'R:R:R',    (0b0111011, 0b101, 0b0100000)),
]

rv_ext_m_instructions = [
    ('MUL',    'R', 'R:R:R', (0b0110011, 0b000, 0b0000001)),
    ('MULH',   'R', 'R:R:R', (0b0110011, 0b001, 0b0000001)),
    ('MULHSU', 'R', 'R:R:R', (0b0110011, 0b010, 0b0000001)),
    ('MULHU',  'R', 'R:R:R', (0b0110011, 0b011, 0b0000001)),
    ('DIV',    'R', 'R:R:R', (0b0110011, 0b100, 0b0000001)),
    ('DIVU',   'R', 'R:R:R', (0b0110011, 0b101, 0b0000001)),
    ('REM',    'R', 'R:R:R', (0b0110011, 0b110, 0b0000001)),
    ('REMU',   'R', 'R:R:R', (0b0110011, 0b111, 0b0000001)),
]

rv64_ext_m_instructions = [
    ('MULW',  'R', 'R:R:R', (0b0111011, 0b000, 0b0000001)),
    ('DIVW',  'R', 'R:R:R', (0b0111011, 0b100, 0b0000001)),
    ('DIVUW', 'R', 'R:R:R', (0b0111011, 0b101, 0b0000001)),
    ('REMW',  'R', 'R:R:R', (0b0111011, 0b110, 0b0000001)),
    ('REMUW', 'R', 'R:R:R', (0b0111011, 0b111, 0b0000001)),
]

rv_ext_d_instructions = [
    ('FLD',       'I',       'F:RB:I12',   (0b0000111, 0b011)),
    ('FSD',       'S',       'F:RB:I12',   (0b0100111, 0b011)),
    ('FMADD_D',   'R4_RM',   'F:F:F:F:RM', (0b1000011, 0b01)),
    ('FMSUB_D',   'R4_RM',   'F:F:F:F:RM', (0b1000111, 0b01)),
    ('FNMSUB_D',  'R4_RM',   'F:F:F:F:RM', (0b1001011, 0b01)),
    ('FNMADD_D',  'R4_RM',   'F:F:F:F:RM', (0b1001111, 0b01)),
    ('FADD_D',    'R_RM',    'F:F:F:RM',   (0b1010011, 0b0000001)),
    ('FSUB_D',    'R_RM',    'F:F:F:RM',   (0b1010011, 0b0000101)),
    ('FMUL_D',    'R_RM',    'F:F:F:RM',   (0b1010011, 0b0001001)),
    ('FDIV_D',    'R_RM',    'F:F:F:RM',   (0b1010011, 0b0001101)),
    ('FSQRT_D',   'I12_RM',  'F:F:RM',     (0b1010011, 0b010110100000)),
    ('FSGNJ_D',   'R',       'F:F:F',      (0b1010011, 0b000, 0b0010001)),
    ('FSGNJN_D',  'R',       'F:F:F',      (0b1010011, 0b001, 0b0010001)),
    ('FSGNJX_D',  'R',       'F:F:F',      (0b1010011, 0b010, 0b0010001)),
    ('FMIN_D',    'R',       'F:F:F',      (0b1010011, 0b000, 0b0010101)),
    ('FMAX_D',    'R',       'F:F:F',      (0b1010011, 0b001, 0b0010101)),
    ('FCVT_S_D',  'I12_RM',  'F:F:RM',     (0b1010011, 0b010000000001)),
    ('FCVT_D_S',  'I12',     'F:F',        (0b1010011, 0b000, 0b010000100000)),
    ('FEQ_D',     'R',       'R:F:F',      (0b1010011, 0b010, 0b1010001)),
    ('FLT_D',     'R',       'R:F:F',      (0b1010011, 0b001, 0b1010001)),
    ('FLE_D',     'R',       'R:F:F',      (0b1010011, 0b000, 0b1010001)),
    ('FCLASS_D',  'I12',     'R:F',        (0b1010011, 0b001, 0b111000100000)),
    ('FCVT_W_D',  'I12_RM',  'R:F:RM',     (0b1010011, 0b110000100000)),
    ('FCVT_WU_D', 'I12_RM',  'R:F:RM',     (0b1010011, 0b110000100001)),
    ('FCVT_D_W',  'I12',     'F:R',        (0b1010011, 0b000, 0b110100100000)),
    ('FCVT_D_WU', 'I12',     'F:R',        (0b1010011, 0b000, 0b110100100001)),
]

rv64_ext_d_instructions = [
    ('FCVT_L_D',  'I12_RM', 'R:F:RM', (0b1010011, 0b110000100010)),
    ('FCVT_LU_D', 'I12_RM', 'R:F:RM', (0b1010011, 0b110000100011)),
    ('FMV_X_D',   'I12',    'R:F',    (0b1010011, 0b000, 0b111000100000)),
    ('FCVT_D_L',  'I12_RM', 'F:R:RM', (0b1010011, 0b110100100010)),
    ('FCVT_D_LU', 'I12_RM', 'F:R:RM', (0b1010011, 0b110100100011)),
    ('FMV_D_X',   'I12',    'F:R',    (0b1010011, 0b000, 0b111100100000)),
]

rv_ext_a_instructions = [
    ('LR_W',      'AMO2', 'R:R:AMOLR',   (0b0101111, 0b010, 0b00010)),
    ('SC_W',      'AMO3', 'R:R:R:AMOSC', (0b0101111, 0b010, 0b00011)),
    ('AMOSWAP_W', 'AMO3', 'R:R:R:AMO',   (0b0101111, 0b010, 0b00001)),
    ('AMOADD_W',  'AMO3', 'R:R:R:AMO',   (0b0101111, 0b010, 0b00000)),
    ('AMOXOR_W',  'AMO3', 'R:R:R:AMO',   (0b0101111, 0b010, 0b00100)),
    ('AMOAND_W',  'AMO3', 'R:R:R:AMO',   (0b0101111, 0b010, 0b01100)),
    ('AMOOR_W',   'AMO3', 'R:R:R:AMO',   (0b0101111, 0b010, 0b01000)),
    ('AMOMIN_W',  'AMO3', 'R:R:R:AMO',   (0b0101111, 0b010, 0b10000)),
    ('AMOMAX_W',  'AMO3', 'R:R:R:AMO',   (0b0101111, 0b010, 0b10100)),
    ('AMOMINU_W', 'AMO3', 'R:R:R:AMO',   (0b0101111, 0b010, 0b11000)),
    ('AMOMAXU_W', 'AMO3', 'R:R:R:AMO',   (0b0101111, 0b010, 0b11100)),
]

rv64_ext_a_instructions = [
    ('LR_D',      'AMO2', 'R:R:AMOLR',   (0b0101111, 0b011, 0b00010)),
    ('SC_D',      'AMO3', 'R:R:R:AMOSC', (0b0101111, 0b011, 0b00011)),
    ('AMOSWAP_D', 'AMO3', 'R:R:R:AMO',   (0b0101111, 0b011, 0b00001)),
    ('AMOADD_D',  'AMO3', 'R:R:R:AMO',   (0b0101111, 0b011, 0b00000)),
    ('AMOXOR_D',  'AMO3', 'R:R:R:AMO',   (0b0101111, 0b011, 0b00100)),
    ('AMOAND_D',  'AMO3', 'R:R:R:AMO',   (0b0101111, 0b011, 0b01100)),
    ('AMOOR_D',   'AMO3', 'R:R:R:AMO',   (0b0101111, 0b011, 0b01000)),
    ('AMOMIN_D',  'AMO3', 'R:R:R:AMO',   (0b0101111, 0b011, 0b10000)),
    ('AMOMAX_D',  'AMO3', 'R:R:R:AMO',   (0b0101111, 0b011, 0b10100)),
    ('AMOMINU_D', 'AMO3', 'R:R:R:AMO',   (0b0101111, 0b011, 0b11000)),
    ('AMOMAXU_D', 'AMO3', 'R:R:R:AMO',   (0b0101111, 0b011, 0b11100)),
]

all_instructions = \
    rv_base_i_instructions + \
    rv64_base_i_instructions + \
    rv_ext_m_instructions + \
    rv64_ext_m_instructions + \
    rv_ext_d_instructions + \
    rv64_ext_d_instructions + \
    rv_ext_a_instructions + \
    rv64_ext_a_instructions

# fence instruction memory ordering immediate fields
FMO_WRITE  = 0b0001
FMO_READ   = 0b0010
FMO_OUTPUT = 0b0100
FMO_INPUT  = 0b1000

AMO_ACQUIRE = 0b10
AMO_RELEASE = 0b01

def _main():
    has_error = False

    # Check whether there are duplicated mnemonics.
    mnemonics = set()
    for mnemonic, instr_type, op_spec, fields in all_instructions:
        if mnemonic in mnemonics:
            print 'error: Found duplicated mnemonic:', mnemonic
            has_error = True
        mnemonics.add(mnemonic)

    # Check whether the type-specific fields are correct.
    _EXPECTED_NUM_FIELDS = {
        'R': 3,
        'I': 2,
        'S': 2,
        'B': 2,
        'U': 1,
        'J': 1,
        'I_SHAMT5': 3,
        'I_SHAMT6': 3,
        'R4_RM': 2,
        'R_RM': 2,
        'I12': 3,
        'I12_RM': 2,
        'A': 2,
        'F': 3,
        'AMO2': 3,
        'AMO3': 3,
    }
    for mnemonic, instr_type, op_spec, fields in all_instructions:
        if len(fields) != _EXPECTED_NUM_FIELDS[instr_type]:
            print 'error: Mismatched number of fields:', mnemonic
            has_error = True

    # Check whether the operand specification matches the instruction type.
    _SUPPORTED_OP_SPEC = {
        'R': {'F:F:F', 'R:F:F', 'R:R:R'},
        'I': {'F:RB:I12', 'R:R:I12', 'R:RB:I12'},
        'S': {'F:RB:I12', 'R:RB:I12'},
        'B': {'R:R:I13'},
        'U': {'R:U20'},
        'J': {'R:I21'},
        'I_SHAMT5': {'R:R:SH5'},
        'I_SHAMT6': {'R:R:SH6'},
        'R4_RM': {'F:F:F:F:RM'},
        'R_RM': {'F:F:F:RM'},
        'I12': {'F:F', 'F:R', 'R:F'},
        'I12_RM': {'F:F:RM', 'F:R:RM', 'R:F:RM'},
        'A': {''},
        'F': {'FMO:FMO'},
        'AMO2': {'R:R:AMOLR'},
        'AMO3': {'R:R:R:AMO', 'R:R:R:AMOSC'},
    }
    for mnemonic, instr_type, op_spec, fields in all_instructions:
        if op_spec not in _SUPPORTED_OP_SPEC[instr_type]:
            print 'error: Unsupported operand specification:', mnemonic, \
                    instr_type, op_spec
            has_error = True

    # Check whether there are unused supported operand specifications.
    all_instructions_op_specs = set(
        (instr_type, op_spec) for _, instr_type, op_spec, _ in all_instructions)
    for instr_type, op_specs in _SUPPORTED_OP_SPEC.iteritems():
        for op_spec in op_specs:
            if (instr_type, op_spec) not in all_instructions_op_specs:
                print 'error: Found unused supported operand spec:', \
                        instr_type, op_spec
                has_error = True

    if not has_error:
        print 'defined', len(mnemonics), 'instructions successfully'

if __name__ == '__main__':
    _main()
del _main

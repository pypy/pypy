import py
from pypy.rlib.objectmodel import ComputedIntSymbolic, we_are_translated
from pypy.rlib.objectmodel import specialize
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.rarithmetic import intmask
from pypy.rpython.lltypesystem import rffi

BYTE_REG_FLAG = 0x20
NO_BASE_REGISTER = -1

class R(object):
    # the following are synonyms for rax, rcx, etc. on 64 bits
    eax, ecx, edx, ebx, esp, ebp, esi, edi = range(8)

    # 8-bit registers
    al, cl, dl, bl, ah, ch, dh, bh = [reg | BYTE_REG_FLAG for reg in range(8)]

    # xmm registers
    xmm0, xmm1, xmm2, xmm3, xmm4, xmm5, xmm6, xmm7 = range(8)

    # the following are extra registers available only on 64 bits
    r8, r9, r10, r11, r12, r13, r14, r15 = range(8, 16)
    xmm8, xmm9, xmm10, xmm11, xmm12, xmm13, xmm14, xmm15 = range(8, 16)

    # These replace ah, ch, dh, bh when the REX-prefix is used
    spl, bpl, sil, dil = ah, ch, dh, bh

    # Low-byte of extra registers
    r8l, r9l, r10l, r11l, r12l, r13l, r14l, r15l = [reg | BYTE_REG_FLAG for reg in range(8, 16)]

    names = ['eax', 'ecx', 'edx', 'ebx', 'esp', 'ebp', 'esi', 'edi',
             'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15']
    xmmnames = ['xmm%d' % i for i in range(16)]

def low_byte(reg):
    # XXX: On 32-bit, this only works for 0 <= reg < 4
    # Maybe we should check this?
    return reg | BYTE_REG_FLAG

def high_byte(reg):
    # This probably shouldn't be called in 64-bit mode, since to use the
    # high-byte registers you have to make sure that there is no REX-prefix
    assert 0 <= reg < 4
    return (reg + 4) | BYTE_REG_FLAG

def single_byte(value):
    return -128 <= value < 128

def fits_in_32bits(value):
    return -2147483648 <= value <= 2147483647

# ____________________________________________________________
# Emit a single char

def encode_char(mc, _, char, orbyte):
    mc.writechar(chr(char | orbyte))
    return 0

# ____________________________________________________________
# Encode a register number in the orbyte

def reg_number_3bits(mc, reg):
    if mc.WORD == 4:
        assert 0 <= reg < 8
        return reg
    else:
        assert 0 <= reg < 16
        return reg & 7

@specialize.arg(2)
def encode_register(mc, reg, factor, orbyte):
    return orbyte | (reg_number_3bits(mc, reg) * factor)

@specialize.arg(2)
def rex_register(mc, reg, factor):
    if reg >= 8:
        if factor == 1:
            return REX_B
        elif factor == 8:
            return REX_R
        else:
            raise ValueError(factor)
    return 0

def register(argnum, factor=1):
    assert factor in (1, 8)
    return encode_register, argnum, factor, rex_register

@specialize.arg(2)
def rex_byte_register(mc, reg, factor):
    assert reg & BYTE_REG_FLAG
    return rex_register(mc, reg & ~BYTE_REG_FLAG, factor)

@specialize.arg(2)
def encode_byte_register(mc, reg, factor, orbyte):
    assert reg & BYTE_REG_FLAG
    return encode_register(mc, reg & ~BYTE_REG_FLAG, factor, orbyte)

def byte_register(argnum, factor=1):
    assert factor in (1, 8)
    return encode_byte_register, argnum, factor, rex_byte_register


# ____________________________________________________________
# Encode a constant in the orbyte

def encode_orbyte(mc, _, constant, orbyte):
    return orbyte | constant

def orbyte(value):
    return encode_orbyte, None, value, None

# ____________________________________________________________
# Emit an immediate value

@specialize.arg(2)
def encode_immediate(mc, immediate, width, orbyte):
    assert orbyte == 0
    if width == 'b':
        mc.writeimm8(immediate)
    elif width == 'h':
        mc.writeimm16(immediate)
    elif width == 'o':
        return immediate    # in the 'orbyte' for the next command
    elif width == 'q' and mc.WORD == 8:
        mc.writeimm64(immediate)
    else:
        if mc._use_16_bit_immediate:
            mc.writeimm16(immediate)
        else:
            mc.writeimm32(immediate)
    return 0

def immediate(argnum, width='i'):
    return encode_immediate, argnum, width, None

# ____________________________________________________________
# Emit an immediate displacement (relative to the cur insn)

def encode_relative(mc, relative_target, _, orbyte):
    assert orbyte == 0
    mc.writeimm32(relative_target)
    return 0

def relative(argnum):
    return encode_relative, argnum, None, None

# ____________________________________________________________
# Emit a mod/rm referencing a stack location [EBP+offset]

@specialize.arg(2)
def encode_stack_bp(mc, offset, force_32bits, orbyte):
    if not force_32bits and single_byte(offset):
        mc.writechar(chr(0x40 | orbyte | R.ebp))
        mc.writeimm8(offset)
    else:
        mc.writechar(chr(0x80 | orbyte | R.ebp))
        mc.writeimm32(offset)
    return 0

def stack_bp(argnum, force_32bits=False):
    return encode_stack_bp, argnum, force_32bits, None

# ____________________________________________________________
# Emit a mod/rm referencing a stack location [ESP+offset]

def encode_stack_sp(mc, offset, _, orbyte):
    SIB = chr((R.esp<<3) | R.esp)    #   use [esp+(no index)+offset]
    if offset == 0:
        mc.writechar(chr(0x04 | orbyte))
        mc.writechar(SIB)
    elif single_byte(offset):
        mc.writechar(chr(0x44 | orbyte))
        mc.writechar(SIB)
        mc.writeimm8(offset)
    else:
        mc.writechar(chr(0x84 | orbyte))
        mc.writechar(SIB)
        mc.writeimm32(offset)
    return 0

def stack_sp(argnum):
    return encode_stack_sp, argnum, None, None

# ____________________________________________________________
# Emit a mod/rm referencing a memory location [reg1+offset]

def encode_mem_reg_plus_const(mc, (reg, offset), _, orbyte):
    assert reg != R.esp and reg != R.ebp
    #
    reg1 = reg_number_3bits(mc, reg)
    no_offset = offset == 0
    SIB = -1
    # 64-bits special cases for reg1 == r12 or r13
    # (which look like esp or ebp after being truncated to 3 bits)
    if mc.WORD == 8:
        if reg1 == R.esp:               # forces an SIB byte:
            SIB = (R.esp<<3) | R.esp    #   use [r12+(no index)+offset]
        elif reg1 == R.ebp:
            no_offset = False
    # end of 64-bits special cases
    if no_offset:
        mc.writechar(chr(0x00 | orbyte | reg1))
        if SIB >= 0: mc.writechar(chr(SIB))
    elif single_byte(offset):
        mc.writechar(chr(0x40 | orbyte | reg1))
        if SIB >= 0: mc.writechar(chr(SIB))
        mc.writeimm8(offset)
    else:
        mc.writechar(chr(0x80 | orbyte | reg1))
        if SIB >= 0: mc.writechar(chr(SIB))
        mc.writeimm32(offset)
    return 0

def rex_mem_reg_plus_const(mc, (reg, offset), _):
    if reg >= 8:
        return REX_B
    return 0

def mem_reg_plus_const(argnum):
    return encode_mem_reg_plus_const, argnum, None, rex_mem_reg_plus_const

# ____________________________________________________________
# Emit a mod/rm referencing an array memory location [reg1+reg2*scale+offset]

def encode_mem_reg_plus_scaled_reg_plus_const(mc,
                                              (reg1, reg2, scaleshift, offset),
                                              _, orbyte):
    # emit "reg1 + (reg2 << scaleshift) + offset"
    assert reg1 != R.ebp and reg2 != R.esp
    assert 0 <= scaleshift < 4
    reg2 = reg_number_3bits(mc, reg2)

    # Special case for no base register
    if reg1 == NO_BASE_REGISTER:
        # modrm
        mc.writechar(chr(0x04 | orbyte))
        # SIB
        mc.writechar(chr((scaleshift<<6) | (reg2<<3) | 5))
        # We're forced to output a disp32, even if offset == 0
        mc.writeimm32(offset)
        return 0

    reg1 = reg_number_3bits(mc, reg1)

    SIB = chr((scaleshift<<6) | (reg2<<3) | reg1)
    #
    no_offset = offset == 0
    # 64-bits special case for reg1 == r13
    # (which look like ebp after being truncated to 3 bits)
    if mc.WORD == 8:
        if reg1 == R.ebp:
            no_offset = False
    # end of 64-bits special case
    if no_offset:
        mc.writechar(chr(0x04 | orbyte))
        mc.writechar(SIB)
    elif single_byte(offset):
        mc.writechar(chr(0x44 | orbyte))
        mc.writechar(SIB)
        mc.writeimm8(offset)
    else:
        mc.writechar(chr(0x84 | orbyte))
        mc.writechar(SIB)
        mc.writeimm32(offset)
    return 0

def rex_mem_reg_plus_scaled_reg_plus_const(mc,
                                           (reg1, reg2, scaleshift, offset),
                                           _):
    rex = 0
    if reg1 >= 8: rex |= REX_B
    if reg2 >= 8: rex |= REX_X
    return rex

def mem_reg_plus_scaled_reg_plus_const(argnum):
    return (encode_mem_reg_plus_scaled_reg_plus_const, argnum, None,
            rex_mem_reg_plus_scaled_reg_plus_const)

# ____________________________________________________________
# Emit a mod/rm referencing an immediate address that fits in 32-bit
# (the immediate address itself must be explicitely encoded as well,
# with immediate(argnum)).

def encode_abs(mc, _1, _2, orbyte):
    # expands to either '\x05' on 32-bit, or '\x04\x25' or 64-bit
    if mc.WORD == 8:
        mc.writechar(chr(0x04 | orbyte))
        mc.writechar(chr(0x25))
    else:
        mc.writechar(chr(0x05 | orbyte))
    return 0

abs_ = encode_abs, 0, None, None

# ____________________________________________________________
# For 64-bits mode: the REX.W, REX.R, REX.X, REG.B prefixes

REX_W = 8
REX_R = 4
REX_X = 2
REX_B = 1

@specialize.arg(2)
def encode_rex(mc, rexbyte, basevalue, orbyte):
    if mc.WORD == 8:
        assert 0 <= rexbyte < 8
        # XXX: Hack. Ignore REX.W if we are using 16-bit operands
        if mc._use_16_bit_immediate:
            basevalue &= ~REX_W
        if basevalue != 0 or rexbyte != 0:
            if basevalue == 0:
                basevalue = 0x40
            mc.writechar(chr(basevalue | rexbyte))
    else:
        assert rexbyte == 0
    return 0

rex_w  = encode_rex, 0, (0x40 | REX_W), None      # a REX.W prefix
rex_nw = encode_rex, 0, 0, None                   # an optional REX prefix
rex_fw = encode_rex, 0, 0x40, None                # a forced REX prefix

# ____________________________________________________________

def insn(*encoding):
    def encode(mc, *args):
        rexbyte = 0
        if mc.WORD == 8:
            # compute the REX byte, if any
            for encode_step, arg, extra, rex_step in encoding_steps:
                if rex_step:
                    if arg is not None:
                        arg = args[arg-1]
                    rexbyte |= rex_step(mc, arg, extra)
        args = (rexbyte,) + args
        # emit the bytes of the instruction
        orbyte = 0
        for encode_step, arg, extra, rex_step in encoding_steps:
            if arg is not None:
                arg = args[arg]
            orbyte = encode_step(mc, arg, extra, orbyte)
        assert orbyte == 0

    #
    encoding_steps = []
    for step in encoding:
        if isinstance(step, str):
            for c in step:
                encoding_steps.append((encode_char, None, ord(c), None))
        else:
            assert type(step) is tuple and len(step) == 4
            encoding_steps.append(step)
    encoding_steps = unrolling_iterable(encoding_steps)
    return encode

def xmminsn(*encoding):
    encode = insn(*encoding)
    encode.is_xmm_insn = True
    return encode

def common_modes(group):
    base = group * 8
    char = chr(0xC0 | base)
    INSN_ri8 = insn(rex_w, '\x83', register(1), char, immediate(2,'b'))
    INSN_ri32= insn(rex_w, '\x81', register(1), char, immediate(2))
    INSN_rr = insn(rex_w, chr(base+1), register(2,8), register(1,1), '\xC0')
    INSN_br = insn(rex_w, chr(base+1), register(2,8), stack_bp(1))
    INSN_rb = insn(rex_w, chr(base+3), register(1,8), stack_bp(2))
    INSN_rm = insn(rex_w, chr(base+3), register(1,8), mem_reg_plus_const(2))
    INSN_rj = insn(rex_w, chr(base+3), register(1,8), abs_, immediate(2))
    INSN_ji8 = insn(rex_w, '\x83', orbyte(base), abs_, immediate(1),
                    immediate(2,'b'))
    INSN_bi8 = insn(rex_w, '\x83', orbyte(base), stack_bp(1), immediate(2,'b'))
    INSN_bi32= insn(rex_w, '\x81', orbyte(base), stack_bp(1), immediate(2))

    def INSN_ri(mc, reg, immed):
        if single_byte(immed):
            INSN_ri8(mc, reg, immed)
        else:
            INSN_ri32(mc, reg, immed)
    INSN_ri._always_inline_ = True      # try to constant-fold single_byte()

    def INSN_bi(mc, offset, immed):
        if single_byte(immed):
            INSN_bi8(mc, offset, immed)
        else:
            INSN_bi32(mc, offset, immed)
    INSN_bi._always_inline_ = True      # try to constant-fold single_byte()

    return (INSN_ri, INSN_rr, INSN_rb, INSN_bi, INSN_br, INSN_rm, INSN_rj,
            INSN_ji8)

def select_8_or_32_bit_immed(insn_8, insn_32):
    def INSN(*args):
        immed = args[-1]
        if single_byte(immed):
            insn_8(*args)
        else:
            assert fits_in_32bits(immed)
            insn_32(*args)

    return INSN

def shifts(mod_field):
    modrm = chr(0xC0 | (mod_field << 3))
    shift_once = insn(rex_w, '\xD1', register(1), modrm)
    shift_r_by_cl = insn(rex_w, '\xD3', register(1), modrm)
    shift_ri8 = insn(rex_w, '\xC1', register(1), modrm, immediate(2, 'b'))

    def shift_ri(mc, reg, immed):
        if immed == 1:
            shift_once(mc, reg)
        else:
            shift_ri8(mc, reg, immed)

    def shift_rr(mc, reg1, reg2):
        assert reg2 == R.ecx
        shift_r_by_cl(mc, reg1)

    return (shift_ri, shift_rr)
# ____________________________________________________________


# Method names take the form of
#
#     <instruction name>_<operand type codes>
#
# For example, the method name for "mov reg, immed" is MOV_ri. Operand order
# is Intel-style, with the destination first.
#
# The operand type codes are:
#     r - register
#     b - ebp/rbp offset
#     s - esp/rsp offset
#     j - address
#     i - immediate
#     x - XMM register
#     a - 4-tuple: (base_register, scale_register, scale, offset)
#     m - 2-tuple: (base_register, offset)
class AbstractX86CodeBuilder(object):
    """Abstract base class."""

    # Used by the 16-bit version of instructions
    _use_16_bit_immediate = False

    def writechar(self, char):
        raise NotImplementedError

    def writeimm8(self, imm):
        self.writechar(chr(imm & 0xFF))

    def writeimm16(self, imm):
        self.writechar(chr(imm & 0xFF))
        self.writechar(chr((imm >> 8) & 0xFF))

    def writeimm32(self, imm):
        assert fits_in_32bits(imm)
        self.writechar(chr(imm & 0xFF))
        self.writechar(chr((imm >> 8) & 0xFF))
        self.writechar(chr((imm >> 16) & 0xFF))
        self.writechar(chr((imm >> 24) & 0xFF))

    # ------------------------------ MOV ------------------------------

    MOV_ri = insn(rex_w, register(1), '\xB8', immediate(2, 'q'))
    MOV8_ri = insn(rex_fw, byte_register(1), '\xB0', immediate(2, 'b'))

    # ------------------------------ Arithmetic ------------------------------

    ADD_ri, ADD_rr, ADD_rb, _, _, ADD_rm, ADD_rj, _ = common_modes(0)
    OR_ri,  OR_rr,  OR_rb,  _, _, OR_rm,  OR_rj,  _ = common_modes(1)
    AND_ri, AND_rr, AND_rb, _, _, AND_rm, AND_rj, _ = common_modes(4)
    SUB_ri, SUB_rr, SUB_rb, _, _, SUB_rm, SUB_rj, SUB_ji8 = common_modes(5)
    SBB_ri, SBB_rr, SBB_rb, _, _, SBB_rm, SBB_rj, _ = common_modes(3)
    XOR_ri, XOR_rr, XOR_rb, _, _, XOR_rm, XOR_rj, _ = common_modes(6)
    CMP_ri, CMP_rr, CMP_rb, CMP_bi, CMP_br, CMP_rm, CMP_rj, _ = common_modes(7)

    CMP_mi8 = insn(rex_w, '\x83', orbyte(7<<3), mem_reg_plus_const(1), immediate(2, 'b'))
    CMP_mi32 = insn(rex_w, '\x81', orbyte(7<<3), mem_reg_plus_const(1), immediate(2))
    CMP_mi = select_8_or_32_bit_immed(CMP_mi8, CMP_mi32)
    CMP_mr = insn(rex_w, '\x39', register(2, 8), mem_reg_plus_const(1))

    CMP_ji8 = insn(rex_w, '\x83', orbyte(7<<3), abs_,
                   immediate(1), immediate(2, 'b'))
    CMP_ji32 = insn(rex_w, '\x81', orbyte(7<<3), abs_,
                    immediate(1), immediate(2))
    CMP_ji = select_8_or_32_bit_immed(CMP_ji8, CMP_ji32)
    CMP_jr = insn(rex_w, '\x39', register(2, 8), abs_, immediate(1))

    CMP32_mi = insn(rex_nw, '\x81', orbyte(7<<3), mem_reg_plus_const(1), immediate(2))

    CMP8_ri = insn(rex_fw, '\x80', byte_register(1), '\xF8', immediate(2, 'b'))

    AND8_rr = insn(rex_fw, '\x20', byte_register(1), byte_register(2,8), '\xC0')

    OR8_rr = insn(rex_fw, '\x08', byte_register(1), byte_register(2,8), '\xC0')

    NEG_r = insn(rex_w, '\xF7', register(1), '\xD8')

    DIV_r = insn(rex_w, '\xF7', register(1), '\xF0')
    IDIV_r = insn(rex_w, '\xF7', register(1), '\xF8')

    IMUL_rr = insn(rex_w, '\x0F\xAF', register(1, 8), register(2), '\xC0')
    IMUL_rb = insn(rex_w, '\x0F\xAF', register(1, 8), stack_bp(2))

    IMUL_rri8 = insn(rex_w, '\x6B', register(1, 8), register(2), '\xC0', immediate(3, 'b'))
    IMUL_rri32 = insn(rex_w, '\x69', register(1, 8), register(2), '\xC0', immediate(3))
    IMUL_rri = select_8_or_32_bit_immed(IMUL_rri8, IMUL_rri32)

    def IMUL_ri(self, reg, immed):
        self.IMUL_rri(reg, reg, immed)

    SHL_ri, SHL_rr = shifts(4)
    SHR_ri, SHR_rr = shifts(5)
    SAR_ri, SAR_rr = shifts(7)

    NOT_r = insn(rex_w, '\xF7', register(1), '\xD0')
    NOT_b = insn(rex_w, '\xF7', orbyte(2<<3), stack_bp(1))

    # ------------------------------ Misc stuff ------------------------------

    NOP = insn('\x90')
    RET = insn('\xC3')

    PUSH_r = insn(rex_nw, register(1), '\x50')
    PUSH_b = insn(rex_nw, '\xFF', orbyte(6<<3), stack_bp(1))
    PUSH_i32 = insn('\x68', immediate(1, 'i'))

    POP_r = insn(rex_nw, register(1), '\x58')
    POP_b = insn(rex_nw, '\x8F', orbyte(0<<3), stack_bp(1))

    LEA_rb = insn(rex_w, '\x8D', register(1,8), stack_bp(2))
    LEA_rs = insn(rex_w, '\x8D', register(1,8), stack_sp(2))
    LEA32_rb = insn(rex_w, '\x8D', register(1,8),stack_bp(2,force_32bits=True))
    LEA_ra = insn(rex_w, '\x8D', register(1, 8), mem_reg_plus_scaled_reg_plus_const(2))
    LEA_rm = insn(rex_w, '\x8D', register(1, 8), mem_reg_plus_const(2))
    LEA_rj = insn(rex_w, '\x8D', register(1, 8), abs_, immediate(2))

    CALL_l = insn('\xE8', relative(1))
    CALL_r = insn(rex_nw, '\xFF', register(1), chr(0xC0 | (2<<3)))
    CALL_b = insn('\xFF', orbyte(2<<3), stack_bp(1))

    # XXX: Only here for testing purposes..."as" happens the encode the
    # registers in the opposite order that we would otherwise do in a
    # register-register exchange.
    #XCHG_rr = insn(rex_w, '\x87', register(1), register(2,8), '\xC0')

    JMP_l = insn('\xE9', relative(1))
    JMP_r = insn(rex_nw, '\xFF', orbyte(4<<3), register(1), '\xC0')
    # FIXME: J_il8 and JMP_l8 assume the caller will do the appropriate
    # calculation to find the displacement, but J_il does it for the caller.
    # We need to be consistent.
    JMP_l8 = insn('\xEB', immediate(1, 'b'))
    J_il8 = insn(immediate(1, 'o'), '\x70', immediate(2, 'b'))
    J_il = insn('\x0F', immediate(1,'o'), '\x80', relative(2))

    SET_ir = insn(rex_w, '\x0F', immediate(1,'o'),'\x90', byte_register(2), '\xC0')

    # The 64-bit version of this, CQO, is defined in X86_64_CodeBuilder
    CDQ = insn(rex_nw, '\x99')

    TEST8_mi = insn(rex_nw, '\xF6', orbyte(0<<3), mem_reg_plus_const(1), immediate(2, 'b'))
    TEST8_ji = insn(rex_nw, '\xF6', orbyte(0<<3), abs_, immediate(1), immediate(2, 'b'))
    TEST_rr = insn(rex_w, '\x85', register(2,8), register(1), '\xC0')

    # x87 instructions
    FSTP_b = insn('\xDD', orbyte(3<<3), stack_bp(1))

    # ------------------------------ Random mess -----------------------
    RDTSC = insn('\x0F\x31')

    # reserved as an illegal instruction
    UD2 = insn('\x0F\x0B')

    # ------------------------------ SSE2 ------------------------------

    # Conversion
    CVTSI2SD_xr = xmminsn('\xF2', rex_w, '\x0F\x2A', register(1, 8), register(2), '\xC0')
    CVTSI2SD_xb = xmminsn('\xF2', rex_w, '\x0F\x2A', register(1, 8), stack_bp(2))

    CVTTSD2SI_rx = xmminsn('\xF2', rex_w, '\x0F\x2C', register(1, 8), register(2), '\xC0')
    CVTTSD2SI_rb = xmminsn('\xF2', rex_w, '\x0F\x2C', register(1, 8), stack_bp(2))

    MOVD_rx = xmminsn('\x66', rex_w, '\x0F\x7E', register(2, 8), register(1), '\xC0')
    MOVD_xr = xmminsn('\x66', rex_w, '\x0F\x6E', register(1, 8), register(2), '\xC0')

    PSRAD_xi = xmminsn('\x66', rex_nw, '\x0F\x72', register(1), '\xE0', immediate(2, 'b'))

    # ------------------------------------------------------------

Conditions = {
     'O':  0,
    'NO':  1,
     'C':  2,     'B':  2,   'NAE':  2,
    'NC':  3,    'NB':  3,    'AE':  3,
     'Z':  4,     'E':  4,
    'NZ':  5,    'NE':  5,
                 'BE':  6,    'NA':  6,
                'NBE':  7,     'A':  7,
     'S':  8,
    'NS':  9,
     'P': 10,    'PE': 10,
    'NP': 11,    'PO': 11,
                  'L': 12,   'NGE': 12,
                 'NL': 13,    'GE': 13,
                 'LE': 14,    'NG': 14,
                'NLE': 15,     'G': 15,
}

def invert_condition(cond_num):
    return cond_num ^ 1

class X86_32_CodeBuilder(AbstractX86CodeBuilder):
    WORD = 4

    PMOVMSKB_rx = xmminsn('\x66', rex_nw, '\x0F\xD7', register(1, 8), register(2), '\xC0')

class X86_64_CodeBuilder(AbstractX86CodeBuilder):
    WORD = 8

    def writeimm64(self, imm):
        self.writechar(chr(imm & 0xFF))
        self.writechar(chr((imm >> 8) & 0xFF))
        self.writechar(chr((imm >> 16) & 0xFF))
        self.writechar(chr((imm >> 24) & 0xFF))
        self.writechar(chr((imm >> 32) & 0xFF))
        self.writechar(chr((imm >> 40) & 0xFF))
        self.writechar(chr((imm >> 48) & 0xFF))
        self.writechar(chr((imm >> 56) & 0xFF))

    CQO = insn(rex_w, '\x99')

    # MOV_ri from the parent class is not wrong, but here is a better encoding
    # for the common case where the immediate fits in 32 bits
    MOV_ri32 = insn(rex_w, '\xC7', register(1), '\xC0', immediate(2, 'i'))
    MOV_ri64 = AbstractX86CodeBuilder.MOV_ri

    def MOV_ri(self, reg, immed):
        if fits_in_32bits(immed):
            self.MOV_ri32(reg, immed)
        else:
            AbstractX86CodeBuilder.MOV_ri(self, reg, immed)

def define_modrm_modes(insnname_template, before_modrm, after_modrm=[], regtype='GPR'):
    def add_insn(code, *modrm):
        args = before_modrm + list(modrm) + after_modrm
        methname = insnname_template.replace('*', code)
        if methname.endswith('_rr') or methname.endswith('_xx'):
            args.append('\xC0')

        if regtype == 'XMM':
            insn_func = xmminsn(*args)
        else:
            insn_func = insn(*args)

        if not hasattr(AbstractX86CodeBuilder, methname):
            setattr(AbstractX86CodeBuilder, methname, insn_func)

    modrm_argnum = insnname_template.split('_')[1].index('*')+1

    if regtype == 'GPR':
        add_insn('r', register(modrm_argnum))
    elif regtype == 'BYTE':
        add_insn('r', byte_register(modrm_argnum))
    elif regtype == 'XMM':
        add_insn('x', register(modrm_argnum))
    else:
        raise AssertionError("Invalid type")

    add_insn('b', stack_bp(modrm_argnum))
    add_insn('s', stack_sp(modrm_argnum))
    add_insn('m', mem_reg_plus_const(modrm_argnum))
    add_insn('a', mem_reg_plus_scaled_reg_plus_const(modrm_argnum))
    add_insn('j', abs_, immediate(modrm_argnum))

# Define a regular MOV, and a variant MOV32 that only uses the low 4 bytes of a
# register
for insnname, rex_type in [('MOV', rex_w), ('MOV32', rex_nw)]:
    define_modrm_modes(insnname + '_*r', [rex_type, '\x89', register(2, 8)])
    define_modrm_modes(insnname + '_r*', [rex_type, '\x8B', register(1, 8)])
    define_modrm_modes(insnname + '_*i', [rex_type, '\xC7', orbyte(0<<3)], [immediate(2)])

define_modrm_modes('MOV8_*r', [rex_fw, '\x88', byte_register(2, 8)], regtype='BYTE')
define_modrm_modes('MOV8_*i', [rex_fw, '\xC6', orbyte(0<<3)], [immediate(2, 'b')], regtype='BYTE')

define_modrm_modes('MOVZX8_r*', [rex_w, '\x0F\xB6', register(1, 8)], regtype='BYTE')
define_modrm_modes('MOVSX8_r*', [rex_w, '\x0F\xBE', register(1, 8)], regtype='BYTE')
define_modrm_modes('MOVZX16_r*', [rex_w, '\x0F\xB7', register(1, 8)])
define_modrm_modes('MOVSX16_r*', [rex_w, '\x0F\xBF', register(1, 8)])
define_modrm_modes('MOVSX32_r*', [rex_w, '\x63', register(1, 8)])

define_modrm_modes('MOVSD_x*', ['\xF2', rex_nw, '\x0F\x10', register(1,8)], regtype='XMM')
define_modrm_modes('MOVSD_*x', ['\xF2', rex_nw, '\x0F\x11', register(2,8)], regtype='XMM')

#define_modrm_modes('XCHG_r*', [rex_w, '\x87', register(1, 8)])

define_modrm_modes('ADDSD_x*', ['\xF2', rex_nw, '\x0F\x58', register(1, 8)], regtype='XMM')
define_modrm_modes('SUBSD_x*', ['\xF2', rex_nw, '\x0F\x5C', register(1, 8)], regtype='XMM')
define_modrm_modes('MULSD_x*', ['\xF2', rex_nw, '\x0F\x59', register(1, 8)], regtype='XMM')
define_modrm_modes('DIVSD_x*', ['\xF2', rex_nw, '\x0F\x5E', register(1, 8)], regtype='XMM')
define_modrm_modes('UCOMISD_x*', ['\x66', rex_nw, '\x0F\x2E', register(1, 8)], regtype='XMM')
define_modrm_modes('XORPD_x*', ['\x66', rex_nw, '\x0F\x57', register(1, 8)], regtype='XMM')
define_modrm_modes('ANDPD_x*', ['\x66', rex_nw, '\x0F\x54', register(1, 8)], regtype='XMM')

def define_pxmm_insn(insnname_template, insn_char):
    def add_insn(char, *post):
        methname = insnname_template.replace('*', char)
        insn_func = xmminsn('\x66', rex_nw, '\x0F' + insn_char,
                            register(1, 8), *post)
        assert not hasattr(AbstractX86CodeBuilder, methname)
        setattr(AbstractX86CodeBuilder, methname, insn_func)
    #
    assert insnname_template.count('*') == 1
    add_insn('x', register(2), '\xC0')
    add_insn('j', abs_, immediate(2))

define_pxmm_insn('PADDQ_x*',     '\xD4')
define_pxmm_insn('PSUBQ_x*',     '\xFB')
define_pxmm_insn('PAND_x*',      '\xDB')
define_pxmm_insn('POR_x*',       '\xEB')
define_pxmm_insn('PXOR_x*',      '\xEF')
define_pxmm_insn('PUNPCKLDQ_x*', '\x62')
define_pxmm_insn('PCMPEQD_x*',   '\x76')

# ____________________________________________________________

_classes = (AbstractX86CodeBuilder, X86_64_CodeBuilder, X86_32_CodeBuilder)

# Used to build the MachineCodeBlockWrapper
all_instructions = sorted(name for cls in _classes for name in cls.__dict__
                          if name.split('_')[0].isupper())

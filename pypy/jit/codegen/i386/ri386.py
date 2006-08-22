

class OPERAND(object):
    pass

class REG(OPERAND):
    width = 4

class REG8(OPERAND):
    width = 1

class EAX(REG): op=0
class ECX(REG): op=1
class EDX(REG): op=2
class EBX(REG): op=3
class ESP(REG): op=4
class EBP(REG): op=5
class ESI(REG): op=6
class EDI(REG): op=7

class AL(REG8): op=0
class CL(REG8): op=1
class DL(REG8): op=2
class BL(REG8): op=3
class AH(REG8): op=4
class CH(REG8): op=5
class DH(REG8): op=6
class BH(REG8): op=7

class IMM32(OPERAND):
    def __init__(self, value):
        self.value = value

class IMM8(IMM32):
    pass

class IMM16(OPERAND):  # only for RET
    def __init__(self, value):
        self.value = value

class MODRM(OPERAND):
    def __init__(self, byte, extradata):
        self.byte = byte
        self.extradata = extradata

class MODRM8(MODRM):
    pass

class REL32(OPERAND):
    def __init__(self, absolute_target):
        self.absolute_target = absolute_target

class MISSING(OPERAND):
    pass

# ____________________________________________________________
# Public interface: the concrete operands to instructions
# 
# NB.: UPPERCASE names represent classes of operands (the same
#      instruction can have multiple modes, depending on these
#      classes), while lowercase names are concrete operands.


eax = EAX()
ecx = ECX()
edx = EDX()
ebx = EBX()
esp = ESP()
ebp = EBP()
esi = ESI()
edi = EDI()

al = AL()
cl = CL()
dl = DL()
bl = BL()
ah = AH()
ch = CH()
dh = DH()
bh = BH()

imm32 = IMM32
imm8 = IMM8
imm16 = IMM16
rel32 = REL32

def memregister(register):
    assert register.width == 4
    return MODRM(0xC0 | register.op, '')

def mem(basereg, offset=0):
    return memSIB(basereg, None, 0, offset)

def memSIB(base, index, scaleshift, offset):
    return _SIBencode(MODRM, base, index, scaleshift, offset)

def memregister8(register):
    assert register.width == 1
    return MODRM8(0xC0 | register.op, '')

def mem8(basereg, offset=0):
    return memSIB8(basereg, None, 0, offset)

def memSIB8(base, index, scaleshift, offset):
    return _SIBencode(MODRM8, base, index, scaleshift, offset)

def _SIBencode(cls, base, index, scaleshift, offset):
    assert base is None or isinstance(base, REG)
    assert index is None or (isinstance(index, REG) and index is not esp)
    assert 0<=scaleshift<4

    if base is None:
        if index is None:
            return cls(0x05, packimm32(offset))
        if scaleshift > 0:
            return cls(0x04, chr((scaleshift<<6) | (index.op<<3) | 0x05) +
                               packimm32(offset))
        base = index
        index = None

    if index is not None:
        SIB = chr((scaleshift<<6) | (index.op<<3) | base.op)
    elif base is esp:
        SIB = '\x24'
    elif offset == 0 and base is not ebp:
        return cls(base.op, '')
    elif single_byte(offset):
        return cls(0x40 | base.op, packimm8(offset))
    else:
        return cls(0x80 | base.op, packimm32(offset))

    if offset == 0 and base is not ebp:
        return cls(0x04, SIB)
    elif single_byte(offset):
        return cls(0x44, SIB + packimm8(offset))
    else:
        return cls(0x84, SIB + packimm32(offset))

def single_byte(value):
    return -128 <= value < 128

def packimm32(i):
    return (chr(i & 0xFF) +
            chr((i >> 8) & 0xFF) +
            chr((i >> 16) & 0xFF) +
            chr((i >> 24) & 0xFF))

def packimm8(i):
    if i < 0:
        i += 256
    return chr(i)

def packimm16(i):
    return (chr(i & 0xFF) +
            chr((i >> 8) & 0xFF))

missing = MISSING()

# __________________________________________________________
# Abstract base class, with methods like NOP(), ADD(x, y), etc.

class AbstractCodeBuilder(object):

    def write(self, data):
        raise NotImplementedError

    def tell(self):
        raise NotImplementedError


import ri386setup  # side-effect: add methods to AbstractCodeBuilder

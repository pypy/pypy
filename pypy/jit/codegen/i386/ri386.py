from pypy.rlib.rarithmetic import intmask


class OPERAND(object):
    _attrs_ = []
    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.assembler())

class REG(OPERAND):
    width = 4
    def __repr__(self):
        return '<%s>' % self.__class__.__name__.lower()
    def assembler(self):
        return '%' + self.__class__.__name__.lower()
    def lowest8bits(self):
        if self.op < 4:
            return registers8[self.op]
        else:
            raise ValueError

class REG8(OPERAND):
    width = 1
    def __repr__(self):
        return '<%s>' % self.__class__.__name__.lower()
    def assembler(self):
        return '%' + self.__class__.__name__.lower()

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
    width = 4
    value = 0      # annotator hack

    def __init__(self, value):
        self.value = value
    def assembler(self):
        return '$%d' % (self.value,)

    def lowest8bits(self):
        val = self.value & 0xFF
        if val > 0x7F:
            val -= 0x100
        return IMM8(val)

class IMM8(IMM32):
    width = 1

class IMM16(OPERAND):  # only for RET
    width = 2
    value = 0      # annotator hack

    def __init__(self, value):
        self.value = value
    def assembler(self):
        return '$%d' % (self.value,)

class MODRM(OPERAND):
    width = 4

    def __init__(self, byte, extradata):
        self.byte = byte
        self.extradata = extradata

    def lowest8bits(self):
        return MODRM8(self.byte, self.extradata)

    def assembler(self):
        mod = self.byte & 0xC0
        rm  = self.byte & 0x07
        if mod == 0xC0:
            return registers[rm].assembler()
        if self.byte == 0x05:
            return '%d' % (unpack(self.extradata),)
        if mod == 0x00:
            offset_bytes = 0
        elif mod == 0x40:
            offset_bytes = 1
        else:
            offset_bytes = 4
        if rm == 4:
            SIB = ord(self.extradata[0])
            scale = (SIB & 0xC0) >> 6
            index = (SIB & 0x38) >> 3
            base  = (SIB & 0x07)
            if base == 5 and mod == 0x00:
                offset_bytes = 4
                basename = ''
            else:
                basename = registers[base].assembler()
            if index == 4:
                # no index
                s = '(%s)' % (basename,)
            else:
                indexname = registers[index].assembler()
                s = '(%s,%s,%d)' % (basename, indexname, 1 << scale)
            offset = self.extradata[1:]
        else:
            s = '(%s)' % (registers[rm].assembler(),)
            offset = self.extradata

        assert len(offset) == offset_bytes
        if offset_bytes > 0:
            s = '%d%s' % (unpack(offset), s)
        return s

    def is_register(self):
        mod = self.byte & 0xC0
        return mod == 0xC0

    def ofs_relative_to_ebp(self):
        # very custom: if self is a mem(ebp, ofs) then return ofs
        # otherwise raise ValueError
        mod = self.byte & 0xC0
        rm  = self.byte & 0x07
        if mod == 0xC0:
            raise ValueError     # self is just a register
        if self.byte == 0x05:
            raise ValueError     # self is just an [immediate]
        if rm != 5:
            raise ValueError     # not a simple [ebp+ofs]
        offset = self.extradata
        if not offset:
            return 0
        else:
            return unpack(offset)

    def is_relative_to_ebp(self):
        try:
            self.ofs_relative_to_ebp()
        except ValueError:
            return False
        else:
            return True

    def involves_ecx(self):
        # very custom: is ecx present in this mod/rm?
        mod = self.byte & 0xC0
        rm  = self.byte & 0x07
        if mod != 0xC0 and rm == 4:
            SIB = ord(self.extradata[0])
            index = (SIB & 0x38) >> 3
            base  = (SIB & 0x07)
            return base == ECX.op or index == ECX.op
        else:
            return rm == ECX.op


class MODRM8(MODRM):
    width = 1

class REL32(OPERAND):
    width = 4
    def __init__(self, absolute_target):
        self.absolute_target = absolute_target
    def assembler(self):
        return '%d' % (self.absolute_target,)

class MISSING(OPERAND):
    def __repr__(self):
        return '<MISSING>'

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

registers = [eax, ecx, edx, ebx, esp, ebp, esi, edi]
registers8 = [al, cl, dl, bl, ah, ch, dh, bh]

for r in registers + registers8:
    r.bitmask = 1 << r.op
del r

imm32 = IMM32
imm8 = IMM8
imm16 = IMM16
rel32 = REL32

def imm(value):
    if single_byte(value):
        return imm8(value)
    else:
        return imm32(value)

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

def fixedsize_ebp_ofs(offset):
    return MODRM(0x80 | EBP.op, packimm32(offset))

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

def unpack(s):
    assert len(s) in (1, 2, 4)
    if len(s) == 1:
        a = ord(s[0])
        if a > 0x7f:
            a -= 0x100
    else:
        a = ord(s[0]) | (ord(s[1]) << 8)
        if len(s) == 2:
            if a > 0x7fff:
                a -= 0x10000
        else:
            a |= (ord(s[2]) << 16) | (ord(s[3]) << 24)
            a = intmask(a)
    return a

missing = MISSING()

# __________________________________________________________
# Abstract base class, with methods like NOP(), ADD(x, y), etc.

class I386CodeBuilder(object):

    def write(self, data):
        raise NotImplementedError

    def tell(self):
        raise NotImplementedError


import ri386setup  # side-effect: add methods to I386CodeBuilder

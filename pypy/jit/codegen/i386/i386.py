import struct
from types import StringType, IntType


# Registers
EAX = 0
ECX = 1
EDX = 2
EBX = 3
ESP = 4
EBP = 5
ESI = 6
EDI = 7

AL = 8
CL = 9
DL = 10
BL = 11
AH = 12
CH = 13
DH = 14
BH = 15

REG    = -1
MODRM  = -2
IMM32  = -3
REG8   = -4
MODRM8 = -5
IMM8   = -6
IMM16  = -7  # for 'RET immed16' only
REL8   = -8
REL32  = -9


class operand:
    pass

class orbyte(operand):

    def __init__(self, value):
        self.value = value

    def eval(self, s):
        s.i_orbyte |= self.value


class fixed(operand):
    
    def __init__(self, cte):
        self.cte = cte

    def eval(self, s):
        s.i_write(self.cte)


class soperand(operand):

    def __init__(self, op, width='i'):
        self.op = op
        self.width = width

    def specialize(self, mode):
        return []


class register(soperand):

    def __init__(self, op, factor=1, width='i'):
        self.op = op
        self.factor = factor
        self.width = width

    def eval(self, s):
        reg = s.i_table[self.op]
        assert 0<=reg<8
        s.i_orbyte |= reg * self.factor

    def specialize(self, mode):
        if self.width == 'i':
            return [(reg, [orbyte(reg * self.factor)]) for reg in range(8)]
        else:
            return [(reg+8, [orbyte(reg * self.factor)]) for reg in range(8)]


class modrm(soperand):

    def eval(self, s):
        memoryfn, args = s.i_table[self.op]
        memoryfn(s, *args)

    def specialize(self, mode):
        if self.width == 'i':
            return [(REG, [register(self.op, 1, 'i'), '\xC0'])]
        else:
            return [(REG8, [register(self.op, 1, 'b'), '\xC0'])]


class immediate(soperand):

    def __init__(self, op, width='i', relative=None):
        self.op = op
        self.width = width
        self.relative = relative

    def eval(self, s):
        assert not s.i_orbyte
        s.writeimmediate(s.i_table[self.op], self.width, self.relative)

    def specialize(self, mode):
        if mode == IMM32:
            return [(IMM8, [self])]
        if mode == REL32:
            assert self.relative is None and self.width=='i'
            return [(REL8, [self]),
                    (IMM32, [immediate(self.op, self.width, 4)])]
        return []


def memRegister(s, register):
    s.i_write(chr(0xC0 | (register & 7)))

def memBase(s, base, offset):
    memSIB(s, base, None, 0, offset)
##    if base == ESP:
##        return memSIB(ESP, 4, 0, offset)   # 4 == <no index>
##    if offset==0 and base!=EBP:
##        return chr(base)
##    elif -128 <= offset < 128:
##        return chr(0x40 | base) + struct.pack('b', offset)
##    else:
##        return chr(0x80 | base) + struct.pack('i', offset)

def memSIB(s, base, index, scale, offset):
    assert base is None or 0<=base<8
    assert index is None or (index != ESP and 0<=index<8)
    assert 0<=scale<4
    if base is None:
        if index is None:
            s.i_write('\x05')
            s.writeimmediate(offset)
            return
        if scale>0:
            s.i_write('\x04' + chr((scale<<6) | (index<<3) | 0x05))
            s.writeimmediate(offset)
            return
        base = index
        index = None
    if index is None:
        if base==ESP:
            SIB = '\x24'
        elif offset==0 and base!=EBP:
            s.i_write(chr(base))
            return
        elif single_byte(offset):
            s.i_write(chr(0x40 | base))
            s.writeimmediate(offset, 'b')
            return
        else:
            s.i_write(chr(0x80 | base))
            s.writeimmediate(offset, 'i')
            return
    else:
        SIB = chr((scale<<6) | (index<<3) | base)
    if offset==0 and base!=EBP:
        s.i_write('\x04' + SIB)
    elif single_byte(offset):
        s.i_write('\x44' + SIB)
        s.writeimmediate(offset, 'b')
    else:
        s.i_write('\x84' + SIB)
        s.writeimmediate(offset, 'i')

##def memSIBfar(reg, (base, index, scale)):
##    assert 0<=base<8
##    assert 0<=index<8
##    assert 0<=scale<4
##    SIB = chr((scale<<6) | (index<<3) | base)
##    return '\x84' + SIB

def single_byte(value):
    return type(value) is IntType and -128 <= value < 128

def sub32(x, y):
    "x-y computed using the processor's wrap-around 32-bit arithmetic."
    z = (long(x) - y) & 0xFFFFFFFFL
    if z >= 0x80000000L:
        z -= 0x100000000L
    return int(z)


def consolidate(code1):
    for i in range(len(code1)-1, 0, -1):
        curop = code1[i]
        prevop = code1[i-1]
        if type(curop) is StringType:
            if not curop:
                del code1[i]
                continue
            if type(prevop) is StringType:
                code1[i-1] = prevop + curop
                del code1[i]
                continue
            if isinstance(prevop, orbyte):
                code1[i-1] = chr(prevop.value | ord(curop[0])) + curop[1:]
                del code1[i]
                continue
        elif isinstance(curop, orbyte):
            if not curop.value:
                del code1[i]
                continue
            if isinstance(prevop, orbyte):
                code1[i-1] = orbyte(curop.value | prevop.value)
                del code1[i]
                continue


class Instruction:
    #Error = "no such encoding"
    indirect = 0
    as_all_suffixes = 0
    as_alias = None
    
    def __init__(self):
        #self.modes = []
        self.encodings = { }

    def getopcodes(self, *ops):
        table = {}
        mlist = []
        for i in range(len(ops)):
            m, table[i+1] = ops[i]
            mlist.append(m)
        #try:
        return self.encodings[tuple(mlist)], table
        #except KeyError:
        #    if not self.modes:
        #        raise self.Error, tuple(mlist)
        #    self.nextmode()
        #    return self.getopcodes(*ops)

    def encode(self, s, *ops):
        def i_write(data, s=s):
            if data:
                if s.i_orbyte:
                    data = chr(ord(data[0]) | s.i_orbyte) + data[1:]
                    s.i_orbyte = 0
                s.write(data)
        s.i_write = i_write
        s.i_orbyte = 0
        opcodes, s.i_table = self.getopcodes(*ops)
        for op in opcodes:
            if type(op) is StringType:
                i_write(op)
            else:
                op.eval(s)
        assert not s.i_orbyte
        del s.i_orbyte
        del s.i_write
        del s.i_table

    def __repr__(self):
        name = '???'
        for key, value in globals().items():
            if value is self:
                name = key
                break
        return '<%s>' % name

    def mode0(self, code):
        self._mode((), code, 1)

    def mode1(self, m1, code):
        self._mode((m1,), code, 1)

    def mode2(self, m1, m2, code):
        self._mode((m1, m2), code, 1)

    def mode3(self, m1, m2, m3, code):
        self._mode((m1, m2, m3), code, 1)

    def _mode(self, mm, code, nodups):
        if self.encodings.has_key(mm):
            if nodups:
                raise "'mode' calls in wrong order"
            return
        consolidate(code)
        self.encodings[mm] = code
        for i, op in zip(range(len(code)), code):
            if isinstance(op, soperand):
                s1 = op.specialize(mm[op.op-1])
                for smode, scode in s1:
                    scode1 = code[:]
                    scode1[i:i+1] = scode
                    smm = list(mm)
                    smm[op.op-1] = smode
                    self._mode(tuple(smm), scode1, 0)

    #def allencodings(self):
    #    while self.modes:
    #        self.nextmode()
    #    return self.encodings

    def common_modes(self, group):
        base = group * 8
        self.mode2(MODRM, IMM8,  ['\x83', orbyte(group<<3), modrm(1),
                                                            immediate(2,'b')])
        self.mode2(EAX,   IMM32, [chr(base+5), immediate(2)])
        self.mode2(MODRM, IMM32, ['\x81', orbyte(group<<3), modrm(1),
                                                            immediate(2)])
        self.mode2(MODRM, REG,   [chr(base+1), register(2,8), modrm(1)])
        self.mode2(REG,   MODRM, [chr(base+3), register(1,8), modrm(2)])

        self.mode2(AL,    IMM8,  [chr(base+4), immediate(2,'b')])
        self.mode2(MODRM8,IMM8,  ['\x80', orbyte(group<<3), modrm(1,'b'),
                                                            immediate(2,'b')])
        self.mode2(MODRM8,REG8,  [chr(base+0), register(2,8,'b'), modrm(1,'b')])
        self.mode2(REG8,  MODRM8,[chr(base+2), register(1,8,'b'), modrm(2,'b')])


MOV = Instruction()
for e in range(16):
    MOV.mode2(e, e, [])   # 'MOV <register>, <same register>'
del e
#MOV.mode2(EAX,   MEMABS,['\xA1', memabsolute(2)])
#MOV.mode2(MEMABS,EAX,   ['\xA3', memabsolute(1)])
MOV.mode2(REG,   IMM32, [register(1), '\xB8', immediate(2)])
MOV.mode2(MODRM, IMM32, ['\xC7', orbyte(0<<3), modrm(1), immediate(2)])
MOV.mode2(MODRM, REG,   ['\x89', register(2,8), modrm(1)])
MOV.mode2(REG,   MODRM, ['\x8B', register(1,8), modrm(2)])

#MOV.mode2(AL,    MEMABS,['\xA0', memabsolute(2,'b')])
#MOV.mode2(MEMABS,AL,    ['\xA2', memabsolute(1,'b')])
MOV.mode2(REG8,  IMM8,  [register(1,1,'b'), '\xB0', immediate(2,'b')])
MOV.mode2(MODRM8,IMM8,  ['\xC6', orbyte(0<<3), modrm(1,'b'), immediate(2,'b')])
MOV.mode2(MODRM8,REG8,  ['\x88', register(2,8,'b'), modrm(1,'b')])
MOV.mode2(REG8,  MODRM8,['\x8A', register(1,8,'b'), modrm(2,'b')])

ADD = Instruction()
ADD.common_modes(0)

OR = Instruction()
OR.common_modes(1)

ADC = Instruction()
ADC.common_modes(2)

SBB = Instruction()
SBB.common_modes(3)

AND = Instruction()
AND.common_modes(4)

SUB = Instruction()
SUB.common_modes(5)

XOR = Instruction()
XOR.common_modes(6)

CMP = Instruction()
CMP.common_modes(7)

NOP = Instruction()
NOP.mode0(['\x90'])

RET = Instruction()
RET.mode0(['\xC3'])
RET.mode1(IMM16, ['\xC2', immediate(1,'h')])

CALL = Instruction()
CALL.mode1(REL32, ['\xE8', immediate(1)])
CALL.mode1(MODRM, ['\xFF', orbyte(2<<3), modrm(1)])
CALL.indirect = 1

JMP = Instruction()
JMP.mode1(REL8,  ['\xEB', immediate(1,'b')])
JMP.mode1(REL32, ['\xE9', immediate(1)])
JMP.mode1(MODRM, ['\xFF', orbyte(4<<3), modrm(1)])
JMP.indirect = 1

PUSH = Instruction()
PUSH.mode1(IMM8,  ['\x6A', immediate(1,'b')])
PUSH.mode1(IMM32, ['\x68', immediate(1)])
PUSH.mode1(REG,   [register(1), '\x50'])
PUSH.mode1(MODRM, ['\xFF', orbyte(6<<3), modrm(1)])

PUSHF = Instruction()
PUSHF.mode0(['\x9C'])

POP = Instruction()
POP.mode1(REG,   [register(1), '\x58'])
POP.mode1(MODRM, ['\x8F', orbyte(0<<3), modrm(1)])

POPF = Instruction()
POPF.mode0(['\x9D'])

IMUL = Instruction()
IMUL.mode1(MODRM,  ['\xF7', orbyte(5<<3), modrm(1)])
IMUL.mode1(MODRM8, ['\xF6', orbyte(5<<3), modrm(1)])
IMUL.mode3(REG, MODRM, IMM8, ['\x6B', register(1,8), modrm(2), immediate(3,'b')])
IMUL.mode3(REG, MODRM, IMM32,['\x69', register(1,8), modrm(2), immediate(3)])
IMUL.mode2(REG, IMM8,  ['\x6B', register(1,9), '\xC0', immediate(2,'b')])
IMUL.mode2(REG, IMM32, ['\x69', register(1,9), '\xC0', immediate(2)])
IMUL.mode2(REG, MODRM, ['\x0F\xAF', register(1,8), modrm(2)])

MOVSX = Instruction()
MOVSX.mode2(REG, MODRM8, ['\x0F\xBE', register(1,8), modrm(2,'b')])
MOVSX.as_all_suffixes = 1
MOVSX.as_alias = "MOVS"

MOVZX = Instruction()
MOVZX.mode2(REG, MODRM8, ['\x0F\xB6', register(1,8), modrm(2,'b')])
MOVZX.as_all_suffixes = 1
MOVZX.as_alias = "MOVZ"

INC = Instruction()
INC.mode1(REG,   [register(1), '\x40'])
INC.mode1(MODRM, ['\xFF', orbyte(0<<3), modrm(1)])
INC.mode1(MODRM8,['\xFE', orbyte(0<<3), modrm(1,'b')])

DEC = Instruction()
DEC.mode1(REG,   [register(1), '\x48'])
DEC.mode1(MODRM, ['\xFF', orbyte(1<<3), modrm(1)])
DEC.mode1(MODRM8,['\xFE', orbyte(1<<3), modrm(1,'b')])

XCHG = Instruction()
XCHG.mode2(EAX,    REG,  [register(2), '\x90'])
XCHG.mode2(REG,    EAX,  [register(1), '\x90'])
XCHG.mode2(MODRM,  REG,  ['\x87', register(2,8), modrm(1)])
XCHG.mode2(REG,  MODRM,  ['\x87', register(1,8), modrm(2)])
XCHG.mode2(MODRM8, REG8, ['\x86', register(2,8,'b'), modrm(1,'b')])
XCHG.mode2(REG8, MODRM8, ['\x86', register(1,8,'b'), modrm(2,'b')])

LEA = Instruction()
LEA.mode2(REG, MODRM, ['\x8D', register(1,8), modrm(2)])
for key in LEA.encodings.keys():
    if key[1] != MODRM:
        del LEA.encodings[key]

SHL = Instruction()
SHL.mode2(MODRM,  IMM8,  ['\xC1', orbyte(4<<3), modrm(1), immediate(2,'b')])
SHL.mode2(MODRM,  CL,    ['\xD3', orbyte(4<<3), modrm(1)])

SHR = Instruction()
SHR.mode2(MODRM,  IMM8,  ['\xC1', orbyte(5<<3), modrm(1), immediate(2,'b')])
SHR.mode2(MODRM,  CL,    ['\xD3', orbyte(5<<3), modrm(1)])

SAR = Instruction()
SAR.mode2(MODRM,  IMM8,  ['\xC1', orbyte(7<<3), modrm(1), immediate(2,'b')])
SAR.mode2(MODRM,  CL,    ['\xD3', orbyte(7<<3), modrm(1)])

TEST = Instruction()
TEST.mode2(REG,   MODRM, ['\x85', register(1,8), modrm(2)])
TEST.mode2(MODRM, REG,   ['\x85', register(2,8), modrm(1)])
TEST.mode2(EAX,   IMM32, ['\xA9', immediate(2)])
TEST.mode2(MODRM, IMM32, ['\xF7', orbyte(0<<3), modrm(1), immediate(2)])


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

def define_cond(prefix, indirect, modes, code):
    idx = code.index(None)
    for key, value in Conditions.items():
        name = prefix + key
        instr = globals().setdefault(name, Instruction())
        code1 = code[:]
        code1[idx] = orbyte(value)
        instr._mode(modes, code1, 1)
        instr.indirect = indirect

define_cond('J',   1, (REL8,),   [None,'\x70', immediate(1,'b')])
define_cond('J',   1, (REL32,),  ['\x0F', None,'\x80', immediate(1)])
define_cond('SET', 0, (MODRM8,), ['\x0F', None,'\x90',orbyte(0<<3),modrm(1,'b')])
define_cond('CMOV',0,(REG,MODRM),['\x0F', None,'\x40', register(1,8), modrm(2)])
# note: CMOVxx are Pentium-class instructions, unknown to the 386 and 486


all_instructions = {}
for key, value in globals().items():
    if isinstance(value, Instruction):
        all_instructions[key] = value

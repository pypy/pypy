"""
List of i386 instructions.
This module contains the logic to set up the I386CodeBuilder multimethods.
Not for direct importing.
"""
from ri386 import *

from pypy.objspace.std.multimethod import MultiMethodTable, InstallerVersion2
from pypy.tool.sourcetools import compile2

def reg2modrm(builder, reg):
    return memregister(reg)

def reg2modrm64(builder, reg):
    return memregister64(reg)

def reg2modrm8(builder, reg):
    return memregister8(reg)

type_order = {
    EAX: [(EAX, None), (REG, None), (MODRM, reg2modrm)],
    ECX: [(ECX, None), (REG, None), (MODRM, reg2modrm)],
    EDX: [(EDX, None), (REG, None), (MODRM, reg2modrm)],
    EBX: [(EBX, None), (REG, None), (MODRM, reg2modrm)],
    ESP: [(ESP, None), (REG, None), (MODRM, reg2modrm)],
    EBP: [(EBP, None), (REG, None), (MODRM, reg2modrm)],
    ESI: [(ESI, None), (REG, None), (MODRM, reg2modrm)],
    EDI: [(EDI, None), (REG, None), (MODRM, reg2modrm)],

    AL: [(AL, None), (REG8, None), (MODRM8, reg2modrm8)],
    CL: [(CL, None), (REG8, None), (MODRM8, reg2modrm8)],
    DL: [(DL, None), (REG8, None), (MODRM8, reg2modrm8)],
    BL: [(BL, None), (REG8, None), (MODRM8, reg2modrm8)],
    AH: [(AH, None), (REG8, None), (MODRM8, reg2modrm8)],
    CH: [(CH, None), (REG8, None), (MODRM8, reg2modrm8)],
    DH: [(DH, None), (REG8, None), (MODRM8, reg2modrm8)],
    BH: [(BH, None), (REG8, None), (MODRM8, reg2modrm8)],

    REG:  [(REG,  None), (MODRM,  reg2modrm)],
    REG8: [(REG8, None), (MODRM8, reg2modrm8)],

    IMM32: [(IMM32, None)],
    IMM16: [(IMM16, None)],      # only for RET
    IMM8:  [(IMM8,  None), (IMM32, None)],

    REL32: [(REL32, None)],

    MODRM:   [(MODRM,  None)],
    MODRM8:  [(MODRM8, None)],
    MODRM64: [(MODRM64, None)],
    XMMREG:  [(XMMREG, None), (MODRM64, reg2modrm64)],

    MISSING: [(MISSING, None)],  # missing operands
    }


class operand:
    def __init__(self, op, width='i'):
        self.op = op
        self.width = width

class orbyte(operand):
    def __init__(self, value):
        self.value = value
    def eval(self, lines, has_orbyte):
        if has_orbyte:
            lines.append('orbyte |= %d' % self.value)
        else:
            lines.append('orbyte = %d' % self.value)
        return True

class register(operand):
    def __init__(self, op, factor=1, width='i'):
        self.op = op
        self.factor = factor
        self.width = width
    def eval(self, lines, has_orbyte):
        value = 'arg%d.op' % self.op
        if self.factor != 1:
            value = '%s * %d' % (value, self.factor)
        if has_orbyte:
            lines.append('orbyte |= %s' % value)
        else:
            lines.append('orbyte = %s' % value)
        return True

class modrm(operand):
    def eval(self, lines, has_orbyte):
        expr = 'arg%d.byte' % self.op
        if has_orbyte:
            expr = 'orbyte | %s' % expr
        lines.append('builder.writechr(%s)' % expr)
        lines.append('builder.write(arg%d.extradata)' % self.op)
        return False

class immediate(operand):
    def eval(self, lines, has_orbyte):
        assert not has_orbyte, "malformed bytecode"
        if self.width == 'i':
            lines.append('builder.write(packimm32(arg%d.value))' % (self.op,))
        elif self.width == 'b':
            lines.append('builder.writechr(arg%d.value & 0xFF)' % (self.op,))
        elif self.width == 'h':
            lines.append('builder.write(packimm16(arg%d.value))' % (self.op,))
        else:
            raise AssertionError, "invalid width %r" % (self.width,)
        return False

class relative(operand):
    def eval(self, lines, has_orbyte):
        assert not has_orbyte, "malformed bytecode"
        assert self.width == 'i', "only REL32 supported at the moment"
        lines.append('offset = arg%d.absolute_target - (builder.tell()+4)' % (
            self.op,))
        lines.append('builder.write(packimm32(offset))')
        return False

##class conditioncode(operand):
##    def __init__(self):
##        pass
##    def eval(self, lines, has_orbyte):
##        assert not has_orbyte, "malformed bytecode"
##        lines.append('orbyte = arg1.value')
##        return True


def consolidate(code1):
    for i in range(len(code1)-1, 0, -1):
        curop = code1[i]
        prevop = code1[i-1]
        if isinstance(curop, str):
            if not curop:
                del code1[i]
                continue
            if isinstance(prevop, str):
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

def generate_function(sig, opcodes):
    consolidate(opcodes)
    lines = []
    has_orbyte = False
    for op in opcodes:
        if isinstance(op, str):
            if has_orbyte:
                nextbyte = ord(op[0])
                if nextbyte:
                    lines.append('orbyte |= %d' % nextbyte)
                lines.append('builder.writechr(orbyte)')
                has_orbyte = False
                op = op[1:]
            if op:
                if len(op) > 1:
                    lines.append('builder.write(constlistofchars(%r))' % (op,))
                else:
                    lines.append('builder.writechr(%d)' % (ord(op),))
        else:
            has_orbyte = op.eval(lines, has_orbyte)
    assert not has_orbyte, "malformed bytecode"

    if not lines:
        lines.append('pass')
    args = ', '.join(['builder'] + ['arg%d'%i for i in range(1, len(sig)+1)])
    lines.insert(0, 'def encode(%s):' % args)
    source = '\n    '.join(lines) + '\n'
    miniglobals = {
        'packimm32': packimm32,
        'packimm8': packimm8,
        'packimm16': packimm16,
        'constlistofchars': constlistofchars,
        }
    exec compile2(source) in miniglobals
    return miniglobals['encode']


class Instruction:
    indirect = 0
    as_all_suffixes = 0
    as_alias = None
    name = '???'     # initialized by setup()

    def __init__(self):
        self.modes = {}

    def setup(self, name):
        self.name = name
        arity = max([len(mm) for mm in self.modes])
        if arity == 0:
            encoder = generate_function([], self.modes[()])
        else:
            table = MultiMethodTable(arity, root_class=OPERAND,
                                     argnames_before=['builder'])
            for mm, opcodes in self.modes.items():
                sig = list(mm) + [MISSING] * (arity - len(mm))
                for cls in sig:
                    assert issubclass(cls, OPERAND)
                encoder1 = generate_function(sig, opcodes)
                table.register(encoder1, *sig)
            # always use the InstallerVersion2, including for testing,
            # because it produces code that is more sensitive to
            # registration errors
            encoder = table.install('__encode' + name, [type_order] * arity,
                                    installercls = InstallerVersion2)
            mmmin = min([len(mm) for mm in self.modes])
            if mmmin < arity:
                encoder.func_defaults = (missing,) * (arity - mmmin)
        setattr(I386CodeBuilder, name, encoder)

    def __repr__(self):
        return '<%s>' % self.name

    def mode0(self, code):
        self._mode((), code)

    def mode1(self, m1, code):
        self._mode((m1,), code)

    def mode2(self, m1, m2, code):
        self._mode((m1, m2), code)

    def mode3(self, m1, m2, m3, code):
        self._mode((m1, m2, m3), code)

    def _mode(self, mm, code):
        self.modes[mm] = code

    def common_modes(self, group):
        base = group * 8
        self.mode2(EAX,   IMM8,  ['\x83', orbyte(group<<3), '\xC0',
                                                            immediate(2,'b')])
        self.mode2(MODRM, IMM8,  ['\x83', orbyte(group<<3), modrm(1),
                                                            immediate(2,'b')])
        self.mode2(EAX,   IMM32, [chr(base+5), immediate(2)])
        self.mode2(MODRM, IMM32, ['\x81', orbyte(group<<3), modrm(1),
                                                            immediate(2)])
        self.mode2(REG,   REG,   [chr(base+1), register(2,8), register(1,1),
                                  '\xC0'])
        self.mode2(MODRM, REG,   [chr(base+1), register(2,8), modrm(1)])
        self.mode2(REG,   MODRM, [chr(base+3), register(1,8), modrm(2)])

        self.mode2(AL,    IMM8,  [chr(base+4), immediate(2,'b')])
        self.mode2(MODRM8,IMM8,  ['\x80', orbyte(group<<3), modrm(1,'b'),
                                                            immediate(2,'b')])
        self.mode2(REG8,  REG8,  [chr(base+0), register(2,8,'b'),
                                  register(1,1,'b'), '\xC0'])
        self.mode2(MODRM8,REG8,  [chr(base+0), register(2,8,'b'), modrm(1,'b')])
        self.mode2(REG8,  MODRM8,[chr(base+2), register(1,8,'b'), modrm(2,'b')])


MOV = Instruction()
##for e in [EAX, ECX, EDX, EBX, ESP, EBP, ESI, EDI, 
##          AL, CL, DL, BL, AH, CH, DH, BH]:
##    MOV.mode2(e, e, [])   # 'MOV <register>, <same register>'
##del e
#MOV.mode2(EAX,   MEMABS,['\xA1', memabsolute(2)])
#MOV.mode2(MEMABS,EAX,   ['\xA3', memabsolute(1)])
MOV.mode2(REG,   IMM32, [register(1), '\xB8', immediate(2)])
MOV.mode2(MODRM, IMM32, ['\xC7', orbyte(0<<3), modrm(1), immediate(2)])
MOV.mode2(REG,   REG,   ['\x89', register(2,8), register(1), '\xC0'])
MOV.mode2(MODRM, REG,   ['\x89', register(2,8), modrm(1)])
MOV.mode2(REG,   MODRM, ['\x8B', register(1,8), modrm(2)])

#MOV.mode2(AL,    MEMABS,['\xA0', memabsolute(2,'b')])
#MOV.mode2(MEMABS,AL,    ['\xA2', memabsolute(1,'b')])
MOV.mode2(REG8,  IMM8,  [register(1,1,'b'), '\xB0', immediate(2,'b')])
MOV.mode2(MODRM8,IMM8,  ['\xC6', orbyte(0<<3), modrm(1,'b'), immediate(2,'b')])
MOV.mode2(REG8,  REG8,  ['\x88', register(2,8,'b'), register(1,1,'b'), '\xC0'])
MOV.mode2(MODRM8,REG8,  ['\x88', register(2,8,'b'), modrm(1,'b')])
MOV.mode2(REG8,  MODRM8,['\x8A', register(1,8,'b'), modrm(2,'b')])

# special modes for writing 16-bit operands into memory
MOV16 = Instruction()
MOV16.mode2(MODRM, IMM32, ['\x66', '\xC7', orbyte(0<<3), modrm(1),
                           immediate(2,'h')])
MOV16.mode2(MODRM, REG,   ['\x66', '\x89', register(2,8), modrm(1)])

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

# special mode for comparing a 16-bit operand with an immediate
CMP16 = Instruction()
CMP16.mode2(MODRM, IMM32, ['\x66', '\x81', orbyte(7<<3), modrm(1),
                           immediate(2,'h')])

NOP = Instruction()
NOP.mode0(['\x90'])

RET = Instruction()
RET.mode0(['\xC3'])
RET.mode1(IMM16, ['\xC2', immediate(1,'h')])

CALL = Instruction()
CALL.mode1(REL32, ['\xE8', relative(1)])
CALL.mode1(MODRM, ['\xFF', orbyte(2<<3), modrm(1)])
CALL.indirect = 1

JMP = Instruction()
#JMP.mode1(REL8,  ['\xEB', immediate(1,'b')])
JMP.mode1(REL32, ['\xE9', relative(1)])
JMP.mode1(MODRM, ['\xFF', orbyte(4<<3), modrm(1)])
JMP.indirect = 1

PUSH = Instruction()
PUSH.mode1(IMM8,  ['\x6A', immediate(1,'b')])
PUSH.mode1(IMM32, ['\x68', immediate(1)])
PUSH.mode1(REG,   [register(1), '\x50'])
PUSH.mode1(MODRM, ['\xFF', orbyte(6<<3), modrm(1)])

PUSHF = Instruction()
PUSHF.mode0(['\x9C'])

PUSHA = Instruction()
PUSHA.mode0(['\x60'])

POP = Instruction()
POP.mode1(REG,   [register(1), '\x58'])
POP.mode1(MODRM, ['\x8F', orbyte(0<<3), modrm(1)])

POPF = Instruction()
POPF.mode0(['\x9D'])

POPA = Instruction()
POPA.mode0(['\x61'])

IMUL = Instruction()
IMUL.mode1(MODRM,  ['\xF7', orbyte(5<<3), modrm(1)])
IMUL.mode1(MODRM8, ['\xF6', orbyte(5<<3), modrm(1)])
IMUL.mode3(REG, MODRM, IMM8, ['\x6B', register(1,8), modrm(2), immediate(3,'b')])
IMUL.mode3(REG, MODRM, IMM32,['\x69', register(1,8), modrm(2), immediate(3)])
IMUL.mode2(REG, IMM8,  ['\x6B', register(1,9), '\xC0', immediate(2,'b')])
IMUL.mode2(REG, IMM32, ['\x69', register(1,9), '\xC0', immediate(2)])
IMUL.mode2(REG, MODRM, ['\x0F\xAF', register(1,8), modrm(2)])

IDIV = Instruction()
IDIV.mode1(MODRM,  ['\xF7', orbyte(7<<3), modrm(1)])
IDIV.mode1(MODRM8, ['\xF6', orbyte(7<<3), modrm(1)])

MUL = Instruction()
MUL.mode1(MODRM,  ['\xF7', orbyte(4<<3), modrm(1)])
MUL.mode1(MODRM8, ['\xF6', orbyte(4<<3), modrm(1)])

DIV = Instruction()
DIV.mode1(MODRM,  ['\xF7', orbyte(6<<3), modrm(1)])
DIV.mode1(MODRM8, ['\xF6', orbyte(6<<3), modrm(1)])

NEG = Instruction()
NEG.mode1(MODRM,  ['\xF7', orbyte(3<<3), modrm(1)])
NEG.mode1(MODRM8, ['\xF6', orbyte(3<<3), modrm(1)])

NOT = Instruction()
NOT.mode1(MODRM,  ['\xF7', orbyte(2<<3), modrm(1)])
NOT.mode1(MODRM8, ['\xF6', orbyte(2<<3), modrm(1)])

CDQ = Instruction()
CDQ.mode0(['\x99'])

MOVSX = Instruction()
MOVSX.mode2(REG, MODRM8, ['\x0F\xBE', register(1,8), modrm(2,'b')])
MOVSX.as_all_suffixes = 1
MOVSX.as_alias = "MOVS"

MOVZX = Instruction()
MOVZX.mode2(REG, MODRM8, ['\x0F\xB6', register(1,8), modrm(2,'b')])
MOVZX.mode2(REG, MODRM,  ['\x0F\xB7', register(1,8), modrm(2)])
#                ^^^ but this only reads the 16 lower bits of the source
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
XCHG.mode2(REG,    REG,  ['\x87', register(2,8), register(1), '\xC0'])
XCHG.mode2(MODRM,  REG,  ['\x87', register(2,8), modrm(1)])
XCHG.mode2(REG,  MODRM,  ['\x87', register(1,8), modrm(2)])
XCHG.mode2(REG8,   REG8, ['\x86', register(2,8,'b'), register(1,1,'b'),'\xC0'])
XCHG.mode2(MODRM8, REG8, ['\x86', register(2,8,'b'), modrm(1,'b')])
XCHG.mode2(REG8, MODRM8, ['\x86', register(1,8,'b'), modrm(2,'b')])

LEA = Instruction()
LEA.mode2(REG, MODRM,  ['\x8D', register(1,8), modrm(2)])
LEA.mode2(REG, MODRM8, ['\x8D', register(1,8), modrm(2)])
# some cases produce a MODRM8, but the result is always a 32-bit REG
# and the encoding is the same

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
TEST.mode2(AL,    IMM8,  ['\xA8', immediate(2,'b')])
TEST.mode2(MODRM8,IMM8,  ['\xF6', orbyte(0<<3),modrm(1,'b'), immediate(2,'b')])

INT = Instruction()
INT.mode1(IMM8, ['\xCD', immediate(1, 'b')])

INTO = Instruction()
INTO.mode0(['\xCE'])

BREAKPOINT = Instruction()    # INT 3
BREAKPOINT.mode0(['\xCC'])
BREAKPOINT.as_alias = "INT3"

SAHF = Instruction()
SAHF.mode0(['\x9E'])

LODSB = Instruction()
LODSB.mode0(['\xAC'])

LODSD = Instruction()
LODSD.mode0(['\xAD'])
LODSD.as_alias = "LODSL"

# ------------------------- floating point instructions ------------------

FLDL = Instruction()
FLDL.mode1(MODRM64, ['\xDD', modrm(1)])

FADDP = Instruction()
FADDP.mode0(['\xDE\xC1'])

FSUBP = Instruction()
FSUBP.mode0(['\xDE\xE1'])

FMULP = Instruction()
FMULP.mode0(['\xDE\xC9'])

FDIVP = Instruction()
FDIVP.mode0(['\xDE\xF1'])

FCHS = Instruction()
FCHS.mode0(['\xD9\xE0'])

FABS = Instruction()
FABS.mode0(['\xD9\xE1'])

FTST = Instruction()
FTST.mode0(['\xD9\xE4'])

# store status control word
FNSTSW = Instruction()
FNSTSW.mode0(['\xDF\xE0'])

FUCOMP = Instruction()
FUCOMP.mode0(['\xDD\xE9'])

FUCOMPP = Instruction()
FUCOMPP.mode0(['\xDA\xE9'])

FSTP = Instruction()
FSTP.mode1(MODRM64, ['\xDD', orbyte(3<<3), modrm(1)])
FST = Instruction()
FST.mode1(MODRM64, ['\xDD', orbyte(2<<3), modrm(1)])

FISTP = Instruction()
FISTP.mode1(MODRM, ['\xDB', orbyte(3<<3), modrm(1)])

FILD = Instruction()
FILD.mode1(MODRM, ['\xDB', orbyte(0<<3), modrm(1)])

FNSTCW = Instruction()
FNSTCW.mode1(MODRM, ['\xD9', orbyte(7<<3), modrm(1)])

# ------------------------- end of floating point ------------------------

# --------------------------------- SSE2 ---------------------------------

MOVSD = Instruction()
MOVSD.mode2(XMMREG, XMMREG, ['\xF2\x0F\x10', register(1, 8),
                             register(2), '\xC0'])
MOVSD.mode2(XMMREG, MODRM64, ['\xF2\x0F\x10', register(1, 8), modrm(2)])
MOVSD.mode2(MODRM64, XMMREG, ['\xF2\x0F\x11', register(2, 8), modrm(1)])

ADDSD = Instruction()
ADDSD.mode2(XMMREG, MODRM64, ['\xF2\x0F\x58', register(1, 8), modrm(2)])

SUBSD = Instruction()
SUBSD.mode2(XMMREG, MODRM64, ['\xF2\x0F\x5C', register(1, 8), modrm(2)])

MULSD = Instruction()
MULSD.mode2(XMMREG, MODRM64, ['\xF2\x0F\x59', register(1, 8), modrm(2)])

DIVSD = Instruction()
DIVSD.mode2(XMMREG, MODRM64, ['\xF2\x0F\x5E', register(1, 8), modrm(2)])

UCOMISD = Instruction()
UCOMISD.mode2(XMMREG, MODRM64, ['\x66\x0F\x2E', register(1, 8), modrm(2)])

XORPD = Instruction()  # warning: a memory argument must be aligned to 16 bytes
XORPD.mode2(XMMREG, MODRM64, ['\x66\x0f\x57', register(1, 8), modrm(2)])

ANDPD = Instruction()  # warning: a memory argument must be aligned to 16 bytes
ANDPD.mode2(XMMREG, MODRM64, ['\x66\x0F\x54', register(1, 8), modrm(2)])

CVTTSD2SI = Instruction()
CVTTSD2SI.mode2(REG, XMMREG, ['\xF2\x0F\x2C', register(1, 8), register(2),
                             '\xC0'])

CVTSI2SD = Instruction()
CVTSI2SD.mode2(XMMREG, MODRM, ['\xF2\x0F\x2A', register(1, 8), modrm(2)])

# ------------------------------ end of SSE2 -----------------------------

UD2 = Instruction()      # reserved as an illegal instruction
UD2.mode0(['\x0F\x0B'])


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
        instr._mode(modes, code1)
        instr.indirect = indirect

#define_cond('J',   1, (REL8,),   [None,'\x70', immediate(1,'b')])
define_cond('J',   1, (REL32,),  ['\x0F', None,'\x80', relative(1)])
define_cond('SET', 0, (MODRM8,), ['\x0F', None,'\x90',orbyte(0<<3),modrm(1,'b')])
define_cond('CMOV',0,(REG,MODRM),['\x0F', None,'\x40', register(1,8), modrm(2)])
# note: CMOVxx are Pentium-class instructions, unknown to the 386 and 486

##Jcond = Instruction()
##Jcond.mode2(  IMM8, REL32,     ['\x0F', conditioncode(),'\x80', relative(2)])

##SETcond = Instruction()
##SETcond.mode2(IMM8, MODRM8,    ['\x0F', conditioncode(),'\x90', orbyte(0<<3),
##                                                                modrm(2,'b')])

##CMOVcond = Instruction()
##CMOVcond.mode3(IMM8,REG,MODRM, ['\x0F', conditioncode(),'\x40', register(2,8),
##                                                                modrm(3)])


all_instructions = {}
for key, value in globals().items():
    if isinstance(value, Instruction):
        value.setup(key)
        all_instructions[key] = value

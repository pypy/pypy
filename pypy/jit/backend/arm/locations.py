from pypy.jit.metainterp.history import INT, FLOAT, REF
from pypy.jit.backend.arm.arch import WORD
class AssemblerLocation(object):
    _immutable_ = True
    type = INT

    def is_imm(self):
        return False

    def is_stack(self):
        return False

    def is_reg(self):
        return False

    def is_vfp_reg(self):
        return False

    def is_imm_float(self):
        return False

    def as_key(self):
        raise NotImplementedError

class RegisterLocation(AssemblerLocation):
    _immutable_ = True
    width = WORD

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return 'r%d' % self.value

    def is_reg(self):
        return True

    def as_key(self):
        return self.value

class VFPRegisterLocation(RegisterLocation):
    _immutable_ = True
    type = FLOAT 
    width = 2*WORD

    def get_single_precision_regs(self):
        return [VFPRegisterLocation(i) for i in [self.value*2, self.value*2+1]]

    def __repr__(self):
        return 'vfp%d' % self.value

    def is_reg(self):
        return False

    def is_vfp_reg(self):
        return True

    def as_key(self):
        return self.value + 20

class ImmLocation(AssemblerLocation):
    _immutable_ = True
    width = WORD


    def __init__(self, value):
        self.value = value

    def getint(self):
        return self.value

    def __repr__(self):
        return "imm(%d)" % (self.value)

    def is_imm(self):
        return True

    def as_key(self):
        return self.value + 40

class ConstFloatLoc(AssemblerLocation):
    """This class represents an imm float value which is stored in memory at
    the address stored in the field value"""
    _immutable_ = True
    width = 2*WORD
    type = FLOAT

    def __init__(self, value):
        self.value = value

    def getint(self):
        return self.value

    def __repr__(self):
        return "imm_float(stored at %d)" % (self.value)

    def is_imm_float(self):
        return True

    def as_key(self):
        return -1 * self.value

class StackLocation(AssemblerLocation):
    _immutable_ = True

    def __init__(self, position, num_words=1, type=INT):
        self.position = position
        self.width = num_words * WORD
        self.type = type

    def __repr__(self):
        return 'FP(%s)+%d' % (self.type, self.position,)

    def location_code(self):
        return 'b'

    def assembler(self):
        return repr(self)

    def is_stack(self):
        return True

    def as_key(self):
        return -self.position

def imm(i):
    return ImmLocation(i)

from pypy.jit.metainterp.history import INT, FLOAT, REF
import sys

# XXX import from arch.py, currently we have a circular import
if sys.maxint == (2**31 - 1):
    WORD = 4
else:
    WORD = 8
DWORD = 2 * WORD

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

class FPRegisterLocation(RegisterLocation):
    _immutable_ = True
    type = FLOAT 
    width = DWORD

    def __repr__(self):
        return 'fp%d' % self.value

    def is_reg(self):
        return False

    def is_fp_reg(self):
        return True

    def as_key(self):
        return self.value

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

class StackLocation(AssemblerLocation):
    _immutable_ = True

    def __init__(self, position, num_words=1, type=INT):
        self.position = position
        self.type = type
        self.value = get_spp_offset(position)

    def __repr__(self):
        return 'SPP(%s)+%d' % (self.type, self.value)

    def location_code(self):
        return 'b'

    def assembler(self):
        return repr(self)

    def is_stack(self):
        return True

    def as_key(self):
        return -self.position

def imm(val):
    return ImmLocation(val)

def get_spp_offset(pos):
    return -(pos + 1) * WORD

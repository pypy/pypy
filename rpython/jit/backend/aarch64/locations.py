
from rpython.jit.backend.aarch64.arch import WORD, JITFRAME_FIXED_SIZE
from rpython.jit.metainterp.history import INT, FLOAT

class AssemblerLocation(object):
    _immutable_ = True
    type = INT

    def is_imm(self):
        return False

    def is_stack(self):
        return False

    def is_raw_sp(self):
        return False

    def is_core_reg(self):
        return False

    def is_vfp_reg(self):
        return False

    def is_imm_float(self):
        return False

    def is_float(self):
        return False

    def as_key(self):
        raise NotImplementedError

    def get_position(self):
        raise NotImplementedError # only for stack

class RegisterLocation(AssemblerLocation):
    _immutable_ = True

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return 'x%d' % self.value

    def is_core_reg(self):
        return True

    def as_key(self):       # 0 <= as_key <= 30, 31 being zero register
        xxx
        return self.value

class VFPRegisterLocation(RegisterLocation):
    _immutable_ = True
    type = FLOAT

    def __repr__(self):
        return 'vfp(d%d)' % self.value

    def is_core_reg(self):
        return False

    def is_vfp_reg(self):
        return True

    def as_key(self):            # 40 <= as_key <= 71
        xxx
        return self.value + 40

    def is_float(self):
        return True

class ImmLocation(AssemblerLocation):
    _immutable_ = True

    def __init__(self, value):
        self.value = value

    def getint(self):
        return self.value

    def __repr__(self):
        return "imm(%d)" % (self.value)

    def is_imm(self):
        return True

class StackLocation(AssemblerLocation):
    _immutable_ = True

    def __init__(self, position, fp_offset, type=INT):
        self.position = position
        self.value = fp_offset
        self.type = type

    def __repr__(self):
        return 'FP(%s)+%d' % (self.type, self.position,)

    def location_code(self):
        return 'b'

    def get_position(self):
        return self.position

    def assembler(self):
        return repr(self)

    def is_stack(self):
        return True

    def as_key(self):                # an aligned word + 10000
        XXX
        return self.position + 10000

    def is_float(self):
        return self.type == FLOAT


class ZeroRegister(AssemblerLocation):
    _immutable_ = True

    def __init__(self):
        self.value = 31

    def __repr__(self):
        return "xzr"

    def as_key(self):
        return 31

def get_fp_offset(base_ofs, position):
    return base_ofs + WORD * (position + JITFRAME_FIXED_SIZE)

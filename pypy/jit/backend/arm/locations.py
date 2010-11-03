from pypy.jit.metainterp.history import INT
from pypy.jit.backend.arm.arch import WORD
class AssemblerLocation(object):
    pass
    def is_imm(self):
        return False

    def is_stack(self):
        return False

    def is_reg(self):
        return False

class RegisterLocation(AssemblerLocation):

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return 'r%d' % self.value

    def is_reg(self):
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
    def __init__(self, position, num_words=1, type=INT):
        self.position = position
        self.width = num_words * WORD
        # One of INT, REF, FLOAT
        assert num_words == 1
        assert type == INT
        #self.type = type

    def frame_size(self):
        return self.width // WORD

    def __repr__(self):
        return 'SP+%d' % (self.position,)

    def location_code(self):
        return 'b'

    def assembler(self):
        return repr(self)

    def is_stack(self):
        return True

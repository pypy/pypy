class AssemblerLocation(object):
    pass
    def is_imm(self):
        return False

class RegisterLocation(AssemblerLocation):

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return 'r%d' % self.value

class ImmLocation(AssemblerLocation):
    _immutable_ = True
    def __init__(self, value):
        self.value = value

    def getint(self):
        return self.value

    def __repr__(self):
        return "ImmedLoc(%d)" % (self.value)

    def is_imm(self):
        return True

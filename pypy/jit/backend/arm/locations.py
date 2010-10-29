class AssemblerLocation(object):
    pass

class RegisterLocation(AssemblerLocation):

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return 'r%d' % self.value

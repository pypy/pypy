class AssemblerLocation(object):
    pass

class RegisterLocation(AssemblerLocation):

    def __init__(self, value):
        self.value = value

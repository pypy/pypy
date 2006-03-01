class Clone: pass

class Inject(object):

    def __init__(self, constraint):
        self.constraint = constraint

class Revise(object):

    def __init__(self, var):
        self.var = var

    def __eq__(self, other):
        if not isinstance(other, Revise): return False
        return self.var == other.var

    

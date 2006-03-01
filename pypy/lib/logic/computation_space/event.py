class NewSpace: pass

class Clone: pass

class Revise(object):

    def __init__(self, var):
        self.var = var

    def __eq__(self, other):
        if not isinstance(other, Revise): return False
        return self.var == other.var

    

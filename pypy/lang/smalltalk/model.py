
class W_Object:
    def __init__(self, w_class):
        self.w_class = w_class

class W_NamedVarsObject(W_Object):
    def __init__(self, w_class):
        W_Object.__init__(self, w_class)
        self.named_vars = [None] * w_class.namedvarssize

    def getnamedvar(self, index):
        return self.named_vars[index]

    def setnamedvar(self, index, w_value):
        self.named_vars[index] = w_value


NO_INDEXED   = 0
OBJ_INDEXED  = 1
BYTE_INDEXED = 2
WORD_INDEXED = 3

class W_Class(W_Object):
    def __init__(self, w_class, w_superclass, namedvarssize=0,
                 indexed=NO_INDEXED):
        W_Object.__init__(self, w_class)
        self.w_superclass = w_superclass
        self.methoddict = {}
        self.namedvarssize = namedvarssize
        self.indexed = indexed

    def new(self):
        if self.indexed == NO_INDEXED:
            return W_NamedVarsObject(self)
        else:
            raise NotImplementedError(self.indexed)

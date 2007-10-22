
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

class W_IndexedNamedVarsObject(W_NamedVarsObject):
    def __init__(self, w_class, size):
        W_NamedVarsObject.__init__(self, w_class)
        self.indexed_vars = [None] * size

    def getindexedvar(self, index):
        return self.indexed_vars[index]

    def setindexedvar(self, index, w_value):
        self.indexed_vars[index] = w_value

# ____________________________________________________________ 

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

    def new(self, size=0):
        if self.indexed == NO_INDEXED:
            assert size == 0
            return W_NamedVarsObject(self)
        elif self.indexed == OBJ_INDEXED:
            return W_IndexedNamedVarsObject(self, size)
        else:
            raise NotImplementedError(self.indexed)

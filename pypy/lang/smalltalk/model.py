
class W_Object:
    def __init__(self, w_class):
        self.w_class = w_class
        
    def size(self):
        return 0
        
    def instvarsize(self):
        return self.w_class.instvarsize        

class W_SmallInteger(W_Object):
    def __init__(self, w_class, value):
        W_Object.__init__(self, w_class)
        self.value = value

class W_Float(W_Object):
    def __init__(self, w_class, value):
        W_Object.__init__(self, w_class)
        self.value = value

class W_PointersObject(W_Object):
    """ The normal object """
    def __init__(self, w_class, size=0):
        W_Object.__init__(self, w_class)
        self.named_vars = [None] * w_class.instvarsize
        self.indexed_vars = [None] * size

    def getnamedvar(self, index):
        return self.named_vars[index]

    def setnamedvar(self, index, w_value):
        self.named_vars[index] = w_value

    def size(self):
        return len(self.indexed_vars)
        
    def getindexedvar(self, index):
        return self.indexed_vars[index]

    def setindexedvar(self, index, w_value):
        self.indexed_vars[index] = w_value

class W_BytesObject(W_Object):
    def __init__(self, w_class, size):
        W_Object.__init__(self, w_class)
        self.bytes = ['\x00'] * size
        
    def getbyte(self, n):
        return ord(self.bytes[n])
        
    def setbyte(self, n, byte):
        self.bytes[n] = chr(byte)

    def size(self):
        return len(self.bytes)    

class W_WordsObject(W_Object):
    def __init__(self, w_class, size):
        W_Object.__init__(self, w_class)
        self.words = [0] * size
        
    def getword(self, n):
        return self.words[n]
        
    def setword(self, n, word):
        self.words[n] = word        

    def size(self):
        return len(self.words)    

class W_CompiledMethod(W_Object):
    def __init__(self, w_class, size,
                 bytes="", argsize=0, tempsize=0, primitive=0):
        W_Object.__init__(self, w_class)
        self.literals = [None] * size
        self.bytes = bytes
        self.argsize = argsize
        self.tempsize = tempsize
        self.primitive = primitive

    def createFrame(self, receiver, arguments, sender = None):
        from pypy.lang.smalltalk.interpreter import W_ContextFrame
        assert len(arguments) == self.argsize
        return W_ContextFrame(None, self, receiver, arguments, sender)

# ____________________________________________________________ 

POINTERS = 0
VAR_POINTERS = 1
BYTES = 2
WORDS = 3
WEAK_POINTERS = 4

class W_Class(W_Object):
    def __init__(self, w_class, w_superclass, instvarsize=0,
                 format=POINTERS, name="?"):
        W_Object.__init__(self, w_class)
        self.name = name
        self.w_superclass = w_superclass
        self.methoddict = {}
        self.instvarsize = instvarsize
        self.format = format

    def isindexable(self):
        return self.format in (VAR_POINTERS, WORDS, BYTES)

    def ismetaclass(self):
        return False

    def new(self, size=0):
        if self.format == POINTERS:
            assert size == 0
            return W_PointersObject(self)
        elif self.format == VAR_POINTERS:
            return W_PointersObject(w_class=self, size=size)
        elif self.format == WORDS:
            return W_WordsObject(w_class=self, size=size)
        elif self.format == BYTES:
            return W_BytesObject(w_class=self, size=size)
        else:
            raise NotImplementedError(self.format)

    def __repr__(self):
        return "W_Class(%s)" % self.name

    def lookup(self, selector):
        if selector in self.methoddict:
            return self.methoddict[selector]
        elif self.w_superclass != None:
            return self.w_superclass.lookup(selector)
        else:
            return None

class W_MetaClass(W_Class):
    def ismetaclass(self):
        return True

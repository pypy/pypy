
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
    """My instances are methods suitable for interpretation by the virtual machine.  This is the only class in the system whose instances intermix both indexable pointer fields and indexable integer fields.


    The current format of a CompiledMethod is as follows:

    	header (4 bytes)
    	literals (4 bytes each)
    	bytecodes  (variable)
    	trailer (variable)

    The header is a 30-bit integer with the following format:

    (index 0)	9 bits:	main part of primitive number   (#primitive)
    (index 9)	8 bits:	number of literals (#numLiterals)
    (index 17)	1 bit:	whether a large frame size is needed (#frameSize)
    (index 18)	6 bits:	number of temporary variables (#numTemps)
    (index 24)	4 bits:	number of arguments to the method (#numArgs)
    (index 28)	1 bit:	high-bit of primitive number (#primitive)
    (index 29)	1 bit:	flag bit, ignored by the VM  (#flag)


    The trailer has two variant formats.  In the first variant, the last byte is at least 252 and the last four bytes represent a source pointer into one of the sources files (see #sourcePointer).  In the second variant, the last byte is less than 252, and the last several bytes are a compressed version of the names of the method's temporary variables.  The number of bytes used for this purpose is the value of the last byte in the method.
    """
    def __init__(self, w_class, size, bytes="", argsize=0, 
                 tempsize=0, primitive=0, w_compiledin=None):
        W_Object.__init__(self, w_class)
        self.literals = [None] * size
        self.w_compiledin = w_compiledin
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

    def installmethod(self, selector, method):
        self.methoddict[selector] = method
        method.w_compiledin = self

class W_MetaClass(W_Class):
    def ismetaclass(self):
        return True

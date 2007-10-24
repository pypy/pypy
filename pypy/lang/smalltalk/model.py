
class W_Object(object):

    def size(self):
        return 0

    def getclassmirror(self):
        raise NotImplementedError

    def gethash(self):
        raise NotImplementedError

    def invariant(self):
        return True

class W_SmallInteger(W_Object):
    def __init__(self, value):
        self.value = value

    def getclassmirror(self):
        from pypy.lang.smalltalk.classtable import m_SmallInteger
        return m_SmallInteger

    def gethash(self):
        return self.value    # XXX check this

    def invariant(self):
        return isinstance(self.value, int)

class W_Float(W_Object):
    def __init__(self, value):
        self.value = value

    def getclassmirror(self):
        from pypy.lang.smalltalk.classtable import m_Float
        return m_Float

    def gethash(self):
        return XXX    # check this

    def invariant(self):
        return self.value is not None        # XXX but later:
        #return isinstance(self.value, float)

class W_ObjectWithStoredClass(W_Object):
    """ The base class of objects that store 'm_class' explicitly. """
    def __init__(self, m_class):
        self.m_class = m_class
        self.hash = 42             # XXX

    def getclassmirror(self):
        return self.m_class

    def gethash(self):
        return self.hash

    def invariant(self):
        from pypy.lang.smalltalk.mirror import ClassMirror
        return (isinstance(self.m_class, ClassMirror) and
                1)#isinstance(self.hash, int)) XXX

class W_PointersObject(W_ObjectWithStoredClass):
    """ The normal object """
    def __init__(self, m_class, size):
        W_ObjectWithStoredClass.__init__(self, m_class)
        self.vars = [None] * size

    def fetch(self, index):
        return self.vars[index]
        
    def store(self, index, w_value):    
        self.vars[index] = w_value

    def size(self):
        return len(self.vars)

    def invariant(self):
        return (W_ObjectWithStoredClass.invariant(self) and
                isinstance(self.vars, list))

class W_BytesObject(W_ObjectWithStoredClass):
    def __init__(self, m_class, size):
        W_ObjectWithStoredClass.__init__(self, m_class)
        self.bytes = ['\x00'] * size
        
    def getbyte(self, n):
        return ord(self.bytes[n])
        
    def setbyte(self, n, byte):
        self.bytes[n] = chr(byte)

    def size(self):
        return len(self.bytes)    

    def invariant(self):
        if not W_ObjectWithStoredClass.invariant(self):
            return False
        for c in self.bytes:
            if not isinstance(c, str) or len(c) != 1:
                return False
        return True

class W_WordsObject(W_ObjectWithStoredClass):
    def __init__(self, m_class, size):
        W_ObjectWithStoredClass.__init__(self, m_class)
        self.words = [0] * size
        
    def getword(self, n):
        return self.words[n]
        
    def setword(self, n, word):
        self.words[n] = word        

    def size(self):
        return len(self.words)   

    def invariant(self):
        return (W_ObjectWithStoredClass.invariant(self) and
                isinstance(self.words, list))

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
    def __init__(self, size, bytes, argsize=0, 
                 tempsize=0, primitive=0, m_compiledin=None):
        self.literals = [None] * size
        self.m_compiledin = m_compiledin
        self.bytes = bytes
        self.argsize = argsize
        self.tempsize = tempsize
        self.primitive = primitive

    def getclassmirror(self):
        from pypy.lang.smalltalk.classtable import m_CompiledMethod
        return m_CompiledMethod

    def gethash(self):
        return 43     # XXX

    def createFrame(self, receiver, arguments, sender = None):
        from pypy.lang.smalltalk.interpreter import W_MethodContext
        assert len(arguments) == self.argsize
        return W_MethodContext(self, receiver, arguments, sender)

    def invariant(self):
        return (W_Object.invariant(self) and
                hasattr(self, 'literals') and
                self.literals is not None and 
                hasattr(self, 'bytes') and
                self.bytes is not None and 
                hasattr(self, 'argsize') and
                self.argsize is not None and 
                hasattr(self, 'tempsize') and
                self.tempsize is not None and 
                hasattr(self, 'primitive') and
                self.primitive is not None)       

import sys
from pypy.rlib import rrandom
from pypy.rlib.rarithmetic import intmask
from pypy.lang.smalltalk import constants

class MethodNotFound(Exception):
    pass

class W_Object(object):

    def size(self):
        return 0

    def getclass(self):
        raise NotImplementedError

    def gethash(self):
        raise NotImplementedError

    def invariant(self):
        return True

    def shadow_of_my_class(self):
        return self.getclass().as_class_get_shadow()

class W_SmallInteger(W_Object):
    def __init__(self, value):
        self.value = value

    def getclass(self):
        from pypy.lang.smalltalk.classtable import w_SmallInteger
        return w_SmallInteger

    def gethash(self):
        return self.value

    def invariant(self):
        return isinstance(self.value, int)

    def __repr__(self):
        return "W_SmallInteger(%d)" % self.value

class W_Float(W_Object):
    def __init__(self, value):
        self.value = value

    def getclass(self):
        from pypy.lang.smalltalk.classtable import w_Float
        return w_Float

    def gethash(self):
        return XXX    # check this

    def invariant(self):
        return self.value is not None        # XXX but later:
        #return isinstance(self.value, float)
    def __repr__(self):
        return "W_Float(%f)" % self.value

class W_AbstractObjectWithIdentityHash(W_Object):
    #XXX maybe this is too extreme, but it's very random
    hash_generator = rrandom.Random()
    UNASSIGNED_HASH = sys.maxint

    hash = UNASSIGNED_HASH # default value

    def gethash(self):
        if self.hash == self.UNASSIGNED_HASH:
            self.hash = hash = intmask(self.hash_generator.genrand32()) // 2
            return hash
        return self.hash

    def invariant(self):
        return isinstance(self.hash, int)

class W_AbstractObjectWithClassReference(W_AbstractObjectWithIdentityHash):
    """ The base class of objects that store 'w_class' explicitly. """

    def __init__(self, w_class):
        if w_class is not None:     # it's None only for testing
            assert isinstance(w_class, W_PointersObject)
        self.w_class = w_class

    def getclass(self):
        return self.w_class

    def __str__(self):
        # XXX use the shadow of my class
        if self.size() >= 9:
            return ''.join(self.fetch(constants.CLASS_NAME_INDEX).bytes) + " class"
        else:
            return "a " + ''.join(self.getclass().fetch(constants.CLASS_NAME_INDEX).bytes)

    def invariant(self):
        return (W_AbstractObjectWithIdentityHash.invariant(self) and
                isinstance(self.w_class, W_PointersObject))


class W_PointersObject(W_AbstractObjectWithClassReference):
    """ The normal object """
    def __init__(self, w_class, size):
        W_AbstractObjectWithClassReference.__init__(self, w_class)
        self._vars = [None] * size
        self._shadow = None

    def fetch(self, index):
        return self._vars[index]
        
    def store(self, index, w_value):    
        if self._shadow is not None:
            self._shadow.invalidate()
        self._vars[index] = w_value

    def size(self):
        return len(self._vars)

    def invariant(self):
        return (W_AbstractObjectWithClassReference.invariant(self) and
                isinstance(self._vars, list))

    def as_class_get_shadow(self):
        from pypy.lang.smalltalk.shadow import ClassShadow
        shadow = self._shadow
        if shadow is None:
            self._shadow = shadow = ClassShadow(self)
        assert isinstance(shadow, ClassShadow)      # for now, the only kind
        shadow.check_for_updates()
        return shadow

    def compiledmethodnamed(self, methodname):
        # XXX kill me.  Temporary, for testing
        w_methoddict = self.fetch(constants.CLASS_METHODDICT_INDEX)._vars
        names  = w_methoddict[constants.METHODDICT_NAMES_INDEX:]
        values = w_methoddict[constants.METHODDICT_VALUES_INDEX]._vars
        for var in names:
            if isinstance(var, W_BytesObject):
                if str(var) == repr(methodname):
                    return values[names.index(var)]
        raise MethodNotFound

    def lookup(self, methodname):
        # XXX kill me.  Temporary, for testing
        from pypy.lang.smalltalk import objtable
        in_class = self
        while in_class != None:
            try:
                return in_class.compiledmethodnamed(methodname)
            except MethodNotFound:
                # Current hack because we don't have a ref to the real
                # nil yet... XXX XXX XXX
                try:
                    new_class = in_class._vars[constants.CLASS_SUPERCLASS_INDEX]
                    if new_class is objtable.w_nil:
                        raise IndexError
                    else:
                        in_class = new_class
                except IndexError:
                    return self.lookup("doesNotUnderstand")

class W_BytesObject(W_AbstractObjectWithClassReference):
    def __init__(self, w_class, size):
        W_AbstractObjectWithClassReference.__init__(self, w_class)
        self.bytes = ['\x00'] * size
        
    def getbyte(self, n):
        return ord(self.bytes[n])
        
    def setbyte(self, n, byte):
        self.bytes[n] = chr(byte)

    def size(self):
        return len(self.bytes)    

    def __str__(self):
        return repr("".join(self.bytes))

    def invariant(self):
        if not W_AbstractObjectWithClassReference.invariant(self):
            return False
        for c in self.bytes:
            if not isinstance(c, str) or len(c) != 1:
                return False
        return True

class W_WordsObject(W_AbstractObjectWithClassReference):
    def __init__(self, w_class, size):
        W_AbstractObjectWithClassReference.__init__(self, w_class)
        self.words = [0] * size
        
    def getword(self, n):
        return self.words[n]
        
    def setword(self, n, word):
        self.words[n] = word        

    def size(self):
        return len(self.words)   

    def invariant(self):
        return (W_AbstractObjectWithClassReference.invariant(self) and
                isinstance(self.words, list))

class W_CompiledMethod(W_AbstractObjectWithIdentityHash):
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
    def __init__(self, literalsize, bytes, argsize=0, 
                 tempsize=0, primitive=0, w_compiledin=None):
        self.literals = [None] * literalsize
        self.w_compiledin = w_compiledin
        self.bytes = bytes
        self.argsize = argsize
        self.tempsize = tempsize
        self.primitive = primitive

    def getclass(self):
        from pypy.lang.smalltalk.classtable import w_CompiledMethod
        return w_CompiledMethod

    def getliteral(self, index):
        return self.literals[index + 1] # header of compiledmethod at index 0

    def createFrame(self, receiver, arguments, sender = None):
        from pypy.lang.smalltalk.interpreter import W_MethodContext
        assert len(arguments) == self.argsize
        return W_MethodContext(self, receiver, arguments, sender)

    def __str__(self):
        from pypy.lang.smalltalk.interpreter import BYTECODE_TABLE
        return ("\n\nBytecode:\n---------------------\n" +
                "\n".join([BYTECODE_TABLE[ord(i)].__name__ + " " + str(ord(i)) for i in self.bytes]) +
                "\n---------------------\n")

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

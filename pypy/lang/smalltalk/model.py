import sys
from pypy.rlib import rrandom
from pypy.rlib.rarithmetic import intmask
from pypy.lang.smalltalk import constants
from pypy.tool.pairtype import extendabletype

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
    
def unwrap_int(w_value):
    if isinstance(w_value, W_SmallInteger):
        return w_value.value
    raise ClassShadowError("expected a W_SmallInteger, got %s" % (w_value,))

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

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self)

    def __str__(self):
        if isinstance(self, W_PointersObject) and self._shadow is not None:
            return "%s class" % (self.as_class_get_shadow().name or '?',)
        else:
            return "a %s" % (self.shadow_of_my_class().name or '?',)

    def invariant(self):
        return (W_AbstractObjectWithIdentityHash.invariant(self) and
                isinstance(self.w_class, W_PointersObject))


class W_PointersObject(W_AbstractObjectWithClassReference):
    """ The normal object """
    
    _shadow = None # Default value

    def __init__(self, w_class, size):
        W_AbstractObjectWithClassReference.__init__(self, w_class)
        self._vars = [None] * size

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
        return self.as_string()

    def __repr__(self):
        return "<W_BytesObject %r>" % (self.as_string(),)

    def as_string(self):
        return "".join(self.bytes)

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

class W_ContextPart(W_AbstractObjectWithIdentityHash):

    __metaclass__ = extendabletype
    
    def __init__(self, w_home, w_sender):
        self.stack = []
        self.pc = 0
        assert isinstance(w_home, W_MethodContext)
        self.w_home = w_home
        self.w_sender = w_sender
        
    def getclass(self):
        from pypy.lang.smalltalk.classtable import w_ContextPart
        return w_ContextPart

    # ______________________________________________________________________
    # Imitate the primitive accessors
    
    def fetch(self, index):
        if index == CTXPART_SENDER_INDEX:
            return self.w_sender
        elif index == CTXPART_PC_INDEX:
            return objtable.wrap_int(self.pc)
        elif index == CTXPART_STACKP_INDEX:
            return objtable.wrap_int(len(self.stack))
        
        # Invalid!
        raise IllegalFetchError

    # ______________________________________________________________________
    # Method that contains the bytecode for this method/block context
    
    def w_method(self):
        return self.w_home._w_method

    def getByte(self):
        bytecode = self.w_method().bytes[self.pc]
        currentBytecode = ord(bytecode)
        self.pc = self.pc + 1
        return currentBytecode

    def getNextBytecode(self):
        self.currentBytecode = self.getByte()
        return self.currentBytecode

    # ______________________________________________________________________
    # Temporary Variables
    #
    # Are always fetched relative to the home method context.
    
    def gettemp(self, index):
        return self.w_home.temps[index]

    def settemp(self, index, w_value):
        self.w_home.temps[index] = w_value

    # ______________________________________________________________________
    # Stack Manipulation

    def pop(self):
        return self.stack.pop()

    def push(self, w_v):
        self.stack.append(w_v)

    def push_all(self, lst):
        " Equivalent to 'for x in lst: self.push(x)' where x is a lst "
        self.stack += lst

    def top(self):
        return self.peek(0)
        
    def peek(self, idx):
        return self.stack[-(idx+1)]

    def pop_n(self, n):
        res = self.stack[len(self.stack)-n:]
        self.stack = self.stack[:len(self.stack)-n]
        return res
    
class W_BlockContext(W_ContextPart):

    def __init__(self, w_home, w_sender, argcnt, initialip):
        W_ContextPart.__init__(self, w_home, w_sender)
        self.argcnt = argcnt
        self.initialip = initialip

    def expected_argument_count(self):
        return self.argcnt
        
    def getclass(self):
        from pypy.lang.smalltalk.classtable import w_BlockContext
        return w_BlockContext
    
    def fetch(self, index):
        if index == BLKCTX_BLOCK_ARGUMENT_COUNT_INDEX:
            return objtable.wrap_int(self.argcnt)
        elif index == BLKCTX_INITIAL_IP_INDEX:
            return objtable.wrap_int(self.initialip)
        elif index == BLKCTX_HOME_INDEX:
            return self.w_home
        elif index >= BLKCTX_TEMP_FRAME_START:
            stack_index = len(self.stack) - index - 1
            return self.stack[stack_index]
        else:
            return W_ContextPart.fetch(index)

    def store(self, index, value):
        if index == BLKCTX_BLOCK_ARGUMENT_COUNT_INDEX:
            self.argcnt = unwrap_int(self.argcnt)
        elif index == BLKCTX_INITIAL_IP_INDEX:
            self.pc = unwrap_int(self.argcnt)
        elif index == BLKCTX_HOME_INDEX:
            self.w_home = value
        elif index >= BLKCTX_TEMP_FRAME_START:
            stack_index = len(self.stack) - index - 1
            self.stack[stack_index] = value
        else:
            return W_ContextPart.fetch(index)

class W_MethodContext(W_ContextPart):
    def __init__(self, w_method, w_receiver, arguments, w_sender = None):
        W_ContextPart.__init__(self, self, w_sender)
        self._w_method = w_method
        self.w_receiver = w_receiver
        self.temps = arguments + [None] * w_method.tempsize

    def getclass(self):
        from pypy.lang.smalltalk.classtable import w_MethodContext
        return w_MethodContext

    def fetch(self, index):
        if index == MTHDCTX_METHOD:
            return self.w_method()
        elif index == MTHDCTX_RECEIVER_MAP: # what is this thing?
            return objtable.w_nil
        elif index == MTHDCTX_RECEIVER:
            return self.w_receiver
        elif index >= MTHDCTX_TEMP_FRAME_START:
            # First set of indices are temporary variables:
            offset = index - MTHDCTX_TEMP_FRAME_START
            if offset < len(self.temps):
                return self.temps[offset]

            # After that comes the stack:
            offset -= len(self.temps)
            stack_index = len(self.stack) - offset - 1
            return self.stack[stack_index]
        else:
            return W_ContextPart.fetch(index)


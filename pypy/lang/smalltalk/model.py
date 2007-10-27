import sys
from pypy.rlib import rrandom
from pypy.rlib.rarithmetic import intmask
from pypy.lang.smalltalk import constants
from pypy.tool.pairtype import extendabletype
from pypy.rlib.objectmodel import instantiate

class W_Object(object):
    __slots__ = ()    # no RPython-level instance variables allowed in W_Object

    def size(self):
        return 0

    def varsize(self):
        return self.size()

    def getclass(self):
        raise NotImplementedError

    def gethash(self):
        raise NotImplementedError

    def invariant(self):
        return True

    def shadow_of_my_class(self):
        return self.getclass().as_class_get_shadow()

    def shallow_equals(self,other):
        return self == other

    def equals(self, other):
        return self.shallow_equals(other)

class W_SmallInteger(W_Object):
    __slots__ = ('value',)     # the only allowed slot here

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

    def shallow_equals(self, other):
        if not isinstance(other, W_SmallInteger):
            return False
        return self.value == other.value

class UnwrappingError(Exception):
    pass

def unwrap_int(w_value):
    if isinstance(w_value, W_SmallInteger):
        return w_value.value
    raise UnwrappingError("expected a W_SmallInteger, got %s" % (w_value,))

class W_Float(W_Object):
    def __init__(self, value):
        self.value = value

    def getclass(self):
        from pypy.lang.smalltalk.classtable import w_Float
        return w_Float

    def gethash(self):
        return 41    # XXX check this

    def invariant(self):
        return self.value is not None        # XXX but later:
        #return isinstance(self.value, float)
    def __repr__(self):
        return "W_Float(%f)" % self.value

    def shallow_equals(self, other):
        if not isinstance(other, W_Float):
            return False
        return self.value == other.value

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
        self._vars = [w_nil] * size

    def at0(self, index0):
        return self.fetchvarpointer(index0)

    def atput0(self, index0, w_value):
        self.storevarpointer(index0, w_value)

    def fetch(self, n0):
        return self._vars[n0]
        
    def store(self, n0, w_value):    
        if self._shadow is not None:
            self._shadow.invalidate()
        self._vars[n0] = w_value

    def fetchvarpointer(self, idx):
        return self._vars[idx+self.instsize()]

    def storevarpointer(self, idx, value):
        self._vars[idx+self.instsize()] = value

    def varsize(self):
        return self.size() - self.shadow_of_my_class().instsize()

    def instsize(self):
        return self.getclass().as_class_get_shadow().instsize()

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

    def equals(self, other):
        if not isinstance(other, W_PointersObject):
            return False
        if not other.getclass() == self.getclass():
            return False
        if not other.size() == self.size():
            return False
        for i in range(self.size()):
            if not other.fetch(i).shallow_equals(self.fetch(i)):
                return False
        return True

class W_BytesObject(W_AbstractObjectWithClassReference):
    def __init__(self, w_class, size):
        W_AbstractObjectWithClassReference.__init__(self, w_class)
        self.bytes = ['\x00'] * size

    def at0(self, index0):
        from pypy.lang.smalltalk import objtable
        return objtable.wrap_int(self.getbyte(index0))
       
    def atput0(self, index0, w_value):
        self.setbyte(index0, unwrap_int(w_value))

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

    def shallow_equals(self, other):
        if not isinstance(other,W_BytesObject):
            return False
        return self.bytes == other.bytes

class W_WordsObject(W_AbstractObjectWithClassReference):
    def __init__(self, w_class, size):
        W_AbstractObjectWithClassReference.__init__(self, w_class)
        self.words = [0] * size
        
    def at0(self, index0):
        from pypy.lang.smalltalk import objtable
        return objtable.wrap_int(self.getword(index0))
       
    def atput0(self, index0, w_value):
        self.setword(index0, unwrap_int(w_value))

    def getword(self, n):
        return self.words[n]
        
    def setword(self, n, word):
        self.words[n] = word        

    def size(self):
        return len(self.words)   

    def invariant(self):
        return (W_AbstractObjectWithClassReference.invariant(self) and
                isinstance(self.words, list))

    def shallow_equals(self, other):
        if not isinstance(other,W_WordsObject):
            return False
        return self.words == other.words

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

    def __init__(self, literalsize, bytes=[], argsize=0, 
                 tempsize=0, primitive=0, w_compiledin=None):
        self.literals = [None] * literalsize
        self.w_compiledin = w_compiledin
        self.bytes = bytes
        self.argsize = argsize
        self.tempsize = tempsize
        self.primitive = primitive

    def compiledin(self):
        if self.w_compiledin is None:
            # Last of the literals is an association with compiledin
            # as a class
            association = self.literals[-1]
            assert isinstance(association, W_PointersObject)
            self.w_compiledin = association.fetch(constants.ASSOCIATION_VALUE_INDEX)
        return self.w_compiledin

    def getclass(self):
        from pypy.lang.smalltalk.classtable import w_CompiledMethod
        return w_CompiledMethod

    def getliteral(self, index):
        return self.literals[index + constants.LITERAL_START]

    def getliteralsymbol(self, index):
        w_literal = self.getliteral(index)
        assert isinstance(w_literal, W_BytesObject)
        return w_literal.as_string()    # XXX performance issue here

    def create_frame(self, receiver, arguments, sender = None):
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

    def size(self):
        return self.varsize()

    def staticsize(self):
        return len(self.literals) * constants.BYTES_PER_WORD

    def varsize(self):
        # XXX
        return  self.staticsize() + len(self.bytes)

    def at0(self, index0):
        # XXX
        from pypy.lang.smalltalk import objtable
        index0 = index0 - self.staticsize()
        if index0 < 0:
            # XXX Do something useful with this.... we are not a block
            # of memory as smalltalk expects but wrapped in py-os
            return objtable.wrap_int(0)
        return objtable.wrap_int(ord(self.bytes[index0]))
        
    def atput0(self, index0, w_value):
        index0 = index0 - self.staticsize()
        if index0 < 0:
            # XXX Do something useful with this.... we are not a block
            # of memory as smalltalk expects but wrapped in py-os
            self.staticsize(),w_value)
        else:
            self.setbyte(index0, chr(unwrap_int(w_value)))

    def setbyte(self, index0, chr):
        self.bytes[index0] = chr

class W_ContextPart(W_AbstractObjectWithIdentityHash):

    __metaclass__ = extendabletype
    
    def __init__(self, w_home, w_sender):
        self.stack = []
        self.pc = 0
        assert isinstance(w_home, W_MethodContext)
        self.w_home = w_home
        self.w_sender = w_sender

    def receiver(self):
        " Return self of the method, or the method that contains the block "
        return self.w_home.w_receiver
    
    # ______________________________________________________________________
    # Imitate the primitive accessors
    
    def fetch(self, index):
        from pypy.lang.smalltalk import objtable
        if index == constants.CTXPART_SENDER_INDEX:
            if self.w_sender:
                return self.w_sender
            else:
                return objtable.w_nil
        elif index == constants.CTXPART_PC_INDEX:
            return objtable.wrap_int(self.pc)
        elif index == constants.CTXPART_STACKP_INDEX:
            return objtable.wrap_int(len(self.stack))
        
        # Invalid!
        raise IndexError

    def store(self, index, value):
        raise NotImplementedError

    # ______________________________________________________________________
    # Method that contains the bytecode for this method/block context

    def w_method(self):
        return self.w_home._w_method

    def getbyte(self):
        bytecode = self.w_method().bytes[self.pc]
        currentBytecode = ord(bytecode)
        self.pc = self.pc + 1
        return currentBytecode

    def getNextBytecode(self):
        self.currentBytecode = self.getbyte()
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
        assert w_v
        self.stack.append(w_v)

    def push_all(self, lst):
        " Equivalent to 'for x in lst: self.push(x)' where x is a lst "
        assert None not in lst
        self.stack += lst

    def top(self):
        return self.peek(0)
        
    def peek(self, idx):
        return self.stack[-(idx+1)]

    def pop_n(self, n):
        assert n >= 0
        start = len(self.stack) - n
        assert start >= 0          # XXX what if this fails?
        del self.stack[start:]

    def pop_and_return_n(self, n):
        assert n >= 0
        start = len(self.stack) - n
        assert start >= 0          # XXX what if this fails?
        res = self.stack[start:]
        del self.stack[start:]
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
        from pypy.lang.smalltalk import objtable
        if index == constants.BLKCTX_BLOCK_ARGUMENT_COUNT_INDEX:
            return objtable.wrap_int(self.argcnt)
        elif index == constants.BLKCTX_INITIAL_IP_INDEX:
            return objtable.wrap_int(self.initialip)
        elif index == constants.BLKCTX_HOME_INDEX:
            return self.w_home
        elif index >= constants.BLKCTX_TEMP_FRAME_START:
            stack_index = len(self.stack) - index - 1
            return self.stack[stack_index]
        else:
            return W_ContextPart.fetch(self, index)

    def store(self, index, value):
        # THIS IS ALL UNTESTED CODE and we're a bit unhappy about it
        # because it crashd the translation N+4 times :-(
        if index == constants.BLKCTX_BLOCK_ARGUMENT_COUNT_INDEX:
            self.argcnt = unwrap_int(value)
        elif index == constants.BLKCTX_INITIAL_IP_INDEX:
            self.pc = unwrap_int(value)
        elif index == constants.BLKCTX_HOME_INDEX:
            assert isinstance(value, W_MethodContext)
            self.w_home = value
        elif index >= constants.BLKCTX_TEMP_FRAME_START:
            stack_index = len(self.stack) - index - 1
            self.stack[stack_index] = value
        else:
            W_ContextPart.store(self, index, value)

class W_MethodContext(W_ContextPart):
    def __init__(self, w_method, w_receiver,
                 arguments, w_sender=None):
        W_ContextPart.__init__(self, self, w_sender)
        self._w_method = w_method
        self.w_receiver = w_receiver
        self.temps = arguments + [w_nil] * w_method.tempsize

    def getclass(self):
        from pypy.lang.smalltalk.classtable import w_MethodContext
        return w_MethodContext

    def fetch(self, index):
        if index == constants.MTHDCTX_METHOD:
            return self.w_method()
        elif index == constants.MTHDCTX_RECEIVER_MAP: # what is this thing?
            return w_nil
        elif index == constants.MTHDCTX_RECEIVER:
            return self.w_receiver
        elif index >= constants.MTHDCTX_TEMP_FRAME_START:
            # First set of indices are temporary variables:
            offset = index - constants.MTHDCTX_TEMP_FRAME_START
            if offset < len(self.temps):
                return self.temps[offset]

            # After that comes the stack:
            offset -= len(self.temps)
            stack_index = len(self.stack) - offset - 1
            return self.stack[stack_index]
        else:
            return W_ContextPart.fetch(self, index)

# Use black magic to create w_nil without running the constructor,
# thus allowing it to be used even in the constructor of its own
# class.  Note that we patch its class in objtable.
w_nil = instantiate(W_PointersObject)
w_nil._vars = []

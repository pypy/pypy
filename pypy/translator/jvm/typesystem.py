"""
Defines the basic structures which are used to represent JVM abstraction,
such as Java types, fields, methods and opcodes.

The structures in this file generally two different, but related,
roles.  First, they describe a JVM abstraction.  For example, jObject
describes some of the properties of the built-in class
java.lang.Object.  Second, they can represent the concrete realization
of an OOTYPE construct.  For example, JvmType instances are used to
represent the translated class which will be generated for some OOTYPE
class.

This file itself is intended to be imported from a wide variety of
locations, and thus generally restricts itself to classes and global
variables that describe intrinsic parts of the JVM.  For example,
there are objects representing different opcodes, type definitions for
built-in types like java.lang.Object and java.lang.System, and
method/field declarations for well-known methods and fields on those
types.

Other files extend this set with objects that represent the JVM
realization of some OOTYPE construct.  For example, the module
builtin.py describes the JVM types that are used to define the
built-in OOTYPE types, such as lists or dictionaries.  The module
node.py contains code for representing user-defined classes.  
"""
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype
from pypy.translator.jvm.option import getoption
from pypy.translator.jvm.log import log

# ___________________________________________________________________________
# Type Descriptors
#
# Internal representations of types for the JVM.  Generally speaking,
# only the generator code should deal with these and even it tries to
# avoid them except write before dumping to the output file.

class JvmTypeDescriptor(str):
    """
    An internal class representing JVM type descriptors, which are
    essentially Java's short hand for types.  This is the lowest level
    of our representation for types and are mainly used when defining
    the types of fields or arguments to methods.  The grammar for type
    descriptors can be read about here:
    
    http://java.sun.com/docs/books/vmspec/2nd-edition/html/ClassFile.doc.html

    We use this class also to represent method descriptors, which define
    a set of argument and return types.
    """
    def is_scalar(self):
        return self[0] != 'L' and self[0] != '['
    def is_reference(self):
        return not self.is_scalar()
    def is_array(self):
        return self[0] == '['
    def is_method(self):
        return self[0] == '('
    def class_name(self):
        """ Converts a descriptor like Ljava/lang/Object; to
        full class name java.lang.Object """
        return self.int_class_name().replace('/','.')
    def int_class_name(self):
        """ Converts a descriptor like Ljava/lang/Object; to
        internal class name java/lang/Object """
        if self[0] == 'L' and self[-1] == ';':
            return self[1:-1]
        else:
            assert self.startswith('[')
            return self
    def type_width(self):
        """ Returns number of JVM words this type takes up.  JVM words
        are a theoretically abstract quantity that basically
        represents 32 bits; so most types are 1, but longs and doubles
        are 2. """
        if self[0] == 'J' or self[0] == 'D':
            return 2
        return 1

# JVM type functions

def desc_for_array_of(jdescr):
    """ Returns a JvmType representing an array of 'jtype', which must be
    another JvmType """
    assert isinstance(jdescr, JvmTypeDescriptor)
    return JvmTypeDescriptor('['+jdescr)

def desc_for_class(classnm):
    """ Returns a JvmType representing a particular class 'classnm', which
    should be a fully qualified java class name (i.e., 'java.lang.String') """
    return JvmTypeDescriptor('L%s;' % classnm.replace('.','/'))

def desc_for_method(argtypes, rettype):
    """ A Java method has a descriptor, which is a string specified
    its argument and return types.  This function converts a list of
    argument types (JvmTypes) and the return type (also a JvmType),
    into one of these descriptor strings. """
    return JvmTypeDescriptor("(%s)%s" % ("".join(argtypes), rettype))

# ______________________________________________________________________
# Basic JVM Types
#
# As described above, some of these define well-known types in the JVM
# or standard Java library.  In addition, there are subtypes of
# JvmType which represent the translated version of some RPython
# class, such as a list, dictionary, or user-defined class.  Those
# subtypes are generally defined in other modules, as they have
# dependencies that would cause circular imports.

class JvmType(object):
    """
    The JvmType interface defines the interface for type objects
    that we return in the database in various places.
    """
    def __init__(self, descriptor):
        """ 'descriptor' should be a jvm.generator.JvmTypeDescriptor object
        for this type """
        self.descriptor = descriptor  # public
        self.name = None              # public, string like "java.lang.Object"
                                      # (None for scalars and arrays)

    def lookup_field(self, fieldnm):
        """ Returns a Field or Property object that represents the
        field named 'fieldnm', or raises KeyError if no such field
        exists.  'fieldnm' generally represents an OOTYPE field, and
        thus this method is generally not implemenented by the JvmType
        classes that just represent native Java classes, even if they
        have fields.  Instead, such fields are described as global
        Field constants, either in this file or elsewhere. """
        raise NotImplementedException
    
    def lookup_method(self, methodnm):
        """ Returns a BaseMethod object that represents the method
        named 'methodnm', or raises KeyError if no such field exists.
        'methodnm' represents an OOTYPE method, and thus this method
        is generally not implemenented by the JvmType classes that
        just represent native Java classes, even if they have methods.
        Instead, such methods are described as global Method constants
        in this file, either in this file or elsewhere. """
        raise NotImplementedException

    def is_generated(self):
        """ Indicates whether the source for this type is generated by
        pypy. """
        return False

    def __repr__(self):
        return "%s<%s>" % (self.__class__.__name__, self.descriptor)
    
class JvmClassType(JvmType):
    """
    Base class used for all class instances.  Kind of an abstract class;
    instances of this class do not support field or method lookup and
    only work to obtain the descriptor.  We use it on occasion for classes
    like java.lang.Object etc.
    """
    def __init__(self, classnm, throwable=False):
        JvmType.__init__(self, desc_for_class(classnm))
        self.name = classnm        # public; String, like 'java.lang.Object'
        self.throwable = throwable # public; boolean
    def lookup_field(self, fieldnm):
        raise KeyError(fieldnm) # we treat as opaque type
    def lookup_method(self, methodnm):
        raise KeyError(fieldnm) # we treat as opaque type

class JvmGeneratedClassType(JvmClassType):
    """ Abstract class extended by the classes in node.py that represent
    generated classes """
    def is_generated(self):
        return True

class JvmInterfaceType(JvmClassType):
    pass

class JvmGeneratedInterfaceType(JvmInterfaceType):
    """ Abstract class extended by the classes in node.py that represent
    generated interfaces """
    def is_generated(self):
        return True

jIntegerClass = JvmClassType('java.lang.Integer')
jLongClass = JvmClassType('java.lang.Long')
jShortClass = JvmClassType('java.lang.Short')
jDoubleClass = JvmClassType('java.lang.Double')
jByteClass = JvmClassType('java.lang.Byte')
jCharClass = JvmClassType('java.lang.Character')
jBoolClass = JvmClassType('java.lang.Boolean')
jThrowable = JvmClassType('java.lang.Throwable', throwable=True)
jPyPyThrowable = JvmClassType('pypy.PyPyThrowable', throwable=True)
jObject = JvmClassType('java.lang.Object')
jString = JvmClassType('java.lang.String')
jCharSequence = JvmClassType('java.lang.CharSequence')
jArrays = JvmClassType('java.util.Arrays')
jMap = JvmInterfaceType('java.util.Map')
jHashMap = JvmClassType('java.util.HashMap')
jIterator = JvmClassType('java.util.Iterator')
jClass = JvmClassType('java.lang.Class')
jStringBuilder = JvmClassType('java.lang.StringBuilder')
jSystem = JvmClassType('java.lang.System')
jPrintStream = JvmClassType('java.io.PrintStream')
jMath = JvmClassType('java.lang.Math')
jList = JvmInterfaceType('java.util.List')
jArrayList = JvmClassType('java.util.ArrayList')
jPyPy = JvmClassType('pypy.PyPy')
jPyPyExcWrap = JvmClassType('pypy.ExceptionWrapper')
jPyPyDictItemsIterator = JvmClassType('pypy.DictItemsIterator')
jPyPyInterlink = JvmInterfaceType('pypy.Interlink')
jPyPyCustomDict = JvmClassType('pypy.CustomDict')
jPyPyStatResult = JvmClassType('pypy.StatResult')
jPyPyWeakRef = JvmClassType('pypy.PyPyWeakRef')
jll_os = JvmClassType('pypy.ll_os')
jPyPyRecordSignedSigned = JvmClassType('pypy.RecordSignedSigned')
jPyPyRecordStringString = JvmClassType('pypy.RecordStringString')
jPyPyRecordFloatSigned = JvmClassType('pypy.RecordFloatSigned')
jPyPyRecordFloatFloat = JvmClassType('pypy.RecordFloatFloat')
jPyPyAbstractMethodException = JvmClassType('pypy.AbstractMethodException')

jStackOverflowError = JvmClassType('java.lang.StackOverflowError', throwable=True)
jOutOfMemoryError = JvmClassType('java.lang.OutOfMemoryError', throwable=True)
jArithmeticException = JvmClassType('java.lang.ArithmeticException', throwable=True)

class JvmScalarType(JvmType):
    """
    Subclass used for all scalar type instances.
    """
    def __init__(self, descrstr, boxtype, unboxmethod):
        JvmType.__init__(self, JvmTypeDescriptor(descrstr))
        self.box_type = boxtype
        self.unbox_method = unboxmethod
    def lookup_field(self, fieldnm):
        raise KeyError(fieldnm)        # Scalar objects have no fields
    def lookup_method(self, methodnm): 
        raise KeyError(methodnm)       # Scalar objects have no methods

jVoid = JvmScalarType('V', None, None)
jInt = JvmScalarType('I', jIntegerClass, 'intValue')
jLong = JvmScalarType('J', jLongClass, 'longValue')
jBool = JvmScalarType('Z', jBoolClass, 'booleanValue')
jDouble = JvmScalarType('D', jDoubleClass, 'doubleValue')
jByte = JvmScalarType('B', jByteClass, 'byteValue')
jChar = JvmScalarType('C', jCharClass, 'charValue')
jShort = JvmScalarType('S', jShortClass, 'shortValue')

class Generifier(object):

    """

    A utility class for working with generic methods in the OOTYPE
    system.  You instantiate it with a given type, and you can ask it
    for the actual or erased types of any method of that type.
    
    """

    def __init__(self, OOTYPE):
        self.OOTYPE = OOTYPE

        # Make a hashtable mapping the generic parameter to a tuple:
        #    (actual type, erased type)
        
        self.generics = {}
        
        if hasattr(self.OOTYPE, 'SELFTYPE_T'):
            self.generics[self.OOTYPE.SELFTYPE_T] = (self.OOTYPE,self.OOTYPE)
            
        for pname,pval in (('ITEMTYPE_T', 'ITEM'),
                           ('KEYTYPE_T', '_KEYTYPE'),
                           ('VALUETYPE_T', '_VALUETYPE')):
            if hasattr(self.OOTYPE, pname):
                placeholder = getattr(self.OOTYPE, pname)
                placeholder_val = getattr(self.OOTYPE, pval)
                self.generics[placeholder] = (placeholder_val, ootype.ROOT)

    def full_types(self, method_name):
        """
        Returns a tuple of argument and return types for the method
        named 'method_name'.  These are the actual generic types.  The
        set method for a list of strings, for example, might return:
        ( [INT, STRING], VOID )
        """
        GENMETH = self.OOTYPE._GENERIC_METHODS[method_name]
        ARGS, RESULT = (GENMETH.ARGS, GENMETH.RESULT)
        ARGS = [self.generics.get(X,(X,))[0] for X in ARGS]
        RESULT = self.generics.get(RESULT, (RESULT,))[0]
        return (ARGS, RESULT)

    def erased_types(self, method_name):
        """
        Returns a tuple of argument and return types for the method
        named 'method_name'.  These are the erased generic types.  The
        set method for a list of strings, for example, might return:
        ( [INT, OBJECT], VOID )
        """
        GENMETH = self.OOTYPE._GENERIC_METHODS[method_name]
        ARGS, RESULT = (GENMETH.ARGS, GENMETH.RESULT)
        ARGS = [self.generics.get(X,(None,X))[1] for X in ARGS]
        RESULT = self.generics.get(RESULT, (None,RESULT))[1]
        return (ARGS, RESULT)

# ______________________________________________________________________
# Java Callback Interfaces
#
# A list of interfaces which static functions that we generate will
# automatically implement if applicable.  See the pypy/Callback.java,
# node.py/StaticMethodInterface for more information.

jCallbackInterfaces = [] # collects all of the defined JvmCallbackInterfaces

class JvmCallbackInterface(JvmInterfaceType):
    def __init__(self, name, jargtypes, jrettype):
        JvmInterfaceType.__init__(self, name)
        self.java_argument_types = jargtypes
        self.java_return_type = jrettype
        jCallbackInterfaces.append(self)  # add to global list
    def matches(self, jargtypes, jrettype):
        """ Given a set of argument types and a return type for some
        static function defined by the user, returns true if this
        JvmCallbackInterface applies.  Note that the types don't have
        to match exactly: we assume that (in the list of arguments)
        jObject is used as a wildcard, and some adaptation code may
        have to be inserted."""
        if len(self.java_argument_types) != len(jargtypes):
            return False
        for expjarg, actjarg in zip(self.java_argument_types, jargtypes):
            if expjarg == jObject: continue # hack: assume obj means any type
            if expjarg != actjarg: return False
        return jrettype == self.java_return_type
    
jPyPyHashCode = JvmCallbackInterface('pypy.HashCode', [jObject], jInt)
jPyPyEquals = JvmCallbackInterface('pypy.Equals', [jObject, jObject], jBool)

class JvmNativeClass(JvmClassType):
    def __init__(self, db, OOTYPE):
        self.OOTYPE = OOTYPE
        self.db = db
        # XXX fixed java.lang?
        self.methods = {}
        JvmClassType.__init__(self, "java.util." + OOTYPE._name)
        self._add_methods()

    def __eq__(self, other):
        return isinstance(other, JvmNativeClass) and other.OOTYPE == self.OOTYPE
    
    def __hash__(self):
        return hash(("JvmNativeClass", self.OOTYPE))

    def lookup_field(self):
        XXX

    def lookup_method(self, methname):
        return self.methods[methname]

    def _add_methods(self):
        for methname, methspec in self.OOTYPE._class_._methods.items():
            argtypes = [self.db.annotation_to_cts(arg._type) for arg in
                        methspec.args]
            restype = self.db.annotation_to_cts(methspec.retval._type)
            self.methods[methname] = Method.v(self, methname,
                                              argtypes, restype)

# ______________________________________________________________________
# The bridge between RPython array and JVM arrays.  The main differences
# are that (a) RPython has arrays of void type, and (b) RPython arrays
# have methods, whereas Java methods don't.  We inline those methods
# into the appropriate bytecode.

class _JvmVoidArray(JvmClassType):
    """
    A special case for void arrays. These are represented by an instance
    of the VoidArray class, which implements the required methods.
    """

    method_types = {
        'll_length': ([], jInt),
        'll_getitem_fast': ([jInt], jVoid),
        'll_setitem_fast': ([jInt], jVoid),
        }

    def __init__(self):
        JvmClassType.__init__(self, 'pypy.VoidArray')

    def make(self, gen):
        # Construct a new VoidArray object, assuming the length has
        # been pushed onto the stack already.
        gen.emit(PYPYVOIDARRAYMAKE)
        
    def lookup_field(self, fieldnm):
        raise KeyError(fieldnm) # no fields

    def lookup_method(self, methodnm):
        jargtypes, jrettype = self.method_types[methodnm]
        return Method.v(self, methodnm, jargtypes, jrettype)
    
class JvmArrayType(JvmType):
    """
    Subclass used for all array instances.
    """
    def __init__(self, elemtype):
        JvmType.__init__(self, desc_for_array_of(elemtype.descriptor))
        self.element_type = elemtype
    def make(self, gen):
        # Issues the opcode to build a new array of the appropriate type.
        # Assumes the length has been pushed onto the stack already.
        gen.emit(NEWARRAY.for_type(self))
    def lookup_field(self, fieldnm):
        raise KeyError(fieldnm)
    def lookup_method(self, methodnm):
        # Arrays don't have methods in Java, but they do in the ootype system
        if methodnm == "ll_length":
            return OpcodeMethod([], jInt, ARRAYLENGTH)
        elif methodnm == "ll_getitem_fast":
            return OpcodeMethod([jInt], self.element_type,
                                ARRLOAD.for_type(self.element_type))
        elif methodnm == "ll_setitem_fast":
            return OpcodeMethod([jInt, self.element_type], jVoid,
                                ARRSTORE.for_type(self.element_type))
        else:
            raise KeyError(methodnm)
        
jBoolArray = JvmArrayType(jBool)
jByteArray = JvmArrayType(jByte)
jObjectArray = JvmArrayType(jObject)
jStringArray = JvmArrayType(jString)
jDoubleArray = JvmArrayType(jDouble)
jCharArray = JvmArrayType(jChar)
jIntArray = JvmArrayType(jInt)
jVoidArray = _JvmVoidArray()
            
# ______________________________________________________________________
# Opcodes
#
# Objects describing the various opcodes which we use.  In some cases,
# there are also opcode families, which consist of a set of related
# opcodes that are specialized by the types they operate on (i.e.,
# IADD, DADD, etc).  

class Opcode(object):
    def __init__(self, jvmstr):
        """
        flags is a set of flags (see above) that describe opcode #UPDATE
        jvmstr is the name for jasmin printouts
        """
        self.jvmstr = jvmstr
        self.flags = None #Should flags be added to args?

    def __repr__(self):
        return "<Opcode %s:%x>" % (self.jvmstr, self.flags)

    def specialize(self, args):
        """ Process the argument list according to the various flags.
        Returns a tuple (OPCODE, ARGS) where OPCODE is a string representing
        the new opcode, and ARGS is a list of arguments or empty tuple.
        Most of these do not do anything. """
        return (self.jvmstr, args)

class IntConstOpcode(Opcode):
    """ The ICONST opcode specializes itself for small integer opcodes. """
    def specialize(self, args):
        assert len(args) == 1
        if args[0] == -1:
            return self.jvmstr + "_m1", ()
        elif args[0] >= 0 and args[0] <= 5:
            return self.jvmstr + "_" + str(args[0]), ()
        # Non obvious: convert ICONST to LDC if the constant is out of
        # range
        return "ldc", args

class VarOpcode(Opcode):
    """ An Opcode which takes a variable index as an argument; specialized
    to small integer indices. """
    def specialize(self, args):
        assert len(args) == 1
        if args[0] >= 0 and args[0] <= 3:
            return self.jvmstr + "_" + str(args[0]), ()
        return Opcode.specialize(self, args)

class IntClassNameOpcode(Opcode):
    """ An opcode which takes an internal class name as its argument;
    the actual argument will be a JvmType instance. """
    def specialize(self, args):
        args = [args[0].descriptor.int_class_name()]
        return self.jvmstr, args
        
class OpcodeFamily(object):
    """
    Many opcodes in JVM have variants that depend on the type of the
    operands; for example, one must choose the correct ALOAD, ILOAD,
    or DLOAD depending on whether one is loading a reference, integer,
    or double variable respectively.  Each instance of this class
    defines one 'family' of opcodes, such as the LOAD family shown
    above, and produces Opcode objects specific to a particular type.
    """
    def __init__(self, opcclass, suffix):
        """
        opcclass is the opcode subclass to use (see above) when
        instantiating a particular opcode
        
        jvmstr is the name for jasmin printouts
        """
        self.opcode_class = opcclass
        self.suffix = suffix
        self.cache = {}

    def _o(self, prefix):
        try:
            return self.cache[prefix]
        except KeyError:
            self.cache[prefix] = obj = self.opcode_class(
                prefix+self.suffix)
            return obj
        
    def for_type(self, argtype):
        """ Returns a customized opcode of this family appropriate to
        'argtype', a JvmType object. """

        desc = argtype.descriptor

        # These are always true:
        if desc[0] == 'L': return self._o("a")   # Objects
        if desc[0] == '[': return self._o("a")   # Arrays
        if desc == 'I':    return self._o("i")   # Integers
        if desc == 'J':    return self._o("l")   # Integers
        if desc == 'D':    return self._o("d")   # Doubles
        if desc == 'V':    return self._o("")    # Void [used by RETURN]

        # Chars/Bytes/Booleans are normally represented as ints
        # in the JVM, but some opcodes are different.  They use a
        # different OpcodeFamily (see ArrayOpcodeFamily for ex)
        if desc == 'C':    return self._o("i")   # Characters
        if desc == 'B':    return self._o("i")   # Bytes
        if desc == 'Z':    return self._o("i")   # Boolean
        if desc == 'S':    return self._o("i")   # Short

        assert False, "Unknown argtype=%s" % repr(argtype)
        raise NotImplementedError

class ArrayOpcodeFamily(OpcodeFamily):
    """ Opcode family specialized for array access instr """
    def for_type(self, argtype):
        desc = argtype.descriptor
        if desc == 'J':    return self._o("l")   # Integers
        if desc == 'D':    return self._o("d")   # Doubles
        if desc == 'C':    return self._o("c")   # Characters
        if desc == 'B':    return self._o("b")   # Bytes
        if desc == 'Z':    return self._o("b")   # Boolean (access as bytes)
        return OpcodeFamily.for_type(self, argtype)

class NewArrayOpcodeFamily(object):
    def __init__(self):
        self.cache = {}

    def for_type(self, arraytype):
        try:
            return self.cache[arraytype]
        except KeyError:
            pass
        desc = arraytype.descriptor
        if desc == '[I':
            s = "newarray int"
        elif desc == '[D':
            s = "newarray double"
        elif desc == '[C':
            s = "newarray char"
        elif desc == '[B':
            s = "newarray byte"
        elif desc == '[Z':
            s = "newarray boolean"
        else:
            s = "anewarray " + arraytype.element_type.descriptor.int_class_name()
        self.cache[arraytype] = obj = Opcode(s)
        return obj

NEWARRAY = NewArrayOpcodeFamily()
ARRAYLENGTH = Opcode("arraylength")

# Define the opcodes for IFNE, IFEQ, IFLT, IF_ICMPLT, etc.  The IFxx
# variants compare a single integer arg against 0, and the IF_ICMPxx
# variants compare 2 integer arguments against each other.
for cmpop in ('ne', 'eq', 'lt', 'gt', 'le', 'ge'):
    ifop = "if%s" % cmpop
    if_icmpop = "if_icmp%s" % cmpop
    globals()[ifop.upper()] = Opcode(ifop)
    globals()[if_icmpop.upper()] = Opcode(if_icmpop)

# Compare references, either against NULL or against each other
IFNULL =    Opcode('ifnull')
IFNONNULL = Opcode('ifnonnull')
IF_ACMPEQ = Opcode('if_acmpeq')
IF_ACMPNE = Opcode('if_acmpne')

# Method invocation
INVOKESTATIC = Opcode('invokestatic')
INVOKEVIRTUAL = Opcode('invokevirtual')
INVOKESPECIAL = Opcode('invokespecial')
INVOKEINTERFACE = Opcode('invokeinterface')

# Other opcodes
LDC =       Opcode('ldc')       # single-word types
LDC2 =      Opcode('ldc2_w')    # double-word types: doubles and longs
GOTO =      Opcode('goto')
ICONST =    IntConstOpcode('iconst')
ICONST_0 =  Opcode('iconst_0')  # sometimes convenient to refer to this directly
ACONST_NULL=Opcode('aconst_null')
DCONST_0 =  Opcode('dconst_0')
DCONST_1 =  Opcode('dconst_1')
LCONST_0 =  Opcode('lconst_0')
LCONST_1 =  Opcode('lconst_1')
GETFIELD =  Opcode('getfield')
PUTFIELD =  Opcode('putfield')
GETSTATIC = Opcode('getstatic')
PUTSTATIC = Opcode('putstatic')
CHECKCAST = IntClassNameOpcode('checkcast')
INEG =      Opcode('ineg')
IXOR =      Opcode('ixor')
IADD =      Opcode('iadd')
ISUB =      Opcode('isub')
IMUL =      Opcode('imul')
IDIV =      Opcode('idiv')
IREM =      Opcode('irem')
IAND =      Opcode('iand')
IOR =       Opcode('ior')
ISHL =      Opcode('ishl')
ISHR =      Opcode('ishr')
IUSHR =     Opcode('iushr')
LCMP =      Opcode('lcmp')
DCMPG =     Opcode('dcmpg')
DCMPL =     Opcode('dcmpl')
NOP =       Opcode('nop')
I2D =       Opcode('i2d')
I2L =       Opcode('i2l')
I2S =       Opcode('i2s')
D2I=        Opcode('d2i')
#D2L=        Opcode('d2l') #PAUL
L2I =       Opcode('l2i')
L2D =       Opcode('l2d')
ATHROW =    Opcode('athrow')
DNEG =      Opcode('dneg')
DADD =      Opcode('dadd')
DSUB =      Opcode('dsub')
DMUL =      Opcode('dmul')
DDIV =      Opcode('ddiv')
DREM =      Opcode('drem')
LNEG =      Opcode('lneg')
LADD =      Opcode('ladd')
LSUB =      Opcode('lsub')
LMUL =      Opcode('lmul')
LDIV =      Opcode('ldiv')
LREM =      Opcode('lrem')
LAND =      Opcode('land')
LOR =       Opcode('lor')
LXOR =      Opcode('lxor')
LSHL =      Opcode('lshl')
LSHR =      Opcode('lshr')
LUSHR =     Opcode('lushr')
NEW =       IntClassNameOpcode('new')
DUP =       Opcode('dup')
DUP2 =      Opcode('dup2')
DUP_X1 =    Opcode('dup_x1')
POP =       Opcode('pop')
POP2 =      Opcode('pop2')
SWAP =      Opcode('swap')
INSTANCEOF= IntClassNameOpcode('instanceof')
# Loading/storing local variables
LOAD =      OpcodeFamily(VarOpcode, "load")
STORE =     OpcodeFamily(VarOpcode, "store")
RETURN =    OpcodeFamily(Opcode, "return")

# Loading/storing from arrays
#   *NOTE*: This family is characterized by the type of the ELEMENT,
#   not the type of the ARRAY.  
#   
#   Also: here I break from convention by naming the objects ARRLOAD
#   rather than ALOAD, even though the suffix is 'aload'.  This is to
#   avoid confusion with the ALOAD opcode.
ARRLOAD =      ArrayOpcodeFamily(Opcode, "aload")
ARRSTORE =     ArrayOpcodeFamily(Opcode, "astore")

# ______________________________________________________________________
# Methods and Fields
#
# These structures are used throughout the code to refer to JVM
# methods and fields.  Similarly to JvmType instances, they are used
# both to represent random fields/methods in the JVM, and to represent
# the translation of an OOTYPE field/method.  Therefore, these may not
# actually generate code corresponding to a real JVM method: for
# example, arrays use a BaseMethod subclass to generate the
# appropriate JVM opcodes that correspond to RPython arrays.
# Likewise, the Property class (see below) allows us to use a pair of
# JVM methods to represent an OOTYPE field.

class BaseMethod(object):
    def __init__(self, argtypes, rettype):
        self.argument_types = argtypes # List of jvmtypes
        self.return_type = rettype     # jvmtype
        
    def is_static(self):
        raise NotImplementedError
    
    def invoke(self, gen):
        raise NotImplementedError

class OpcodeMethod(BaseMethod):
    """
    Represents a "method" that is actually implemented by a single opcode,
    such as ARRAYLENGTH
    """
    def __init__(self, argtypes, rettype, opcode, static=False):
        """
        argtypes = an array of jvm types indicating what we expect on stack
        rettype = the type we will push on the stack (if any)
        opcode = the opcode to emit
        static = should we be considered static?  if true, then we will
        not push the receiver onto the stack in metavm
        """
        BaseMethod.__init__(self, argtypes, rettype)
        self.opcode = opcode
        self.static = static

    def is_static(self):
        return self.static
    
    def invoke(self, gen):
        gen.emit(self.opcode)

class Method(BaseMethod):

    """
    Represents a method implemented by a genuine JVM method.  Unlike
    OpcodeMethod, when we emit the opcode this class is an argument to
    it, and contains the extra info about the class/method being
    invoked that is required.
    """

    # Create a constructor:
    def c(classty, argtypes):
        return Method(classty.name, "<init>", argtypes, jVoid,
                      opcode=INVOKESPECIAL)
    c = staticmethod(c)

    # Create a virtual or interface method:
    def v(classty, methnm, argtypes, rettype):
        """
        Shorthand to create a virtual method.
        'class' - JvmType object for the class
        'methnm' - name of the method (Python string)
        'argtypes' - list of JvmType objects, one for each argument but
        not the this ptr
        'rettype' - JvmType for return type
        """
        assert argtypes is not None
        assert rettype is not None
        classnm = classty.name
        if isinstance(classty, JvmInterfaceType):
            opc = INVOKEINTERFACE
        else:
            assert isinstance(classty, JvmClassType)
            opc = INVOKEVIRTUAL
        return Method(classnm, methnm, argtypes, rettype, opcode=opc)
    v = staticmethod(v)

    # Create a static method:
    def s(classty, methnm, argtypes, rettype):
        """
        Shorthand to create a static method.
        'class' - JvmType object for the class
        'methnm' - name of the method (Python string)
        'argtypes' - list of JvmType objects, one for each argument but
        not the this ptr
        'rettype' - JvmType for return type
        """
        assert isinstance(classty, JvmType)
        classnm = classty.name
        return Method(classnm, methnm, argtypes, rettype)
    s = staticmethod(s)
    
    def __init__(self, classnm, methnm, argtypes, rettype, opcode=INVOKESTATIC):
        BaseMethod.__init__(self, argtypes, rettype)
        self.opcode = opcode
        self.class_name = classnm  # String, ie. "java.lang.Math"
        self.method_name = methnm  # String "abs"

        # Compute the method descriptior, which is a string like "()I":
        argtypesdesc = [a.descriptor for a in argtypes]
        rettypedesc = rettype.descriptor
        self.descriptor = desc_for_method(argtypesdesc, rettypedesc)  
    def invoke(self, gen):
        gen._instr(self.opcode, self)        
    def is_static(self):
        return self.opcode == INVOKESTATIC
    def jasmin_syntax(self):
        res = "%s/%s%s" % (self.class_name.replace('.','/'),
                           self.method_name,
                           self.descriptor)
        # A weird, inexplicable quirk of Jasmin syntax is that it requires
        # the number of arguments after an invokeinterface call:
        if self.opcode == INVOKEINTERFACE:
            res += " %d" % (len(self.argument_types)+1,)
        return res

class Field(object):

    """
    Represents an actual JVM field.  Use the methods
       fld.load(gen) / gen.emit(fld)
    or
       fld.store(gen)
    to load the field's value onto the stack, or store into the field.
    If this is not a static field, you must have pushed the object
    containing the field and the field's value first.

    See also Property.
    """

    @staticmethod
    def i(classty, fieldnm, fieldty, OOTYPE=None):
        """
        Shorthand to create an instance field.
        'class' - JvmType object for the class containing the field
        'fieldnm' - name of the field (Python string)
        'fieldty' - JvmType object for the type of the field
        'OOTYPE' - optional OOTYPE object for the type of the field
        """
        return Field(classty.name, fieldnm, fieldty, False, OOTYPE)
    
    @staticmethod
    def s(classty, fieldnm, fieldty, OOTYPE=None):
        """
        Shorthand to create a static field.
        'class' - JvmType object for the class containing the field
        'fieldnm' - name of the field (Python string)
        'fieldty' - JvmType object for the type of the field
        'OOTYPE' - optional OOTYPE object for the type of the field
        """
        return Field(classty.name, fieldnm, fieldty, True, OOTYPE)

    def __init__(self, classnm, fieldnm, jtype, static, OOTYPE=None):
        # All fields are public
        self.class_name = classnm  # String, ie. "java.lang.Math"
        self.field_name = fieldnm  # String "someField"
        self.OOTYPE = OOTYPE       # OOTYPE equivalent of JvmType, may be None
        self.jtype = jtype         # JvmType
        self.is_static = static    # True or False
    def load(self, gen):
        if self.is_static:
            gen._instr(GETSTATIC, self)
        else:
            gen._instr(GETFIELD, self)
    def store(self, gen):
        if self.is_static:
            gen._instr(PUTSTATIC, self)
        else:
            gen._instr(PUTFIELD, self)
    def jasmin_syntax(self):
        return "%s/%s %s" % (
            self.class_name.replace('.','/'),
            self.field_name,
            self.jtype.descriptor)

class Property(object):
    """
    An object which acts like a Field, but when a value is loaded or
    stored it actually invokes accessor methods.  Use like a field
    (prop.load(gen), prop.store(gen), etc).
    """
    def __init__(self, field_name, get_method, put_method, OOTYPE=None):
        self.get_method = get_method
        self.put_method = put_method
        self.field_name = field_name
        self.OOTYPE = OOTYPE
        
        # Synthesize the Field attributes from the get_method/put_method:
        self.class_name = get_method.class_name
        assert put_method.class_name == self.class_name
        self.jtype = get_method.return_type
        self.is_static = get_method.is_static
    def load(self, gen):
        self.get_method.invoke(gen)
    def store(self, gen):
        self.put_method.invoke(gen)
    # jasmin_syntax is not needed, since this object itself never appears
    # as an argument an Opcode

# ___________________________________________________________________________
# Methods
#
# "Method" objects describe all the information needed to invoke a
# method.  We create one for each node.Function object, as well as for
# various helper methods (defined below).  To invoke a method, you
# push its arguments and then use generator.emit(methobj) where
# methobj is its Method instance.

OBJHASHCODE =           Method.v(jObject, 'hashCode', (), jInt)
OBJTOSTRING =           Method.v(jObject, 'toString', (), jString)
OBJEQUALS =             Method.v(jObject, 'equals', (jObject,), jBool)
SYSTEMIDENTITYHASH =    Method.s(jSystem, 'identityHashCode', (jObject,), jInt)
SYSTEMGC =              Method.s(jSystem, 'gc', (), jVoid)
INTTOSTRINGI =          Method.s(jIntegerClass, 'toString', (jInt,), jString)
SHORTTOSTRINGS =        Method.s(jShortClass, 'toString', (jShort,), jString)
LONGTOSTRINGL =         Method.s(jLongClass, 'toString', (jLong,), jString)
DOUBLETOSTRINGD =       Method.s(jDoubleClass, 'toString', (jDouble,), jString)
CHARTOSTRINGC =         Method.s(jCharClass, 'toString', (jChar,), jString)
MATHIABS =              Method.s(jMath, 'abs', (jInt,), jInt)
IABSOVF =               Method.v(jPyPy, 'abs_ovf', (jInt,), jInt)
MATHLABS =              Method.s(jMath, 'abs', (jLong,), jLong)
LABSOVF =               Method.v(jPyPy, 'abs_ovf', (jLong,), jLong)
MATHDABS =              Method.s(jMath, 'abs', (jDouble,), jDouble)
INEGOVF =               Method.v(jPyPy, 'negate_ovf', (jInt,), jInt)
LNEGOVF =               Method.v(jPyPy, 'negate_ovf', (jLong,), jLong)
IADDOVF =               Method.v(jPyPy, 'add_ovf', (jInt, jInt), jInt)
LADDOVF =               Method.v(jPyPy, 'add_ovf', (jLong, jLong), jLong)
ISUBOVF =               Method.v(jPyPy, 'subtract_ovf', (jInt, jInt), jInt)
LSUBOVF =               Method.v(jPyPy, 'subtract_ovf', (jLong, jLong), jLong)
IMULOVF =               Method.v(jPyPy, 'multiply_ovf', (jInt, jInt), jInt)
LMULOVF =               Method.v(jPyPy, 'multiply_ovf', (jLong, jLong), jLong)
MATHFLOOR =             Method.s(jMath, 'floor', (jDouble,), jDouble)
IFLOORDIVOVF =          Method.v(jPyPy, 'floordiv_ovf', (jInt, jInt), jInt)
LFLOORDIVOVF =          Method.v(jPyPy, 'floordiv_ovf', (jLong, jLong), jLong)
IFLOORDIVZEROVF =       Method.v(jPyPy, 'floordiv_zer_ovf', (jInt, jInt), jInt)
LFLOORDIVZEROVF =       Method.v(jPyPy, 'floordiv_zer_ovf', (jLong, jLong), jLong)
IREMOVF =               Method.v(jPyPy, 'mod_ovf', (jInt, jInt), jInt)
LREMOVF =               Method.v(jPyPy, 'mod_ovf', (jLong, jLong), jLong)
ISHLOVF =               Method.v(jPyPy, 'lshift_ovf', (jInt, jInt), jInt)
LSHLOVF =               Method.v(jPyPy, 'lshift_ovf', (jLong, jLong), jLong)
MATHDPOW =              Method.s(jMath, 'pow', (jDouble, jDouble), jDouble)
PRINTSTREAMPRINTSTR =   Method.v(jPrintStream, 'print', (jString,), jVoid)
CLASSFORNAME =          Method.s(jClass, 'forName', (jString,), jClass)
CLASSISASSIGNABLEFROM = Method.v(jClass, 'isAssignableFrom', (jClass,), jBool)
STRINGBUILDERAPPEND =   Method.v(jStringBuilder, 'append',
                                 (jString,), jStringBuilder)
PYPYINTBETWEEN =        Method.s(jPyPy, 'int_between', (jInt,jInt,jInt), jBool)
PYPYUINTCMP =           Method.s(jPyPy, 'uint_cmp', (jInt,jInt,), jInt)
PYPYULONGCMP =          Method.s(jPyPy, 'ulong_cmp', (jLong,jLong), jInt)
PYPYUINTMOD =           Method.v(jPyPy, 'uint_mod', (jInt, jInt), jInt)
PYPYUINTMUL =           Method.v(jPyPy, 'uint_mul', (jInt, jInt), jInt)
PYPYUINTDIV =           Method.v(jPyPy, 'uint_div', (jInt, jInt), jInt)
PYPYULONGMOD =          Method.v(jPyPy, 'ulong_mod', (jLong, jLong), jLong)
PYPYUINTTOLONG =        Method.s(jPyPy, 'uint_to_long', (jInt,), jLong)
PYPYUINTTODOUBLE =      Method.s(jPyPy, 'uint_to_double', (jInt,), jDouble)
PYPYDOUBLETOUINT =      Method.s(jPyPy, 'double_to_uint', (jDouble,), jInt)
PYPYDOUBLETOLONG =      Method.v(jPyPy, 'double_to_long', (jDouble,), jLong) #PAUL
PYPYDOUBLETOULONG =     Method.s(jPyPy, 'double_to_ulong', (jDouble,), jLong)
PYPYULONGTODOUBLE =     Method.s(jPyPy, 'ulong_to_double', (jLong,), jDouble)
PYPYLONGBITWISENEGATE = Method.v(jPyPy, 'long_bitwise_negate', (jLong,), jLong)
PYPYSTRTOINT =          Method.v(jPyPy, 'str_to_int', (jString,), jInt)
PYPYSTRTOUINT =         Method.v(jPyPy, 'str_to_uint', (jString,), jInt)
PYPYSTRTOLONG =         Method.v(jPyPy, 'str_to_long', (jString,), jLong)
PYPYSTRTOULONG =        Method.v(jPyPy, 'str_to_ulong', (jString,), jLong)
PYPYSTRTOBOOL =         Method.v(jPyPy, 'str_to_bool', (jString,), jBool)
PYPYSTRTODOUBLE =       Method.v(jPyPy, 'str_to_double', (jString,), jDouble)
PYPYSTRTOCHAR =         Method.v(jPyPy, 'str_to_char', (jString,), jChar)
PYPYBOOLTODOUBLE =      Method.v(jPyPy, 'bool_to_double', (jBool,), jDouble)
PYPYDUMP          =     Method.s(jPyPy, 'dump', (jString,), jVoid)
PYPYDUMPEXCWRAPPER =    Method.s(jPyPy, 'dump_exc_wrapper', (jObject,), jVoid)
PYPYSERIALIZEBOOLEAN =  Method.s(jPyPy, 'serialize_boolean', (jBool,), jString)
PYPYSERIALIZEUINT  =    Method.s(jPyPy, 'serialize_uint', (jInt,), jString)
PYPYSERIALIZEULONG =    Method.s(jPyPy, 'serialize_ulonglong', (jLong,),jString)
PYPYSERIALIZEVOID =     Method.s(jPyPy, 'serialize_void', (), jString)
PYPYESCAPEDCHAR =       Method.s(jPyPy, 'escaped_char', (jChar,), jString)
PYPYESCAPEDUNICHAR =    Method.s(jPyPy, 'escaped_unichar', (jChar,), jString)
PYPYESCAPEDSTRING =     Method.s(jPyPy, 'escaped_string', (jString,), jString)
PYPYESCAPEDUNICODE =    Method.s(jPyPy, 'escaped_unicode', (jString,), jString)
PYPYSERIALIZEOBJECT =   Method.s(jPyPy, 'serializeObject', (jObject,), jString)
PYPYRUNTIMENEW =        Method.s(jPyPy, 'RuntimeNew', (jClass,), jObject)
PYPYSTRING2BYTES =      Method.s(jPyPy, 'string2bytes', (jString,), jByteArray)
PYPYARRAYTOLIST =       Method.s(jPyPy, 'array_to_list', (jObjectArray,), jArrayList)
PYPYBOXINT =            Method.s(jPyPy, 'box_integer', (jInt,), jIntegerClass)
PYPYUNBOXINT =          Method.s(jPyPy, 'unbox_integer', (jIntegerClass,), jInt)
PYPYOOPARSEFLOAT =      Method.v(jPyPy, 'ooparse_float', (jString,), jDouble)
OBJECTGETCLASS =        Method.v(jObject, 'getClass', (), jClass)
CLASSGETNAME =          Method.v(jClass, 'getName', (), jString)
CUSTOMDICTMAKE =        Method.s(jPyPyCustomDict, 'make',
                                 (jPyPyEquals, jPyPyHashCode), jPyPyCustomDict)
PYPYWEAKREFCREATE =     Method.s(jPyPyWeakRef, 'create', (jObject,), jPyPyWeakRef)
PYPYWEAKREFGET =        Method.s(jPyPyWeakRef, 'll_get', (), jObject)
PYPYVOIDARRAYMAKE =     Method.s(jVoidArray, 'make', (jInt,), jVoidArray)

# ___________________________________________________________________________
# Fields
#
# Field objects encode information about fields.

SYSTEMOUT =    Field.s(jSystem, 'out', jPrintStream)
SYSTEMERR =    Field.s(jSystem, 'err', jPrintStream)
DOUBLENAN =    Field.s(jDoubleClass, 'NaN', jDouble)
DOUBLEPOSINF = Field.s(jDoubleClass, 'POSITIVE_INFINITY', jDouble)
DOUBLENEGINF = Field.s(jDoubleClass, 'NEGATIVE_INFINITY', jDouble)

PYPYINTERLINK= Field.i(jPyPy, 'interlink', jPyPyInterlink)
PYPYOS =       Field.i(jPyPy, 'os', jll_os)


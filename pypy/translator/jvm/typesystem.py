"""
Definition and some basic translations between PyPy ootypesystem and
JVM type system.

Here are some tentative non-obvious decisions:

Signed scalar types mostly map as is.  

Unsigned scalar types are a problem; the basic idea is to store them
as signed values, but execute special code when working with them.  Another
option would be to use classes, or to use the "next larger" type and remember to use appropriate modulos.  The jury is out on
this.  Another idea would be to add a variant type system that does
not have unsigned values, and write the required helper and conversion
methods in RPython --- then it could be used for multiple backends.

Python strings are mapped to byte arrays, not Java Strings, since
Python strings are really sets of bytes, not unicode code points.
Jury is out on this as well; this is not the approach taken by cli,
for example.

Python Unicode strings, on the other hand, map directly to Java Strings.

WeakRefs are mapped to a thin wrapper class, PyPyWeakRef, to allow for
mutation of the object being referenced (the ll_set method).

Collections can hopefully map to Java collections instances.  Note
that JVM does not have an idea of generic typing at its lowest level
(well, they do have signature attributes, but those don't really count
for much).

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
        assert self[0] == 'L' and self[-1] == ';'
        return self[1:-1]
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
        """ If the class has a field named 'fieldnm', returns a
        jvmgen.Field or jvmgen.Property object that represents it and can
        be used with the interpreter to load/store it.  If no such field
        exists, or this is not a class, then raises KeyError. """
        raise NotImplementedException
    def lookup_method(self, methodnm):
        """ Returns a jvm.generator.Method object representing the method
        with the given name, or raises KeyError if that field does not
        exist on this type. """
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
jDoubleClass = JvmClassType('java.lang.Double')
jByteClass = JvmClassType('java.lang.Byte')
jCharClass = JvmClassType('java.lang.Character')
jBoolClass = JvmClassType('java.lang.Boolean')
jThrowable = JvmClassType('java.lang.Throwable', throwable=True)
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

class JvmArrayType(JvmType):
    """
    Subclass used for all array instances.
    """
    def __init__(self, elemtype):
        JvmType.__init__(self, desc_for_array_of(elemtype.descriptor))
        self.element_type = elemtype
    def lookup_field(self, fieldnm):
        raise KeyError(fieldnm)  # TODO adjust interface to permit opcode here
    def lookup_method(self, methodnm): 
        raise KeyError(methodnm) # Arrays have no methods
    
jByteArray = JvmArrayType(jByte)
jObjectArray = JvmArrayType(jObject)
jStringArray = JvmArrayType(jString)

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
            
        for pname,pval in (('ITEMTYPE_T', '_ITEMTYPE'),
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
# automatically implement if application.  See the pypy/Callback.java,
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
        from pypy.translator.jvm.generator import Method
        for methname, methspec in self.OOTYPE._class_._methods.items():
            argtypes = [self.db.annotation_to_cts(arg._type) for arg in
                        methspec.args]
            restype = self.db.annotation_to_cts(methspec.retval._type)
            self.methods[methname] = Method.v(self, methname,
                                              argtypes, restype)

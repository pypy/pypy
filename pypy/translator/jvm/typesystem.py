"""
Translation between PyPy ootypesystem and JVM type system.

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

WeakRefs can hopefully map to Java Weak References in a straight
forward fashion.

Collections can hopefully map to Java collections instances.  Note
that JVM does not have an idea of generic typing at its lowest level
(well, they do have signature attributes, but those don't really count
for much).

"""
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype
from pypy.translator.jvm.option import getoption
from pypy.translator.jvm.log import log

class JvmType(str):
    """
    The class we use to represent JVM types; it is just a string with
    the JVM type descriptor at the moment.  Using JvmType allows us to
    use isinstance, however. The grammar for type descriptors can be
    read about here:
    http://java.sun.com/docs/books/vmspec/2nd-edition/html/ClassFile.doc.html
    """
    def is_scalar(self):
        return self[0] != 'L' and self[0] != '['
    def is_reference(self):
        return not self.is_scalar()
    def is_array(self):
        return self[0] == '['
    def int_class_name(self):
        """ Converts a descriptor like Ljava/lang/Object; to
        java/lang/Object """
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

def jvm_array_of(jtype):
    """ Returns a JvmType representing an array of 'jtype', which must be
    another JvmType """
    assert isinstance(jtype, JvmType)
    return JvmType('['+str(jtype))

def jvm_for_class(classnm):
    """ Returns a JvmType representing a particular class 'classnm', which
    should be a fully qualified java class name (i.e., 'java.lang.String') """
    return JvmType('L%s;' % classnm.replace('.','/'))

# Common JVM types
jVoid = JvmType('V')
jInt = JvmType('I')
jLong = JvmType('J')
jBool = JvmType('Z')
jDouble = JvmType('D')
jByte = JvmType('B')
jByteArray = jvm_array_of(jByte)
jChar = JvmType('C')
jThrowable = jvm_for_class('java.lang.Throwable')
jObject = jvm_for_class('java.lang.Object')
jString = jvm_for_class('java.lang.String')
jStringArray = jvm_array_of(jString)
jArrayList = jvm_for_class('java.util.ArrayList')
jHashMap = jvm_for_class('java.util.HashMap')
jIterator = jvm_for_class('java.util.Iterator')
jClass = jvm_for_class('java.lang.Class')
jStringBuilder = jvm_for_class('java.lang.StringBuilder')

# Map from OOType to an internal JVM type descriptor
_lltype_to_jvm = {
    ootype.Void:             jVoid,
    ootype.Signed:           jInt,
    ootype.Unsigned:         jInt,
    lltype.SignedLongLong:   jLong,
    lltype.UnsignedLongLong: jLong,
    ootype.Bool:             jBool,
    ootype.Float:            jDouble,
    ootype.Char:             jByte,
    ootype.UniChar:          jChar,
    ootype.String:           jByteArray,
    ootype.ROOT:             jObject,

    # We may want to use PyPy wrappers here later:
    llmemory.WeakGcAddress:  jObject, # XXX
    ootype.StringBuilder:    jStringBuilder,
    ootype.Class:            jClass,
    ootype.List:             jArrayList,
    ootype.Dict:             jHashMap,
    ootype.DictItemsIterator:jIterator
    }

# Method descriptor construction
def jvm_method_desc(argtypes, rettype):
    """ A Java method has a descriptor, which is a string specified
    its argument and return types.  This function converts a list of
    argument types (JvmTypes) and the return type (also a JvmType),
    into one of these descriptor strings. """
    return "(%s)%s" % ("".join(argtypes), rettype)

class JvmTypeSystem(object):

    """ This object translates between the OOTypeSystem and JVM type
    descriptors. """

    def enforce_jvm(self, typ):
        if isinstance(typ, JvmType):
            return typ
        return self.ootype_to_jvm(typ)

    def ootype_to_jvm(self, oot):
        """ Returns an instance of JvmType corresponding to the given
        OOType """

        # Check the easy cases
        if oot in _lltype_to_jvm:
            return _lltype_to_jvm[oot]

        # Now handle the harder ones
        if isinstance(oot, lltype.Ptr) and isinstance(t.TO, lltype.OpaqueType):
            return jObject
        if isinstance(oot, ootype.Instance):
            return XXX
        if isinstance(oot, ootype.Record):
            return XXX
        if isinstance(oot, ootype.StaticMethod):
            return XXX

        # Uh-oh
        unhandled_case


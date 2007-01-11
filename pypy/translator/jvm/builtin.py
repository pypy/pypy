from pypy.translator.jvm import typesystem as jvmtype
from pypy.translator.jvm import generator as jvmgen
from pypy.rpython.ootypesystem import ootype
from pypy.translator.jvm.typesystem import \
     jInt, jVoid, jStringBuilder, jString, jPyPy, jChar, jArrayList, jObject

# ______________________________________________________________________
# Mapping of built-in OOTypes to JVM types

class JvmBuiltInType(jvmtype.JvmClassType):
    
    """
    Represents built-in types to JVM.  May optionally be associated
    with an OOTYPE; if it is, then we will support lookup of the OOTYPE
    methods and will re-map them as needed to the JVM equivalents.
    """
    
    def __init__(self, db, classty, OOTYPE):
        jvmtype.JvmClassType.__init__(self, classty.name)
        self.db = db
        self.OOTYPE = OOTYPE           # might be None
    
        # We need to create a mapping for any generic parameters this
        # OOTYPE may have. Other than SELFTYPE_T, we map each generic
        # argument to ootype.ROOT.  We use a hack here where we assume
        # that the only generic parameters are named SELFTYPE_T,
        # ITEMTYPE_T, KEYTYPE_T, or VALUETYPE_T.
        self.generics = {}
        if hasattr(self.OOTYPE, 'SELFTYPE_T'):
            self.generics[self.OOTYPE.SELFTYPE_T] = self.OOTYPE
        for param in ('ITEMTYPE_T', 'KEYTYPE_T', 'VALUETYPE_T'):
            if hasattr(self.OOTYPE, param):
                self.generics[getattr(self.OOTYPE, param)] = ootype.ROOT

    def lookup_field(self, fieldnm):
        """ Given a field name, returns a jvmgen.Field object """
        _, FIELDTY = self.OOTYPE._lookup_field(fieldnm)
        jfieldty = self.db.lltype_to_cts(FIELDTY)
        return jvmgen.Field(
            self.descriptor.class_name(), fieldnm, jfieldty, False)

    def _map(self, ARG):
        """ Maps ootype ARG to a java type.  If arg is one of our
        generic arguments, substitutes the appropriate type before
        performing the mapping. """
        return self.db.lltype_to_cts(self.generics.get(ARG,ARG))

    def lookup_method(self, methodnm):
        """ Given the method name, returns a jvmgen.Method object """

        # Look for a shortcut method
        try:
            key = (self.OOTYPE.__class__, methodnm)
            print "key=%r" % (key,)
            print "hash=%r" % (built_in_methods,)
            return built_in_methods[key]
        except KeyError: pass

        # Lookup the generic method by name.
        GENMETH = self.OOTYPE._GENERIC_METHODS[methodnm]

        # Create an array with the Java version of each type in the
        # argument list and return type.
        jargtypes = [self._map(P) for P in GENMETH.ARGS]
        jrettype = self._map(GENMETH.RESULT)
        return jvmgen.Method.v(self, methodnm, jargtypes, jrettype)

# When we lookup a method on a  BuiltInClassNode, we first check
# the 'built_in_methods' table.  This allows us to redirect to other
# methods if we like.

def _ll_build_method():
    # Choose an appropriate ll_build depending on what representation
    # we are using for ootype.String:
    if True: # XXX db.using_byte_array...
        return jvmgen.Method.v(
            jStringBuilder, "toString", (),jString)
    return jvmgen.Method.s(
        jvmgen.PYPYJAVA, "ll_build", (jStringBuilder,), jOOString)

built_in_methods = {

    # Note: String and StringBuilder are rebound in ootype, and thus
    # .__class__ is required
    
    (ootype.StringBuilder.__class__, "ll_allocate"):
    jvmgen.Method.v(jStringBuilder, "ensureCapacity", (jInt,), jVoid),
    
    (ootype.StringBuilder.__class__, "ll_append_char"):
    jvmgen.Method.s(jPyPy, "ll_append_char", (jStringBuilder, jChar), jVoid),
    
    (ootype.StringBuilder.__class__, "ll_append"):
    jvmgen.Method.s(jPyPy, "ll_append", (jStringBuilder, jString), jVoid),

    (ootype.StringBuilder.__class__, "ll_build"):
     _ll_build_method(),

    (ootype.List, "ll_length"):
    jvmgen.Method.v(jArrayList, "size", (), jInt),

    (ootype.List, "ll_getitem_fast"):
    jvmgen.Method.v(jArrayList, "get", (jInt,), jObject),

    (ootype.List, "ll_setitem_fast"):
    jvmgen.Method.s(jPyPy, "ll_setitem_fast",
                    (jArrayList, jInt, jObject), jVoid),

    (ootype.List, "_ll_resize_ge"):
    jvmgen.Method.s(jPyPy, "_ll_resize_ge", (jArrayList, jInt), jVoid),

    (ootype.List, "_ll_resize_le"):
    jvmgen.Method.s(jPyPy, "_ll_resize_le", (jArrayList, jInt), jVoid),

    (ootype.List, "_ll_resize"):
    jvmgen.Method.s(jPyPy, "_ll_resize", (jArrayList, jInt), jVoid),

    }

from pypy.translator.jvm import typesystem as jvmtype
from pypy.translator.jvm import generator as jvmgen
from pypy.rpython.ootypesystem import ootype
from pypy.translator.jvm.typesystem import \
     jInt, jVoid, jStringBuilder, jString, jPyPy, jChar, jArrayList, jObject, \
     jBool

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

    def __eq__(self, other):
        return isinstance(other, JvmBuiltInType) and other.name == self.name

    def __hash__(self):
        return hash(self.name)

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

        # By default, we assume it is a static method on the PyPy
        # object, that takes an instance of this object as the first
        # argument.  The other arguments we just convert to java versions,
        # except for generics.
        jargtypes = [self] + [self._map(P) for P in GENMETH.ARGS]
        jrettype = self._map(GENMETH.RESULT)
        return jvmgen.Method.s(jPyPy, methodnm, jargtypes, jrettype)

# When we lookup a method on a  BuiltInClassNode, we first check
# the 'built_in_methods' table.  This allows us to redirect to other
# methods if we like.

built_in_methods = {

    # Note: String and StringBuilder are rebound in ootype, and thus
    # .__class__ is required
    
    (ootype.StringBuilder.__class__, "ll_allocate"):
    jvmgen.Method.v(jStringBuilder, "ensureCapacity", (jInt,), jVoid),
    
    (ootype.StringBuilder.__class__, "ll_build"):
    jvmgen.Method.v(jStringBuilder, "toString", (), jString),

    (ootype.String.__class__, "ll_streq"):
    jvmgen.Method.v(jString, "equals", (jObject,), jBool),

    (ootype.String.__class__, "ll_strlen"):
    jvmgen.Method.v(jString, "length", (), jInt),

    (ootype.List, "ll_length"):
    jvmgen.Method.v(jArrayList, "size", (), jInt),

    (ootype.List, "ll_getitem_fast"):
    jvmgen.Method.v(jArrayList, "get", (jInt,), jObject),

    }

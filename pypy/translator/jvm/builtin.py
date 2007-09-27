from pypy.translator.jvm import typesystem as jvmtype
from pypy.translator.jvm import generator as jvmgen
from pypy.rpython.ootypesystem import ootype
from pypy.translator.jvm.typesystem import \
     jInt, jVoid, jStringBuilder, jString, jPyPy, jChar, jArrayList, jObject, \
     jBool, jHashMap, jPyPyDictItemsIterator, Generifier, jCharSequence, \
     jPyPyCustomDict

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
        self.OOTYPE = OOTYPE
        self.gen = Generifier(OOTYPE)
    
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

    def lookup_method(self, methodnm):
        """ Given the method name, returns a jvmgen.Method object """

        # Look for a shortcut method in our table of remappings:
        try:
            key = (self.OOTYPE.__class__, methodnm)
            return built_in_methods[key]
        except KeyError: pass

        # Otherwise, determine the Method object automagically
        #   First, map the OOTYPE arguments and results to
        #   the java types they will be at runtime.  Note that
        #   we must use the erased types for this.
        ARGS, RESULT = self.gen.erased_types(methodnm)
        jargtypes = [self.db.lltype_to_cts(P) for P in ARGS]
        jrettype = self.db.lltype_to_cts(RESULT)
        
        if self.OOTYPE.__class__ in bridged_objects:
            # Bridged objects are ones where we have written a java class
            # that has methods with the correct names and types already
            return jvmgen.Method.v(self, methodnm, jargtypes, jrettype)
        else:
            # By default, we assume it is a static method on the PyPy
            # object, that takes an instance of this object as the first
            # argument.  The other arguments we just convert to java versions,
            # except for generics.
            jargtypes = [self] + jargtypes
            return jvmgen.Method.s(jPyPy, methodnm, jargtypes, jrettype)

# When we lookup a method on a BuiltInClassNode, we first check the
# 'built_in_methods' and 'bridged_objects' tables.  This allows us to
# redirect to other methods if we like.

bridged_objects = (
    ootype.DictItemsIterator,
    ootype.WeakReference.__class__
    )

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
    
    (ootype.String.__class__, "ll_stritem_nonneg"):
    jvmgen.Method.v(jString, "charAt", (jInt,), jChar),

    (ootype.String.__class__, "ll_startswith"):
    jvmgen.Method.v(jString, "startsWith", (jString,), jBool),

    (ootype.String.__class__, "ll_endswith"):
    jvmgen.Method.v(jString, "endsWith", (jString,), jBool),

    (ootype.String.__class__, "ll_strcmp"):
    jvmgen.Method.v(jString, "compareTo", (jString,), jInt),

    (ootype.String.__class__, "ll_upper"):
    jvmgen.Method.v(jString, "toUpperCase", (), jString),

    (ootype.String.__class__, "ll_lower"):
    jvmgen.Method.v(jString, "toLowerCase", (), jString),

    (ootype.String.__class__, "ll_replace_chr_chr"):
    jvmgen.Method.v(jString, "replace", (jChar, jChar), jString),

    (ootype.Dict, "ll_set"):
    jvmgen.Method.v(jHashMap, "put", (jObject, jObject), jObject),
    
    (ootype.Dict, "ll_get"):
    jvmgen.Method.v(jHashMap, "get", (jObject,), jObject),

    (ootype.Dict, "ll_contains"):
    jvmgen.Method.v(jHashMap, "containsKey", (jObject,), jBool),

    (ootype.Dict, "ll_length"):
    jvmgen.Method.v(jHashMap, "size", (), jInt),
    
    (ootype.Dict, "ll_clear"):
    jvmgen.Method.v(jHashMap, "clear", (), jVoid),

    (ootype.CustomDict, "ll_set"):
    jvmgen.Method.v(jPyPyCustomDict, "put", (jObject, jObject), jObject),
    
    (ootype.CustomDict, "ll_get"):
    jvmgen.Method.v(jPyPyCustomDict, "get", (jObject,), jObject),

    (ootype.CustomDict, "ll_contains"):
    jvmgen.Method.v(jPyPyCustomDict, "containsKey", (jObject,), jBool),

    (ootype.CustomDict, "ll_length"):
    jvmgen.Method.v(jPyPyCustomDict, "size", (), jInt),
    
    (ootype.CustomDict, "ll_clear"):
    jvmgen.Method.v(jPyPyCustomDict, "clear", (), jVoid),

    (ootype.List, "ll_length"):
    jvmgen.Method.v(jArrayList, "size", (), jInt),

    (ootype.List, "ll_getitem_fast"):
    jvmgen.Method.v(jArrayList, "get", (jInt,), jObject),

    }

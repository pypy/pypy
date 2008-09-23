"""
The database centralizes information about the state of our translation,
and the mapping between the OOTypeSystem and the Java type system.
"""

from cStringIO import StringIO
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype, rclass
from pypy.rpython.ootypesystem.module import ll_os
from pypy.translator.jvm import node, methods
from pypy.translator.jvm.option import getoption
from pypy.translator.jvm.builtin import JvmBuiltInType
from pypy.translator.oosupport.database import Database as OODatabase
from pypy.rpython.ootypesystem.bltregistry import ExternalType
from pypy.annotation.signature import annotation
from pypy.annotation.model import annotation_to_lltype
import pypy.translator.jvm.constant as jvmconst
import pypy.translator.jvm.typesystem as jvm

# ______________________________________________________________________
# Database object

class Database(OODatabase):
    def __init__(self, genoo):
        OODatabase.__init__(self, genoo)
        
        # Private attributes:
        self._jasmin_files = [] # list of strings --- .j files we made
        self._classes = {} # Maps ootype class objects to node.Class objects,
                           # and JvmType objects as well
        self._functions = {}      # graph -> jvm.Method

        # (jargtypes, jrettype) -> node.StaticMethodInterface
        self._delegates = {}

        # (INSTANCE, method_name) -> node.StaticMethodImplementation
        self._bound_methods = {}

        self._function_names = {} # graph --> function_name

        self._constants = {}      # flowmodel.Variable --> jvm.Const

#        # Special fields for the Object class, see _translate_Object
#        self._object_interf = None
#        self._object_impl = None
#        self._object_exc_impl = None
#
        # Create information about the Main class we will build:
        #
        #    It will have two static fields, 'ilink' and 'pypy'.  The
        #    first points to an instance of the interface pypy.Interlink
        #    which we will be generated.  The second points to an instance
        #    of pypy.PyPy which was created with this Interlink instance.
        #
        #    The Interlink class provides the bridge between static helper
        #    code and dynamically generated classes.  Since there is one
        #    Main per set of translated code, this also allows multiple
        #    PyPy interpreters to overlap with one another.
        #
        #    These are public attributes that are referenced from
        #    elsewhere in the code using
        #    jvm.Generator.push_interlink() and .push_pypy().
        self.jPyPyMain = jvm.JvmClassType(self._pkg('Main'))
        self.pypy_field = jvm.Field.s(self.jPyPyMain, 'pypy', jvm.jPyPy)
        self.interlink_field = jvm.Field.s(self.jPyPyMain, 'ilink',
                                           jvm.jPyPyInterlink)

    # _________________________________________________________________
    # Java String vs Byte Array
    #
    # We allow the user to configure whether Python strings are stored
    # as Java strings, or as byte arrays.  The latter saves space; the
    # former may be faster.  

    using_byte_array = False

    # XXX have to fill this in
    
    # _________________________________________________________________
    # Miscellaneous
    
    def _uniq(self, nm):
        return nm + "_" + str(self.unique())

    def _pkg(self, nm):
        return "%s.%s" % (getoption('package'), nm)

    def class_name(self, TYPE):
        jtype = self.lltype_to_cts(TYPE)
        assert isinstance(jtype, jvm.JvmClassType)
        return jtype.name

    def add_jasmin_file(self, jfile):
        """ Adds to the list of files we need to run jasmin on """
        self._jasmin_files.append(jfile)

    def jasmin_files(self):
        """ Returns list of files we need to run jasmin on """
        return self._jasmin_files

    def is_Object(self, OOTYPE):
        return isinstance(OOTYPE, ootype.Instance) and OOTYPE._name == "Object"

    # _________________________________________________________________
    # Node Creation
    #
    # Creates nodes that represents classes, functions, simple constants.

    def create_interlink_node(self, methods):
        """ This is invoked by create_interlinke_node() in
        jvm/prebuiltnodes.py.  It creates a Class node that will
        be an instance of the Interlink interface, which is used
        to allow the static java code to throw PyPy exceptions and the
        like.

        The 'methods' argument should be a dictionary whose keys are
        method names and whose entries are jvm.Method objects which
        the corresponding method should invoke. """

        nm = self._pkg(self._uniq('InterlinkImplementation'))
        cls = node.Class(nm, supercls=jvm.jObject)
        for method_name, helper in methods.items():
            cls.add_method(node.InterlinkFunction(cls, method_name, helper))
        cls.add_interface(jvm.jPyPyInterlink)
        self.jInterlinkImplementation = cls
        self.pending_node(cls)

    def types_for_graph(self, graph):
        """
        Given a graph, returns a tuple like so:
          ( (java argument types...), java return type )
        For example, if the graph took two strings and returned a bool,
        then the return would be:
          ( (jString, jString), jBool )
        """
        ARGS = [v.concretetype for v in graph.getargs()]
        RESULT = graph.getreturnvar().concretetype
        return self.types_for_signature(ARGS, RESULT)

    def types_for_signature(self, ARGS, RESULT):
        ARGS = [ARG for ARG in ARGS if ARG is not ootype.Void]
        jargtypes = tuple([self.lltype_to_cts(ARG) for ARG in ARGS])
        jrettype = self.lltype_to_cts(RESULT)
        return jargtypes, jrettype
    
    def _function_for_graph(self, classobj, funcnm, is_static, graph):
        
        """
        Creates a node.Function object for a particular graph.  Adds
        the method to 'classobj', which should be a node.Class object.
        """
        jargtypes, jrettype = self.types_for_graph(graph)
        funcobj = node.GraphFunction(
            self, classobj, funcnm, jargtypes, jrettype, graph, is_static)
        return funcobj
    
    def _translate_record(self, OOTYPE):
        assert OOTYPE is not ootype.ROOT

        # Create class object if it does not already exist:
        if OOTYPE in self._classes:
            return self._classes[OOTYPE]

        # Create the class object first
        clsnm = self._pkg(self._uniq('Record'))
        clsobj = node.Class(clsnm, jvm.jObject)
        self._classes[OOTYPE] = clsobj

        # Add fields:
        self._translate_class_fields(clsobj, OOTYPE)

        # generate toString
        dump_method = methods.RecordDumpMethod(self, OOTYPE, clsobj)
        clsobj.add_method(dump_method)

        # generate equals and hash
        equals_method = methods.DeepEqualsMethod(self, OOTYPE, clsobj)
        clsobj.add_method(equals_method)
        hash_method = methods.DeepHashMethod(self, OOTYPE, clsobj)
        clsobj.add_method(hash_method)

        self.pending_node(clsobj)
        return clsobj

    def _translate_superclass_of(self, OOSUB):
        """
        Invoked to translate OOSUB's super class.  Normally just invokes
        pending_class, but we treat "Object" differently so that we can
        make all exceptions descend from Throwable.
        """
        OOSUPER = OOSUB._superclass
        if OOSUB._name == "exceptions.Exception":
            return jvm.jPyPyThrowable
        return self.pending_class(OOSUPER)

    def _translate_instance(self, OOTYPE):
        assert isinstance(OOTYPE, ootype.Instance)
        assert OOTYPE is not ootype.ROOT

        # Create class object if it does not already exist:
        if OOTYPE in self._classes:
            return self._classes[OOTYPE]

        # Create the class object first
        clsnm = self._pkg(self._uniq(OOTYPE._name))
        clsobj = node.Class(clsnm)
        self._classes[OOTYPE] = clsobj

        # Resolve super class 
        assert OOTYPE._superclass
        supercls = self._translate_superclass_of(OOTYPE)
        clsobj.set_super_class(supercls)

        # TODO --- mangle field and method names?  Must be
        # deterministic, or use hashtable to avoid conflicts between
        # classes?
        
        # Add fields:
        self._translate_class_fields(clsobj, OOTYPE)
            
        # Add methods:
        for mname, mimpl in OOTYPE._methods.iteritems():
            if not hasattr(mimpl, 'graph'):
                # Abstract method
                METH = mimpl._TYPE
                arglist = [self.lltype_to_cts(ARG) for ARG in METH.ARGS
                           if ARG is not ootype.Void]
                returntype = self.lltype_to_cts(METH.RESULT)
                clsobj.add_abstract_method(jvm.Method.v(
                    clsobj, mname, arglist, returntype))
            else:
                # if the first argument's type is not a supertype of
                # this class it means that this method this method is
                # not really used by the class: don't render it, else
                # there would be a type mismatch.
                args =  mimpl.graph.getargs()
                SELF = args[0].concretetype
                if not ootype.isSubclass(OOTYPE, SELF): continue
                mobj = self._function_for_graph(
                    clsobj, mname, False, mimpl.graph)
                clsobj.add_method(mobj)

        # currently, we always include a special "dump" method for debugging
        # purposes
        dump_method = node.InstanceDumpMethod(self, OOTYPE, clsobj)
        clsobj.add_method(dump_method)

        self.pending_node(clsobj)
        return clsobj

    def _translate_class_fields(self, clsobj, OOTYPE):
        for fieldnm, (FIELDOOTY, fielddef) in OOTYPE._fields.iteritems():
            if FIELDOOTY is ootype.Void: continue
            fieldty = self.lltype_to_cts(FIELDOOTY)
            clsobj.add_field(
                jvm.Field(clsobj.name, fieldnm, fieldty, False, FIELDOOTY),
                fielddef)

    def pending_class(self, OOTYPE):
        return self.lltype_to_cts(OOTYPE)

    def pending_function(self, graph):
        """
        This is invoked when a standalone function is to be compiled.
        It creates a class named after the function with a single
        method, invoke().  This class is added to the worklist.
        Returns a jvm.Method object that allows this function to be
        invoked.
        """
        if graph in self._functions:
            return self._functions[graph]
        classnm = self._pkg(self._uniq(graph.name))
        classobj = node.Class(classnm, self.pending_class(ootype.ROOT))
        funcobj = self._function_for_graph(classobj, "invoke", True, graph)
        classobj.add_method(funcobj)
        self.pending_node(classobj)
        res = self._functions[graph] = funcobj.method()
        return res

    def record_delegate(self, TYPE):
        """
        Creates and returns a StaticMethodInterface type; this type
        represents an abstract base class for functions with a given
        signature, represented by TYPE, a ootype.StaticMethod
        instance.
        """

        # Translate argument/return types into java types, check if
        # we already have such a delegate:
        jargs = tuple([self.lltype_to_cts(ARG) for ARG in TYPE.ARGS
                       if ARG is not ootype.Void])
        jret = self.lltype_to_cts(TYPE.RESULT)
        return self.record_delegate_sig(jargs, jret)

    def record_delegate_sig(self, jargs, jret):
        """
        Like record_delegate, but the signature is in terms of java
        types.  jargs is a list of JvmTypes, one for each argument,
        and jret is a Jvm.  Note that jargs does NOT include an
        entry for the this pointer of the resulting object.  
        """
        key = (jargs, jret)
        if key in self._delegates:
            return self._delegates[key]

        # TODO: Make an intelligent name for this interface by
        # mangling the list of parameters
        name = self._pkg(self._uniq('Delegate'))

        # Create a new one if we do not:
        interface = node.StaticMethodInterface(name, jargs, jret)
        self._delegates[key] = interface
        self.pending_node(interface)
        return interface
    
    def record_delegate_standalone_func_impl(self, graph):
        """
        Creates a class with an invoke() method that invokes the given
        graph.  This object can be used as a function pointer.  It
        will extend the appropriate delegate for the graph's
        signature.
        """
        jargtypes, jrettype = self.types_for_graph(graph)
        super_class = self.record_delegate_sig(jargtypes, jrettype)
        pfunc = self.pending_function(graph)
        implnm = self._pkg(self._uniq(graph.name+'_delegate'))
        n = node.StaticMethodImplementation(implnm, super_class, None, pfunc)
        self.pending_node(n)
        return n

    def record_delegate_bound_method_impl(self, INSTANCE, method_name):
        """
        Creates an object with an invoke() method which invokes
        a method named method_name on an instance of INSTANCE.
        """
        key = (INSTANCE, method_name)
        if key in self._bound_methods:
            return self._bound_methods[key]
        METH_TYPE = INSTANCE._lookup(method_name)[1]._TYPE
        super_class = self.record_delegate(METH_TYPE)
        self_class = self.lltype_to_cts(INSTANCE)
        mthd_obj = self_class.lookup_method(method_name)
        implnm = self._pkg(self._uniq(
            self_class.simple_name()+"_"+method_name+"_delegate"))
        n = self._bound_methods[key] = node.StaticMethodImplementation(
            implnm, super_class, self_class, mthd_obj)
        self.pending_node(n)
        return n

    # _________________________________________________________________
    # toString functions
    #
    # Obtains an appropriate method for serializing an object of
    # any type.
    
    _toString_methods = {
        ootype.Signed:jvm.INTTOSTRINGI,
        ootype.Unsigned:jvm.PYPYSERIALIZEUINT,
        ootype.SignedLongLong:jvm.LONGTOSTRINGL,
        ootype.UnsignedLongLong: jvm.PYPYSERIALIZEULONG,
        ootype.Float:jvm.DOUBLETOSTRINGD,
        ootype.Bool:jvm.PYPYSERIALIZEBOOLEAN,
        ootype.Void:jvm.PYPYSERIALIZEVOID,
        ootype.Char:jvm.PYPYESCAPEDCHAR,
        ootype.UniChar:jvm.PYPYESCAPEDUNICHAR,
        ootype.String:jvm.PYPYESCAPEDSTRING,
        ootype.Unicode:jvm.PYPYESCAPEDUNICODE,
        }

    def toString_method_for_ootype(self, OOTYPE):
        """
        Assuming than an instance of type OOTYPE is pushed on the
        stack, returns a Method object that you can invoke.  This method
        will return a string representing the contents of that type.

        Do something like:
        
        > gen.load(var)
        > mthd = db.toString_method_for_ootype(var.concretetype)
        > mthd.invoke(gen)

        to print the value of 'var'.
        """
        return self._toString_methods.get(OOTYPE, jvm.PYPYSERIALIZEOBJECT)

    # _________________________________________________________________
    # Type translation functions
    #
    # Functions which translate from OOTypes to JvmType instances.
    # FIX --- JvmType and their Class nodes should not be different.

    def escape_name(self, nm):
        # invoked by oosupport/function.py; our names don't need escaping?
        return nm

    def llvar_to_cts(self, llv):
        """ Returns a tuple (JvmType, str) with the translated type
        and name of the given variable"""
        return self.lltype_to_cts(llv.concretetype), llv.name

    # Dictionary for scalar types; in this case, if we see the key, we
    # will return the value
    ootype_to_scalar = {
        ootype.Void:             jvm.jVoid,
        ootype.Signed:           jvm.jInt,
        ootype.Unsigned:         jvm.jInt,
        ootype.SignedLongLong:   jvm.jLong,
        ootype.UnsignedLongLong: jvm.jLong,
        ootype.Bool:             jvm.jBool,
        ootype.Float:            jvm.jDouble,
        ootype.Char:             jvm.jChar,    # byte would be sufficient, but harder
        ootype.UniChar:          jvm.jChar,
        ootype.Class:            jvm.jClass,
        ootype.ROOT:             jvm.jObject,  # treat like a scalar
    }

    # Dictionary for non-scalar types; in this case, if we see the key, we
    # will return a JvmBuiltInType based on the value
    ootype_to_builtin = {
        ootype.String:           jvm.jString,
        ootype.Unicode:          jvm.jString,
        ootype.StringBuilder:    jvm.jStringBuilder,
        ootype.UnicodeBuilder:   jvm.jStringBuilder,
        ootype.List:             jvm.jArrayList,
        ootype.Dict:             jvm.jHashMap,
        ootype.DictItemsIterator:jvm.jPyPyDictItemsIterator,
        ootype.CustomDict:       jvm.jPyPyCustomDict,
        ootype.WeakReference:    jvm.jPyPyWeakRef,
        ll_os.STAT_RESULT:       jvm.jPyPyStatResult,

        # These are some configured records that are generated by Java
        # code.  
        #ootype.Record({"item0": ootype.Signed, "item1": ootype.Signed}):
        #jvm.jPyPyRecordSignedSigned,
        #ootype.Record({"item0": ootype.Float, "item1": ootype.Signed}):
        #jvm.jPyPyRecordFloatSigned,
        #ootype.Record({"item0": ootype.Float, "item1": ootype.Float}):
        #jvm.jPyPyRecordFloatFloat,
        #ootype.Record({"item0": ootype.String, "item1": ootype.String}):
        #jvm.jPyPyRecordStringString,        
        }

    def lltype_to_cts(self, OOT):
        import sys
        res = self._lltype_to_cts(OOT)
        return res

    def _lltype_to_cts(self, OOT):
        """ Returns an instance of JvmType corresponding to
        the given OOType """

        # Handle built-in types:
        if OOT in self.ootype_to_scalar:
            return self.ootype_to_scalar[OOT]
        if (isinstance(OOT, lltype.Ptr) and
            isinstance(OOT.TO, lltype.OpaqueType)):
            return jvm.jObject
        if OOT in self.ootype_to_builtin:
            return JvmBuiltInType(self, self.ootype_to_builtin[OOT], OOT)
        if isinstance(OOT, ootype.Array):
            return self._array_type(OOT.ITEM)
        if OOT.__class__ in self.ootype_to_builtin:
            return JvmBuiltInType(
                self, self.ootype_to_builtin[OOT.__class__], OOT)

        # Handle non-built-in-types:
        if isinstance(OOT, ootype.Instance):
            if self.is_Object(OOT):
                return self._translate_Object(OOT)
            return self._translate_instance(OOT)
        if isinstance(OOT, ootype.Record):
            return self._translate_record(OOT)
        if isinstance(OOT, ootype.StaticMethod):
            return self.record_delegate(OOT)

        # handle externals
        if isinstance(OOT, ExternalType):
            return jvm.JvmNativeClass(self, OOT)
        
        assert False, "Untranslatable type %s!" % OOT

    ooitemtype_to_array = {
        ootype.Signed   : jvm.jIntArray,
        ootype.Unsigned : jvm.jIntArray,
        ootype.Char     : jvm.jCharArray,
        ootype.Bool     : jvm.jBoolArray,
        ootype.UniChar  : jvm.jCharArray,
        ootype.String   : jvm.jStringArray,
        ootype.Float    : jvm.jDoubleArray,
        ootype.Void     : jvm.jVoidArray,
    }

    def _array_type(self, ITEM):
        if ITEM in self.ooitemtype_to_array:
            return self.ooitemtype_to_array[ITEM]
        return jvm.jObjectArray

    def annotation_to_cts(self, _tp):
        s_tp = annotation(_tp)
        TP = annotation_to_lltype(s_tp)
        return self.lltype_to_cts(TP)

    # _________________________________________________________________
    # Uh....
    #
    # These functions are invoked by the code in oosupport, but I
    # don't think we need them or use them otherwise.

    def record_function(self, graph, name):
        self._function_names[graph] = name

    def graph_name(self, graph):
        # XXX: graph name are not guaranteed to be unique
        return self._function_names.get(graph, None)

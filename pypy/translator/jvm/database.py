"""
The database tracks which graphs have already been generated, and maintains
a worklist.  It also contains a pointer to the type system.  It is passed
into every node for generation along with the generator.
"""
from cStringIO import StringIO
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.translator.jvm.typesystem import jvm_method_desc, ootype_to_jvm
from pypy.translator.jvm import node
from pypy.translator.jvm.option import getoption
import pypy.translator.jvm.generator as jvmgen
import pypy.translator.jvm.typesystem as jvmtypes

class BuiltInClassNode(object):

    """
    This is a fake node that is returned instead of a node.Class object
    when pending_class is invoked on a built-in type.  It allows other
    code to query the fields and methods.
    """
    
    def __init__(self, db, OOTYPE):
        self.db = db
        self.OOTYPE = OOTYPE
        self.jvmtype = db.lltype_to_cts(OOTYPE)

        # Create a generic mapping. Other than SELFTYPE_T, we map each
        # generic argument to ootype.ROOT.  We use a hack here where
        # we assume that the only generic parameters are named
        # SELFTYPE_T, ITEMTYPE_T, KEYTYPE_T, or VALUETYPE_T.
        
        self.generics = {}

        if hasattr(self.OOTYPE, 'SELFTYPE_T'):
            self.generics[self.OOTYPE.SELFTYPE_T] = self.OOTYPE

        for param in ('ITEMTYPE_T', 'KEYTYPE_T', 'VALUETYPE_T'):
            if hasattr(self.OOTYPE, param):
                self.generics[getattr(self.OOTYPE, param)] = ootype.ROOT

    def jvm_type(self):
        return self.jvmtype

    def lookup_field(self, fieldnm):
        """ Given a field name, returns a jvmgen.Field object """
        _, FIELDTY = self.OOTYPE._lookup_field(fieldnm)
        jfieldty = self.db.lltype_to_cts(FIELDTY)
        return jvmgen.Field(
            self.jvmtype.class_name(), fieldnm, jfieldty, False)

    def _map(self, ARG):
        """ Maps ootype ARG to a java type.  If arg is one of our
        generic arguments, substitutes the appropriate type before
        performing the mapping. """
        return self.db.lltype_to_cts(self.generics.get(ARG,ARG))

    def lookup_method(self, methodnm):
        """ Given the method name, returns a jvmgen.Method object """

        # Lookup the generic method by name.
        GENMETH = self.OOTYPE._GENERIC_METHODS[methodnm]

        # Create an array with the Java version of each type in the
        # argument list and return type.
        jargtypes = [self._map(P) for P in GENMETH.ARGS]
        jrettype = self._map(GENMETH.RESULT)
        return jvmgen.Method(
            self.jvmtype.class_name(),
            methodnm,
            jvm_method_desc(jargtypes, jrettype),
            opcode=jvmgen.INVOKEVIRTUAL)
        

class Database:
    def __init__(self, genoo):
        # Public attributes:
        self.genoo = genoo
        
        # Private attributes:
        self._classes = {} # Maps ootype class objects to node.Class objects,
                           # and JvmType objects as well
        self._counter = 0  # Used to create unique names
        self._functions = {}      # graph -> jvmgen.Method

        self._function_names = {} # graph --> function_name

        self._constants = {}      # flowmodel.Variable --> jvmgen.Const

        self._pending_nodes = set()  # Worklist
        self._rendered_nodes = set()

    def _uniq(self, nm):
        cnt = self._counter
        self._counter += 1
        return nm + "_" + str(cnt) + "_"

    def _pkg(self, nm):
        return "%s.%s" % (getoption('package'), nm)

    def _function_for_graph(self, classobj, funcnm, is_static, graph):
        
        """
        Creates a node.Function object for a particular graph.  Adds
        the method to 'classobj', which should be a node.Class object.
        """
        argtypes = [arg.concretetype for arg in graph.getargs()
                    if arg.concretetype is not ootype.Void]
        jargtypes = [self.lltype_to_cts(argty) for argty in argtypes]
        rettype = graph.getreturnvar().concretetype
        jrettype = self.lltype_to_cts(rettype)
        funcobj = node.Function(
            self, classobj, funcnm, jargtypes, jrettype, graph, is_static)
        return funcobj

    def pending_node(self, node):
        self._pending_nodes.add(node)

    def pending_class(self, OOCLASS):
        if not isinstance(OOCLASS, ootype.Instance):
            return BuiltInClassNode(self, OOCLASS)

        # Create class object if it does not already exist:
        if OOCLASS in self._classes:
            return self._classes[OOCLASS]
        
        # Resolve super class first
        if OOCLASS._superclass:
            superclsnm = self.lltype_to_cts(OOCLASS._superclass).class_name()
        else:
            superclsobj = "java.lang.Object" #?

        # TODO --- make package of java class reflect the package of the
        # OO class?
        clsnm = self._pkg(
            self._uniq(OOCLASS._name.replace('.','_')))
        clsobj = node.Class(clsnm, superclsnm)

        # Store the class object for future calls
        self._classes[OOCLASS] = clsobj
        self._classes[clsobj.jvm_type()] = clsobj

        # TODO --- mangle field and method names?  Must be
        # deterministic, or use hashtable to avoid conflicts between
        # classes?
        
        # Add fields:
        for fieldnm, (FIELDOOTY, fielddef) in OOCLASS._fields.iteritems():
            if FIELDOOTY is ootype.Void: continue
            fieldty = self.lltype_to_cts(FIELDOOTY)
            clsobj.add_field(jvmgen.Field(clsnm, fieldnm, fieldty, False))
            
        # Add methods:
        for mname, mimpl in OOCLASS._methods.iteritems():
            if not hasattr(mimpl, 'graph'):
                # Abstract method
                TODO
            else:
                # if the first argument's type is not a supertype of
                # this class it means that this method this method is
                # not really used by the class: don't render it, else
                # there would be a type mismatch.
                args =  mimpl.graph.getargs()
                SELF = args[0].concretetype
                if not ootype.isSubclass(OOCLASS, SELF): continue
                mobj = self._function_for_graph(
                    clsobj, mname, False, mimpl.graph)
                clsobj.add_method(mobj)

        # currently, we always include a special "dump" method for debugging
        # purposes
        dump_method = node.TestDumpMethod(self, OOCLASS, clsobj)
        clsobj.add_dump_method(dump_method)

        self.pending_node(clsobj)
        return clsobj

    def class_obj_for_jvm_type(self, jvmtype):
        return self._classes[jvmtype]

    def pending_function(self, graph):
        """
        This is invoked when a standalone function is to be compiled.
        It creates a class named after the function with a single
        method, invoke().  This class is added to the worklist.
        Returns a jvmgen.Method object that allows this function to be
        invoked.
        """
        if graph in self._functions:
            return self._functions[graph]
        classnm = self._pkg(self._uniq(graph.name))
        classobj = node.Class(classnm, 'java.lang.Object')
        funcobj = self._function_for_graph(classobj, "invoke", True, graph)
        classobj.add_method(funcobj)
        self.pending_node(classobj)
        res = self._functions[graph] = funcobj.method()
        return res

    def len_pending(self):
        return len(self._pending_nodes)

    def pop(self):
        return self._pending_nodes.pop()

    def gen_constants(self, gen):
        pass

    def record_const(self, constobj):
        TYPE = constobj.concretetype

        # Handle the simple cases:
        if TYPE is ootype.Void:
            return jvmgen.VoidConst()
        elif TYPE in (ootype.Bool, ootype.Signed):
            return jvmgen.SignedIntConst(int(constobj.value))
        elif TYPE is ootype.Char or TYPE is ootype.UniChar:
            return jvmgen.SignedIntConst(ord(constobj.value))
        elif TYPE is ootype.SignedLongLong:
            return jvmgen.SignedLongConst(int(constobj.value))
        elif TYPE is ootype.UnsignedLongLong:
            return jvmgen.UnsignedLongConst(int(constobj.value))
        elif TYPE is ootype.Float:
            return jvmgen.DoubleConst(constobj.value)

        # Handle the complex cases:
        #   In this case, we will need to create a method to
        #   initialize the value and a field.
        #   For NOW, we create a new class PER constant.
        #   Clearly this is probably undesirable in the long
        #   term.
        return jvmgen.WarnNullConst() # TODO

    # Other
    
    _type_printing_methods = {
        ootype.Signed:jvmgen.PYPYDUMPINT,
        ootype.Unsigned:jvmgen.PYPYDUMPUINT,
        ootype.SignedLongLong:jvmgen.PYPYDUMPLONG,
        ootype.Float:jvmgen.PYPYDUMPDOUBLE,
        ootype.Bool:jvmgen.PYPYDUMPBOOLEAN,
        ootype.Class:jvmgen.PYPYDUMPOBJECT,
        ootype.String:jvmgen.PYPYDUMPSTRING,
        ootype.StringBuilder:jvmgen.PYPYDUMPOBJECT,
        }

    def generate_dump_method_for_ootype(self, OOTYPE):
        if OOTYPE in self._type_printing_methods:
            return self._type_printing_methods[OOTYPE]
        pclass = self.pending_class(OOTYPE)
        assert hasattr(pclass, 'dump_method'), "No dump_method for "+OOTYPE
        return pclass.dump_method.method()

    # Type translation functions

    def escape_name(self, nm):
        # invoked by oosupport/function.py; our names don't need escaping?
        return nm

    def llvar_to_cts(self, llv):
        """ Returns a tuple (JvmType, str) with the translated type
        and name of the given variable"""
        return self.lltype_to_cts(llv.concretetype), llv.name

    def lltype_to_cts(self, OOT):
        """ Returns an instance of JvmType corresponding to
        the given OOType"""

        # Check the easy cases
        if OOT in ootype_to_jvm:
            return ootype_to_jvm[OOT]

        # Now handle the harder ones
        if isinstance(OOT, lltype.Ptr) and isinstance(t.TO, lltype.OpaqueType):
            return jObject
        if isinstance(OOT, ootype.Instance):
            return self.pending_class(OOT).jvm_type()
        if isinstance(OOT, ootype.Record):
            return XXX
        if isinstance(OOT, ootype.StaticMethod):
            return XXX

        # Uh-oh
        unhandled_case

    # Invoked by genoo:
    #   I am not sure that we need them
    
    def record_function(self, graph, name):
        self._function_names[graph] = name

    def graph_name(self, graph):
        # XXX: graph name are not guaranteed to be unique
        return self._function_names.get(graph, None)

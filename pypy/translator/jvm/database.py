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

class Database:
    def __init__(self, genoo):
        # Public attributes:
        self.genoo = genoo
        
        # Private attributes:
        self._classes = {} # Maps ootype class objects to node.Class objects
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
        assert isinstance(OOCLASS, ootype.Instance)

        # Create class object if it does not already exist:
        if OOCLASS in self._classes:
            return self._classes[OOCLASS]
        # TODO --- make package of java class reflect the package of the
        # OO class?
        clsnm = self._pkg(
            self._uniq(OOCLASS._name.replace('.','_')))
        clsobj = node.Class(clsnm)

        # TODO --- mangle field and method names?  Must be deterministic or
        # use hashtable to avoid conflicts between classes?
        
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
                args =  m_meth.graph.getargs()
                SELF = args[0].concretetype
                if not ootype.isSubclass(OOCLASS, SELF): continue
                mobj = self._function_for_graph(
                    clsobj, mimpl.name, False, mimpl.graph)
                clsobj.add_method(mobj)

        self._classes[OOCLASS] = clsobj
        self.pending_node(clsobj)
        return clsobj

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
        classobj = node.Class(classnm)
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
        print "TYPE=" + repr(TYPE)
        return jvmgen.VoidConst() # TODO

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

"""
The database tracks which graphs have already been generated, and maintains
a worklist.  It also contains a pointer to the type system.  It is passed
into every node for generation along with the generator.
"""
from cStringIO import StringIO
from pypy.rpython.ootypesystem import ootype
from pypy.translator.jvm.typesystem import jvm_method_desc, ootype_to_jvm
from pypy.translator.jvm import node
import pypy.translator.jvm.generator as jvmgen
import pypy.translator.jvm.typesystem as jvmtypes

class Database:
    def __init__(self, genoo):
        # Public attributes:
        self.genoo = genoo
        
        # Private attributes:
        self._classes = {} # Maps ootype class objects to node.Class objects
        self._counter = 0  # Used to create unique names
        self._functions = {}     # graph -> jvmgen.Method

        self._function_names = {} # graph --> function_name

        self._pending_nodes = set()  # Worklist
        self._rendered_nodes = set()

    def _make_unique_name(self, nm):
        cnt = self._counter
        self._counter += 1
        return nm + "_" + str(cnt) + "_"

    def get_class_for(self, ooclass):
        """ Given an OOTypeSystem Instance object representing a user
        defined class (ooclass), returns a node.Class object representing
        its jvm counterpart. """

        # Create class object if it does not already exist:
        if ooclass in self._classes:
            return self._classes[ooclass]
        clname = self._make_unique_name(ooclass._name)
        clobj = self._classes[ooclass] = node.Class(clname)
        
        # Add fields:
        for fieldnm, (fieldty, fielddef) in ooclass._fields.iteritems():
            if ftype is ootype.Void: continue
            fieldnm = self._make_unique_name(fieldnm)
            fieldty = self.lltype_to_cts(ftype)
            clobj.add_field(fieldty, fieldnm) # TODO --- fielddef??
            
        # Add methods:
        for mname, mimpl in ooclass._methods.iteritems():
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
                if not ootype.isSubclass(ooclass, SELF): continue
                mobj = _function_for_graph(
                    clobj, mimpl.name, False, mimpl.graph)
                clobj.add_method(mobj)

        return clobj

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
        classnm = self._make_unique_name(graph.name)
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

    # Type translation functions

    def escape_name(self, nm):
        # invoked by oosupport/function.py; our names don't need escaping?
        return nm

    def llvar_to_cts(self, llv):
        """ Returns a tuple (JvmType, str) with the translated type
        and name of the given variable"""
        return self.lltype_to_cts(llv.concretetype), llv.name

    def lltype_to_cts(self, oot):
        """ Returns an instance of JvmType corresponding to
        the given OOType"""

        # Check the easy cases
        if oot in ootype_to_jvm:
            return ootype_to_jvm[oot]

        # Now handle the harder ones
        if isinstance(oot, ootype.Ptr) and isinstance(t.TO, ootype.OpaqueType):
            return jObject
        if isinstance(oot, ootype.Instance):
            return XXX
        if isinstance(oot, ootype.Record):
            return XXX
        if isinstance(oot, ootype.StaticMethod):
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

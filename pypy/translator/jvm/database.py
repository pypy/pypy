"""
The database tracks which graphs have already been generated, and maintains
a worklist.  It also contains a pointer to the type system.  It is passed
into every node for generation along with the generator.
"""
from cStringIO import StringIO
from pypy.rpython.ootypesystem import ootype
from pypy.translator.jvm.typesystem import jvm_method_desc
from pypy.translator.jvm import node
import pypy.translator.jvm.generator as jvmgen
import pypy.translator.jvm.typesystem as jvmtypes

class Database:
    def __init__(self, ts):
        # Public attributes:
        self.type_system = ts

        # Private attributes:
        self._classes = {} # Maps ootype class objects to node.Class objects
        self._counter = 0  # Used to create unique names
        self._pending = [] # Worklist

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
            fieldty = self.type_system.ootype_to_jvm(ftype)
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
                mobj = _method_for_graph(clobj, False, mimpl.graph)
                clobj.add_method(mobj)

        return clobj
    
    def _method_for_graph(self, classobj, is_static, graph):
        
        """
        Creates a node.Function object for a particular graph.  Adds the
        method to 'classobj', which should be a node.Class object.
        """

        # Build up a func object 
        func_name = self._make_unique_name(graph.name)
        argtypes = [arg.concretetype for arg in graph.getargs()
                    if arg.concretetype is not ootype.Void]
        jargtypes = [self.type_system.ootype_to_jvm(argty)
                     for argty in argtypes]
        rettype = graph.getreturnvar().concretetype
        jrettype = self.type_system.ootype_to_jvm(rettype)
        funcobj = self._translated[cachekey] = node.Function(
            classobj, func_name, jargtypes, jrettype, graph, is_static)
        return funcobj

    def pending_node(self, node):
        self._pending.append(node)

    def len_pending(self):
        return len(self._pending)

    def pop(self):
        return self._pending.pop()

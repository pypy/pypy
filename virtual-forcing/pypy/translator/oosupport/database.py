from pypy.translator.oosupport.constant import is_primitive
from pypy.rpython.ootypesystem import ootype

class Database(object):

    def __init__(self, genoo):
        self.genoo = genoo
        self.cts = genoo.TypeSystem(self)
        self._pending_nodes = set()
        self._rendered_nodes = set()
        self._unique_counter = 0
        self.constant_generator = genoo.ConstantGenerator(self)
        self.locked = False # new pending nodes are not allowed here

    # ____________________________________________________________
    # Miscellaneous

    def unique(self):
        """ Every time it is called, returns a unique integer.  Used in 
        various places. """
        self._unique_counter+=1
        return self._unique_counter-1

    def class_name(self, OOINSTANCE):
        """ Returns the backend class name of the type corresponding
        to OOINSTANCE"""
        raise NotImplementedError

    # ____________________________________________________________
    # Generation phases

    def gen_constants(self, ilasm):
        """ Renders the constants uncovered during the graph walk"""
        self.locked = True # new pending nodes are not allowed here
        self.constant_generator.gen_constants(ilasm)
        self.locked = False

    # ____________________________________________________________
    # Generation phases

    def record_delegate(self, OOTYPE):
        """ Returns a backend-specific type for a delegate class...
        details currently undefined. """
        raise NotImplementedError

    # ____________________________________________________________
    # Node creation
    #
    # Creates nodes for various kinds of things.
    
    def pending_class(self, INSTANCE):
        """ Returns a Node representing the ootype.Instance provided """
        raise NotImplementedError
    
    def pending_function(self, graph):
        """ Returns a Node representing the graph, which is being used as
        a static function """
        raise NotImplementedError

    # ____________________________________________________________
    # Basic Worklist Manipulation

    def pending_node(self, node):
        """ Adds a node to the worklist, so long as it is not already there
        and has not already been rendered. """
        assert not self.locked # sanity check
        if node in self._pending_nodes or node in self._rendered_nodes:
            return
        self._pending_nodes.add(node)
        node.dependencies()
            
    def len_pending(self):
        return len(self._pending_nodes)

    def pop(self):
        return self._pending_nodes.pop()


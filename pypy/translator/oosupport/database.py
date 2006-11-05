from pypy.translator.oosupport.constant import is_primitive
from pypy.rpython.ootypesystem import ootype

class Database(object):

    def __init__(self, genoo):
        self.genoo = genoo
        self.cts = genoo.TypeSystem(self)
        self._pending_nodes = set()
        self._rendered_nodes = set()
        self._const_cache = {}
        self._unique_counter = 0

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

        # Now, emit the initialization code:
        all_constants = self._const_cache.values()
        gen = self._begin_gen_constants(ilasm, all_constants)
        gen.add_section("Create Pointer Phase")
        ctr = 0
        for const in all_constants:
            gen.add_comment("Constant: %s" % const.name)
            const.create_pointer(gen)
            ctr = self._consider_interrupt(gen, ctr)
        gen.add_section("Initialize Opaque Phase")
        for const in all_constants:
            gen.add_comment("Constant: %s" % const.name)
            const.initialize_opaque(gen)
            ctr = self._consider_interrupt(gen, ctr)
        gen.add_section("Initialize Full Phase")
        for const in all_constants:
            gen.add_comment("Constant: %s" % const.name)
            const.initialize_full(gen)
            ctr = self._consider_interrupt(gen, ctr)
        self._end_gen_constants(gen)

    def _consider_interrupt(self, gen, ctr):
        ctr += 1
        if (ctr % 100) == 0: self._interrupt_gen_constants(gen)
        return ctr

    def _begin_gen_constants(self):
        # returns a generator
        raise NotImplementedError

    def _interrupt_gen_constants(self):
        # invoked every so often so as to break up the generated
        # code and not create one massive function
        pass
    
    def _end_gen_constants(self, gen):
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
        if node not in self._rendered_nodes:
            self._pending_nodes.add(node)
            
    def len_pending(self):
        return len(self._pending_nodes)

    def pop(self):
        return self._pending_nodes.pop()

    # ____________________________________________________________
    # Constants

    # Defines the subclasses used to represent complex constants by
    # _create_complex_const:
    
    InstanceConst = None
    RecordConst = None
    ClassConst = None

    def record_const(self, value):
        """ Returns an object representing the constant, remembering also
        any details needed to initialize the constant.  value should be an
        ootype constant value """
        assert not is_primitive(value)
        if value in self._const_cache:
            return self._const_cache[value]
        const = self._create_complex_const(value)
        self._const_cache[value] = const
        const.record_dependencies()
        return const

    def push_primitive_const(self, gen, value):
        """ Helper which pushes a primitive constant onto the stack """ 
        raise NotImplementedException

    def _create_complex_const(self, value):

        """ A helper method which creates a Constant wrapper object for
        the given value.  Uses the types defined in the sub-class. """
        
        # Determine if the static type differs from the dynamic type.
        if isinstance(value, ootype._view):
            static_type = value._TYPE
            value = value._inst
        else:
            static_type = None

        # Find the appropriate kind of Const object.
        if isinstance(value, ootype._instance):
            return self.InstanceConst(self, value, static_type, self.unique())
        elif isinstance(value, ootype._record):
            return self.RecordConst(self, value, self.unique())
        elif isinstance(value, ootype._class):
            return self.ClassConst(self, value, self.unique())
        #elif isinstance(value, ootype._list):
        #    return ListConst(db, value, count)
        #elif isinstance(value, ootype._static_meth):
        #    return StaticMethodConst(db, value, count)
        #elif isinstance(value, ootype._custom_dict):
        #    return CustomDictConst(db, value, count)
        #elif isinstance(value, ootype._dict):
        #    return DictConst(db, value, count)
        #elif isinstance(value, llmemory.fakeweakaddress):
        #    return WeakRefConst(db, value, count)
        else:
            assert False, 'Unknown constant: %s' % value


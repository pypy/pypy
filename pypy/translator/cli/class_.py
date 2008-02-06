from pypy.rpython.ootypesystem import ootype
from pypy.translator.cli.node import Node
from pypy.translator.cli.cts import CTS
from pypy.translator.oosupport.constant import push_constant
from pypy.translator.cli.ilgenerator import CLIBaseGenerator

try:
    set
except NameError:
    from sets import Set as set

class Class(Node):
    def __init__(self, db, INSTANCE, namespace, name):
        self.db = db
        self.cts = db.genoo.TypeSystem(db)
        self.INSTANCE = INSTANCE
        self.namespace = namespace
        self.name = name

    def dependencies(self):
        if not self.is_root(self.INSTANCE):
            self.db.pending_class(self.INSTANCE._superclass)

    def __hash__(self):
        return hash(self.INSTANCE)

    def __eq__(self, other):
        return self.INSTANCE == other.INSTANCE

    def __ne__(self, other):
        return not self == other

    def is_root(INSTANCE):
        return INSTANCE._superclass is None
    is_root = staticmethod(is_root)

    def get_name(self):
        return self.name

    def __repr__(self):
        return '<Class %s>' % self.name

    def get_base_class(self):
        base_class = self.INSTANCE._superclass
        if self.is_root(base_class):
            return '[mscorlib]System.Object'
        else:
            return self.db.class_name(base_class)

    def is_abstract(self):
        return False # XXX
        
        # if INSTANCE has an abstract method, the class is abstract
        method_names = set()
        for m_name, m_meth in self.INSTANCE._methods.iteritems():
            if not hasattr(m_meth, 'graph'):
                return True
            method_names.add(m_name)

        # if superclasses have abstract methods not overriden by
        # INSTANCE, the class is abstract
        abstract_method_names = set()
        cls = self.INSTANCE._superclass
        while cls is not None:
            abstract_method_names.update(cls._methods.keys())
            cls = cls._superclass
        not_overriden = abstract_method_names.difference(method_names)
        if not_overriden:
            return True
        
        return False

    def render(self, ilasm):        
        if self.is_root(self.INSTANCE):
            return

        self.ilasm = ilasm
        self.gen = CLIBaseGenerator(self.db, ilasm)

        if self.namespace:
            ilasm.begin_namespace(self.namespace)

        ilasm.begin_class(self.name, self.get_base_class(), abstract=self.is_abstract())
        for f_name, (f_type, f_default) in self.INSTANCE._fields.iteritems():
            cts_type = self.cts.lltype_to_cts(f_type)
            f_name = self.cts.escape_name(f_name)
            if cts_type != CTS.types.void:
                ilasm.field(f_name, cts_type)

        self._ctor()
        self._toString()

        for m_name, m_meth in self.INSTANCE._methods.iteritems():
            if hasattr(m_meth, 'graph'):
                # if the first argument's type is not a supertype of
                # this class it means that this method this method is
                # not really used by the class: don't render it, else
                # there would be a type mismatch.
                args =  m_meth.graph.getargs()
                SELF = args[0].concretetype
                if not ootype.isSubclass(self.INSTANCE, SELF):
                    continue
                f = self.db.genoo.Function(self.db, m_meth.graph, m_name, is_method = True)
                f.render(ilasm)
            else:
                # abstract method
                METH = m_meth._TYPE
                arglist = [(self.cts.lltype_to_cts(ARG), 'v%d' % i)
                           for i, ARG in enumerate(METH.ARGS)
                           if ARG is not ootype.Void]
                returntype = self.cts.lltype_to_cts(METH.RESULT)
                ilasm.begin_function(m_name, arglist, returntype, False, 'virtual') #, 'abstract')
                ilasm.add_comment('abstract method')
                if isinstance(METH.RESULT, ootype.OOType):
                    ilasm.opcode('ldnull')
                else:
                    push_constant(self.db, METH.RESULT, 0, self.gen)
                ilasm.opcode('ret')
                ilasm.end_function()

        ilasm.end_class()

        if self.namespace:
            ilasm.end_namespace()

    def _ctor(self):
        self.ilasm.begin_function('.ctor', [], 'void', False, 'specialname', 'rtspecialname', 'instance')
        self.ilasm.opcode('ldarg.0')
        self.ilasm.call('instance void %s::.ctor()' % self.get_base_class())
        # set default values for fields
        default_values = self.INSTANCE._fields.copy()
        default_values.update(self.INSTANCE._overridden_defaults)
        for f_name, (F_TYPE, f_default) in default_values.iteritems():
            if getattr(F_TYPE, '_is_value_type', False):
                continue # we can't set it to null
            INSTANCE_DEF, _ = self.INSTANCE._lookup_field(f_name)
            cts_type = self.cts.lltype_to_cts(F_TYPE)
            f_name = self.cts.escape_name(f_name)
            if cts_type != CTS.types.void:
                self.ilasm.opcode('ldarg.0')
                push_constant(self.db, F_TYPE, f_default, self.gen)
                class_name = self.db.class_name(INSTANCE_DEF)
                self.ilasm.set_field((cts_type, class_name, f_name))

        self.ilasm.opcode('ret')
        self.ilasm.end_function()

    def _toString(self):
        self.ilasm.begin_function('ToString', [], 'string', False, 'virtual', 'instance', 'default')
        self.ilasm.opcode('ldarg.0')
        self.ilasm.call('string class [pypylib]pypy.test.Result::InstanceToPython(object)')
        self.ilasm.ret()
        self.ilasm.end_function()


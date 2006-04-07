from pypy.translator.cli.node import Node
from pypy.translator.cli.function import Function
from pypy.translator.cli import cts

class Class(Node):
    def __init__(self, db, classdef):
        self.db = db
        self.classdef = classdef
        self.namespace, self.name = cts.split_class_name(classdef._name)
        #0/0

    def get_name(self):
        return self.name

    def get_base_class(self):
        base_class = self.classdef._superclass
        if base_class is None:
            return '[mscorlib]System.Object'
        else:
            return base_class._name

    def render(self, ilasm):
        self.ilasm = ilasm
        if self.namespace:
            ilasm.begin_namespace(self.namespace)

        ilasm.begin_class(self.name, self.get_base_class())
        for f_name, (f_type, f_default) in self.classdef._fields.iteritems():
            ilasm.field(f_name, cts.lltype_to_cts(f_type))

        # TODO: should the .ctor set the default values?
        self._ctor()

        for m_name, m_meth in self.classdef._methods.iteritems():
            # TODO: handle class methods and attributes
            f = Function(self.db, m_meth.graph, m_name, is_method = True)
            f.render(ilasm)

        ilasm.end_class()

        if self.namespace:
            ilasm.end_namespace()

    def _ctor(self):
        self.ilasm.begin_function('.ctor', [], 'void', False, 'specialname', 'rtspecialname', 'instance')
        self.ilasm.opcode('ldarg.0')
        self.ilasm.call('instance void %s::.ctor()' % self.get_base_class())
        self.ilasm.opcode('ret')
        self.ilasm.end_function()


from pypy.translator.cli.node import Node
from pypy.translator.cli.function import Function
from pypy.translator.cli import cts

class Class(Node):
    def __init__(self, classdef):
        self.classdef = classdef

    def get_name(self):
        return self.classdef._name

    def render(self, ilasm):
        self.ilasm = ilasm
        name = self.get_name().replace('__main__.', '') # TODO: handle modules
        ilasm.begin_class(name) # TODO: handle base class
        for f_name, (f_type, f_default) in self.classdef._fields.iteritems():
            # TODO: handle default values
            ilasm.field(f_name, cts.lltype_to_cts(f_type))

        self._ctor()

        for m_name, m_meth in self.classdef._methods.iteritems():
            # TODO: handle static methods
            # TODO: should __init__ be rendered as a constructor?
            f = Function(m_meth.graph, m_name, is_method = True)
            f.render(ilasm)

        ilasm.end_class()

    def _ctor(self):
        self.ilasm.begin_function('.ctor', [], 'void', False, 'specialname', 'rtspecialname', 'instance')
        self.ilasm.opcode('ldarg.0')
        self.ilasm.call('instance void object::.ctor()') # TODO: base class
        self.ilasm.opcode('ret')
        self.ilasm.end_function()


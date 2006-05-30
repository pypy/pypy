
""" genjs class definition
"""

from pypy.translator.cli.node import Node
from pypy.translator.cli.cts import CTS

class Class(Node):
    def __init__(self, db, classdef):
        self.db = db
        self.cts = db.type_system_class(db)
        self.classdef = classdef
        self.name = classdef._name.split('.')[-1]

        if not self.is_root(classdef):
            self.parent = self.db.pending_class(classdef._superclass)
            self.order = self.parent.order + 1
        else:
            self.order = 0

    def __hash__(self):
        return hash(self.classdef)

    def __eq__(self, other):
        return self.classdef == other.classdef
    
    def __cmp__(self, other):
        return cmp(self.order, other.order)

    def is_root(classdef):
        return classdef._superclass is None
    is_root = staticmethod(is_root)

    def get_name(self):
        return self.name

    def render(self, ilasm):
        if self.is_root(self.classdef):
            return

        if self.db.class_name(self.classdef) is not None:
            return # already rendered

        self.ilasm = ilasm
        
        ilasm.begin_function(self.name, [])
        ilasm.end_function()

        #for f_name, (f_type, f_default) in self.classdef._fields.iteritems():
        #    cts_type = self.cts.lltype_to_cts(f_type)
            #if cts_type != 'void':
        #    ilasm.field(f_name, cts_type)

        if not self.is_root(self.classdef):
            basename = self.basename(self.classdef._superclass._name)
            if basename != 'Root':
                ilasm.inherits(self.name, basename)
        
        for m_name, m_meth in self.classdef._methods.iteritems():
            f = self.db.function_class(self.db, m_meth.graph, m_name, is_method = True, _class = self.name)
            f.render(ilasm)
        
        
        self.db.record_class(self.classdef, self.name)
    
    def basename(self, name):
        return name.split('.')[-1]

    #def _ctor(self):
    #    self.ilasm.begin_function('.ctor', [], 'void', False, 'specialname', 'rtspecialname', 'instance')
    #    self.ilasm.opcode('ldarg.0')
    #    self.ilasm.call('instance void %s::.ctor()' % self.get_base_class())
    #    self.ilasm.opcode('ret')
    #    self.ilasm.end_function()

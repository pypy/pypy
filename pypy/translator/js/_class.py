
""" genjs class definition
"""

from pypy.translator.cli.node import Node
from pypy.translator.cli.cts import CTS

class Class(Node):
    def __init__(self, db, classdef):
        self.db = db
        self.cts = db.genoo.TypeSystem(db)
        self.classdef = classdef
        self.name = classdef._name.replace('.', '_')#[-1]
        self.real_name = classdef._name

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
        if self.is_root(self.classdef) or self.name == 'Object':
            return

        if self.db.class_name(self.classdef) is not None:
            return # already rendered

        self.ilasm = ilasm
        
        ilasm.begin_function(self.name, [])
        # we need to copy here all the arguments
        self.copy_class_attributes(ilasm)
        ilasm.end_function()
        
        # begin to_String method
        ilasm.begin_method("toString", self.name, [])
        ilasm.load_str("'<%s object>'" % self.real_name)
        ilasm.ret()
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
            graph = getattr(m_meth, 'graph', None)
            if graph:
                f = self.db.genoo.Function(self.db, graph, m_name, is_method = True, _class = self.name)
                f.render(ilasm)
            else:
                pass
                # XXX: We want to implement an abstract method here
                self.db.pending_abstract_function(m_name)
        
        self.db.record_class(self.classdef, self.name)
    
    def copy_class_attributes(self, ilasm):
        default_values = self.classdef._fields.copy()
        default_values.update(self.classdef._overridden_defaults)
        for field_name, (field_type, field_value) in default_values.iteritems():
            ilasm.load_str("this")
            self.db.load_const(field_type, field_value, ilasm)
            ilasm.set_field(None, field_name)
    
    def basename(self, name):
        return name.replace('.', '_')#[-1]

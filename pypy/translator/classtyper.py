"""
Extension to typer.py to preprocess class definitions and usage into
lower-level field and function definitions.
"""
from __future__ import generators
import re
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.objspace.flow.model import FunctionGraph, Block, Link
from pypy.annotation import model as annmodel
from pypy.translator.typer import LLTyper, LLFunction

r_ends_in_underscore_digit = re.compile(r'_\d+$')

# ____________________________________________________________

class ClassField:
    "An attribute of a class, mapped to some field(s) of a low-level struct."
    
    def __init__(self, hltype, name, llclass):
        self.hltype  = hltype
        self.name    = name
        self.llclass = llclass
        varname = '%s_%s' % (llclass.field_prefix, name)
        # to avoid name collisions between the 2nd lltype of a field called xyz
        # and another field whose name is exactly xyz_1, forbid field names
        # ending in '_\d+'
        if r_ends_in_underscore_digit.search(name):
            varname += '_'
        # self.var is a Variable that can stand for this field
        self.var = Variable(varname)
        llclass.makevar(self.var, hltype=hltype)
        # this (high-level) field is implemented as a list of LLVars
        # that are real fields for the C struct
        self.llvars = llclass.llreprs[self.var]

# ____________________________________________________________

class LLClass(LLTyper):
    """Low-level representation of a class as a structure and
    global functions that operate on it."""
    
    def __init__(self, typeset, name, cdef):
        LLTyper.__init__(self, typeset)
        self.typeset = typeset
        self.name = name
        self.cdef = cdef    # instance of pypy.annotator.factory.ClassDef
        self.bindings = typeset.bindings

        # collect the fields that the annotator deduced for this class
        cls = cdef.cls
        mainletters = [c.lower() for c in cls.__name__ if 'A' <= c <= 'Z']
        self.field_prefix = ''.join(mainletters[:3] or ['f'])
        self.fields = [ClassField(typeset.gethltype(s_value), attr, self)
                       for attr, s_value in cdef.attrs.items()]

        self.pyobj_fields = [  # XXX this should not be necessary
            fld.name for fld in self.fields if fld.hltype is typeset.R_OBJECT]
        self.s_instance = annmodel.SomeInstance(self.cdef)

    def get_management_functions(self):
        "Generate LLFunctions that operate on this class' structure."
        yield self.make_fn_new()

    def build_llfunc(self, graph):
        return LLFunction(self.typeset, graph.name, graph)

    def put_op(self, b):
        def op(opname, *args, **kw):
            assert kw.keys() == ['s_result']
            result = Variable()
            self.bindings[result] = kw['s_result']
            b.operations.append(SpaceOperation(opname, args, result))
            return result
        return op

    def make_fn_new(self):
        # generate the flow graph of the xxx_new() function
        b = Block([])
        op = self.put_op(b)
        cls = self.cdef.cls
        v1 = op('alloc_instance', Constant(cls),
                s_result = self.s_instance)
        # class attributes are used as defaults to initialize fields
        for fld in self.fields:
            if hasattr(cls, fld.name):
                value = getattr(cls, fld.name)
                op('setattr', v1, Constant(fld.name), Constant(value),
                   s_result = annmodel.SomeImpossibleValue())
        # finally, return v1
        graph = FunctionGraph('%s_new' % self.name, b)
        self.bindings[graph.getreturnvar()] = self.bindings[v1]
        b.closeblock(Link([v1], graph.returnblock))
        return self.build_llfunc(graph)

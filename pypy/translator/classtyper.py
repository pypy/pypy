"""
Extension to typer.py to preprocess class definitions and usage into
lower-level field and function definitions.
"""
from __future__ import generators
import re
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.objspace.flow.model import FunctionGraph, Block, Link
from pypy.annotation import model as annmodel
from pypy.translator.typer import LLTyper, LLFunction, LLVar
from pypy.translator.genc_repr import R_OBJECT

r_ends_in_underscore_digit = re.compile(r'_\d+$')

# ____________________________________________________________

class ClassField:
    "An attribute of a class, mapped to some field(s) of a low-level struct."
    
    def __init__(self, hltype, name, llclass, is_class_attr):
        self.hltype  = hltype
        self.name    = name
        self.llclass = llclass
        self.is_class_attr = is_class_attr
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

    def getllvars(self, pattern='%s'):
        """Return a list of fresh LLVars that implement the fields in this
        C struct.  The name of the variables are %'ed with 'pattern',
        which can be a C expression template to generate expressions to
        access this field.
        """
        return [LLVar(x.type, pattern % x.name) for x in self.llvars]

# ____________________________________________________________

class LLClass(LLTyper):
    """Low-level representation of a class as a structure and
    global functions that operate on it."""
    
    def __init__(self, typeset, name, cdef, llparent):
        LLTyper.__init__(self, typeset)
        self.typeset = typeset
        self.name = name
        self.cdef = cdef    # instance of pypy.annotator.factory.ClassDef
        self.llparent = llparent
        self.bindings = typeset.bindings
        self.s_instance = annmodel.SomeInstance(self.cdef)

    def setup(self):
        # two-phase initialization.  The code below might require other
        # classes to be already present in GenC.llclasses.

        # collect the fields that the annotator deduced for this class
        typeset = self.typeset
        cdef = self.cdef
        cls = cdef.cls
        mainletters = [c.lower() for c in cls.__name__ if 'A' <= c <= 'Z']
        self.field_prefix = ''.join(mainletters[:3] or ['f'])
        self.fields_here = []
        for attr, s_value in cdef.attrs.items():
            is_class_attr = cdef.readonly[attr]
            hltype = typeset.gethltype(s_value, unbound=is_class_attr)
            fld = ClassField(hltype, attr, self, is_class_attr)
            self.fields_here.append(fld)
        # fields are divided in instance attributes and class attributes
        # according to whether they are ever accessed with SET_ATTR or not
        if self.llparent:
            self.instance_fields = list(self.llparent.instance_fields)
            self.class_fields    = list(self.llparent.class_fields)
        else:
            self.instance_fields = []
            self.class_fields    = []
        self.instance_fields += [fld for fld in self.fields_here
                                 if not fld.is_class_attr]
        self.class_fields    += [fld for fld in self.fields_here
                                 if fld.is_class_attr]

    def get_instance_field(self, name):
        """Returns the ClassField corresponding to this attribute name.
        Keep in mind that it might be from some parent LLClass."""
        for fld in self.instance_fields:
            if fld.name == name:
                return fld
        return None

    def get_class_field(self, name):
        """Returns the ClassField corresponding to this class attribute name.
        Keep in mind that it might be from some parent LLClass."""
        for fld in self.class_fields:
            if fld.name == name:
                return fld
        return None

    def get_management_functions(self):
        "Generate LLFunctions that operate on this class' structure."
        yield self.make_fn_new()
        yield self.make_fn_typenew()

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
        # generate the flow graph of the new_xxx() function
        b = Block([])
        op = self.put_op(b)
        cls = self.cdef.cls
        v1 = op('alloc_instance', Constant(cls),
                s_result = self.s_instance)
        # class attributes are used as defaults to initialize instance fields
        for fld in self.instance_fields:
            if hasattr(cls, fld.name):
                value = getattr(cls, fld.name)
                op('setattr', v1, Constant(fld.name), Constant(value),
                   s_result = annmodel.SomeImpossibleValue())
        # finally, return v1
        graph = FunctionGraph('new_%s' % self.name, b)
        self.bindings[graph.getreturnvar()] = self.bindings[v1]
        b.closeblock(Link([v1], graph.returnblock))
        return self.build_llfunc(graph)

    def make_fn_typenew(self):
        # generate the flow graph of the typenew_xxx() function that
        # initializes the class attributes of the type object
        b = Block([])
        op = self.put_op(b)
        cls = self.cdef.cls
        v1 = Constant(cls)
        # initialize class attributes
        for fld in self.class_fields:
            # some attributes might be missing from 'cls' if it is an abstract
            # base class.  We left the field uninitialized in this case.
            if hasattr(cls, fld.name):
                value = getattr(cls, fld.name)
                op('initclassattr', v1, Constant(fld.name), Constant(value),
                   s_result = annmodel.SomeImpossibleValue())
        # finally, return None
        graph = FunctionGraph('typenew_%s' % self.name, b)
        self.bindings[graph.getreturnvar()] = annmodel.immutablevalue(None)
        b.closeblock(Link([Constant(None)], graph.returnblock))
        return self.build_llfunc(graph)

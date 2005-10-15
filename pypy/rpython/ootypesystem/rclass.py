from pypy.rpython.rmodel import inputconst
from pypy.rpython.rclass import AbstractClassRepr, AbstractInstanceRepr
from pypy.rpython.ootypesystem import ootype

CLASSTYPE = ootype.Class

class ClassRepr(AbstractClassRepr):
    def __init__(self, rtyper, classdef):
        AbstractClassRepr.__init__(self, rtyper, classdef)

        self.lowleveltype = ootype.Class

    def _setup_repr(self):
        # FIXME to be completed
        pass

    def convert_const(self):
        # FIXME
        pass

class InstanceRepr(AbstractInstanceRepr):
    def __init__(self, rtyper, classdef, does_need_gc=True):
        AbstractInstanceRepr.__init__(self, rtyper, classdef)

        self.lowleveltype = ootype.Instance(classdef.cls.__name__, None, {}, {})
        self.prebuiltinstances = {}   # { id(x): (x, _ptr) }

    def _setup_repr(self):
        # FIXME fields, methods
        pass

    def convert_const(self):
        # FIXME
        pass

    def new_instance(self, llops):
        """Build a new instance, without calling __init__."""

        return llops.genop("new",
            [inputconst(ootype.Void, self.lowleveltype)], self.lowleveltype)

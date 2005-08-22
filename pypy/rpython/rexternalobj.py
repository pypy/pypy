from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.rpython import lltype
from pypy.rpython.rmodel import Repr
from pypy.rpython.extfunctable import typetable
from pypy.rpython import rbuiltin
from pypy.tool import sourcetools


class __extend__(annmodel.SomeExternalObject):
    def rtyper_makerepr(self, rtyper):
        return ExternalObjRepr(self.knowntype)
    def rtyper_makekey(self):
        return self.__class__, self.knowntype


class ExternalObjRepr(Repr):

    def __init__(self, knowntype):
        self.exttypeinfo = typetable[knowntype]
        TYPE = self.exttypeinfo.get_lltype()
        self.lowleveltype = lltype.Ptr(TYPE)
        # The set of methods supported depends on 'knowntype', so we
        # cannot have rtype_method_xxx() methods directly on the
        # ExternalObjRepr class.  But we can store them in 'self' now.
        for name, extfuncinfo in self.exttypeinfo.methods.items():
            methodname = 'rtype_method_' + name
            bltintyper = rbuiltin.make_rtype_extfunc(extfuncinfo)
            setattr(self, methodname, bltintyper)

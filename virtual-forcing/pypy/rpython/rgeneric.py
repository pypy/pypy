from pypy.annotation import model as annmodel
from pypy.rpython.rmodel import Repr
from pypy.rpython.rpbc import AbstractFunctionsPBCRepr,\
     AbstractMethodsPBCRepr
from pypy.tool.pairtype import pairtype
from pypy.rpython.lltypesystem import lltype

class AbstractGenericCallableRepr(Repr):
    def __init__(self, rtyper, s_generic):
        self.rtyper = rtyper
        self.s_generic = s_generic
        self.args_r = [self.rtyper.getrepr(arg) for arg in s_generic.args_s]
        self.r_result = self.rtyper.getrepr(s_generic.s_result)
        self.lowleveltype = self.create_low_leveltype()

    def rtype_simple_call(self, hop):
        return self.call('simple_call', hop)

    def rtype_call_args(self, hop):
        return self.call('call_args', hop)

    def call(self, opname, hop):
        bk = self.rtyper.annotator.bookkeeper
        vlist = hop.inputargs(self, *self.args_r) + [hop.inputconst(lltype.Void, None)]
        hop.exception_is_here()
        v_result = hop.genop('indirect_call', vlist, resulttype=self.r_result)
        return v_result

    def convert_const(self, value):
        bookkeeper = self.rtyper.annotator.bookkeeper
        if value is None:
            return self.rtyper.type_system.null_callable(self.lowleveltype)
        r_func = self.rtyper.getrepr(bookkeeper.immutablevalue(value))
        return r_func.get_unique_llfn().value

    def _setup_repr(self):
        for r in self.args_r:
            r.setup()
        self.r_result.setup()

class __extend__(annmodel.SomeGenericCallable):
    def rtyper_makerepr(self, rtyper):
        return rtyper.type_system.rgeneric.GenericCallableRepr(rtyper, self)

    def rtyper_makekey(self):
        return self.__class__, tuple([i.rtyper_makekey() for i in self.args_s]),\
              self.s_result.rtyper_makekey()

class __extend__(pairtype(AbstractFunctionsPBCRepr, AbstractGenericCallableRepr)):
    def convert_from_to((pbcrepr, gencallrepr), v, llops):
        if pbcrepr.lowleveltype is lltype.Void:
            r = gencallrepr.convert_const(pbcrepr.s_pbc.const)
            r.setup()
            return r
        if pbcrepr.lowleveltype == gencallrepr.lowleveltype:
            return v
        return NotImplemented

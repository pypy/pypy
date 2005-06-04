import types
from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.rpython.lltype import typeOf, Void
from pypy.rpython.rmodel import Repr, TyperError
from pypy.rpython import rclass


class __extend__(annmodel.SomePBC):
    def rtyper_makerepr(self, rtyper):
        return PBCRepr(self.prebuiltinstances)


class PBCRepr(Repr):

    def __init__(self, prebuiltinstances):
        self.prebuiltinstances = prebuiltinstances
        assert len(prebuiltinstances) == 1, "Not Implemented: multiPBCs"
        self.lowleveltype = Void

    def rtype_getattr(_, hop):
        if hop.s_result.is_constant():
            return hop.inputconst(hop.r_result, hop.s_result.const)
        else:
            NotImplementedYet

    def rtype_simple_call(_, hop):
        r_func, s_func = hop.r_s_popfirstarg()
        if not s_func.is_constant():
            NotImplementedYet
        func = s_func.const
        if isinstance(func, types.FunctionType):
            # XXX hackish
            f = hop.rtyper.getfunctionptr(func)
            graph = f._obj.graph
            FUNCPTR = typeOf(f)
            rinputs = [hop.rtyper.bindingrepr(v) for v in graph.getargs()]
            if FUNCPTR.TO.RESULT == Void:
                rresult = Void
            else:
                rresult = hop.rtyper.bindingrepr(graph.getreturnvar())
            args_v = hop.inputargs(*rinputs)
            c = hop.inputconst(FUNCPTR, f)
            return hop.genop('direct_call', [c] + args_v,
                             resulttype = rresult)
        elif isinstance(func, (types.ClassType, type)):
            return rclass.rtype_new_instance(s_func.const, hop)
            # XXX call __init__ somewhere

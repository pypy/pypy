from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.rpython.lltype import Ptr, _ptr
from pypy.rpython.lltype import ContainerType, Void, Signed, Bool
from pypy.rpython.rmodel import Repr, TyperError, IntegerRepr, inputconst


class __extend__(annmodel.SomePtr):
    def rtyper_makerepr(self, rtyper):
        if self.is_constant():   # constant NULL
            return nullptr_repr
        else:
            return PtrRepr(self.ll_ptrtype)
    def rtyper_makekey(self):
        if self.is_constant():
            return None
        else:
            return self.ll_ptrtype


class PtrRepr(Repr):

    def __init__(self, ptrtype):
        assert isinstance(ptrtype, Ptr)
        self.lowleveltype = ptrtype

    def rtype_getattr(self, hop):
        attr = hop.args_s[1].const
        FIELD_TYPE = getattr(self.lowleveltype.TO, attr)
        if isinstance(FIELD_TYPE, ContainerType):
            newopname = 'getsubstruct'
        else:
            newopname = 'getfield'
        vlist = hop.inputargs(self, Void)
        return hop.genop(newopname, vlist,
                         resulttype = hop.r_result.lowleveltype)

    def rtype_setattr(self, hop):
        attr = hop.args_s[1].const
        FIELD_TYPE = getattr(self.lowleveltype.TO, attr)
        assert not isinstance(FIELD_TYPE, ContainerType)
        vlist = hop.inputargs(self, Void, hop.args_r[2])
        hop.genop('setfield', vlist)

    def rtype_len(self, hop):
        vlist = hop.inputargs(self)
        return hop.genop('getarraysize', vlist,
                         resulttype = hop.r_result.lowleveltype)

    def rtype_is_true(self, hop):
        vlist = hop.inputargs(self)
        return hop.genop('ptr_nonzero', vlist, resulttype=Bool)


class __extend__(pairtype(PtrRepr, IntegerRepr)):

    def rtype_getitem((r_ptr, r_int), hop):
        ARRAY = r_ptr.lowleveltype.TO
        ITEM_TYPE = ARRAY.OF
        if isinstance(ITEM_TYPE, ContainerType):
            newopname = 'getarraysubstruct'
        else:
            newopname = 'getarrayitem'
        vlist = hop.inputargs(r_ptr, Signed)
        return hop.genop(newopname, vlist,
                         resulttype = hop.r_result.lowleveltype)

    def rtype_setitem((r_ptr, r_int), hop):
        ARRAY = r_ptr.lowleveltype.TO
        ITEM_TYPE = ARRAY.OF
        assert not isinstance(ITEM_TYPE, ContainerType)
        vlist = hop.inputargs(r_ptr, Signed, hop.args_r[2])
        hop.genop('setarrayitem', vlist)

# ____________________________________________________________
#
#  Null Pointers

class NullPtrRepr(Repr):
    lowleveltype = Void

    def rtype_is_true(self, hop):
        return hop.inputconst(Bool, False)

nullptr_repr = NullPtrRepr()

class __extend__(pairtype(NullPtrRepr, PtrRepr)):
    def convert_from_to((r_null, r_ptr), v, llops):
        # nullptr to general pointer
        return inputconst(r_ptr, _ptr(r_ptr.lowleveltype, None))

# ____________________________________________________________
#
#  Comparisons

class __extend__(pairtype(PtrRepr, Repr)):

    def rtype_eq((r_ptr, r_any), hop):
        vlist = hop.inputargs(r_ptr, r_ptr)
        return hop.genop('ptr_eq', vlist, resulttype=Bool)

    def rtype_ne((r_ptr, r_any), hop):
        vlist = hop.inputargs(r_ptr, r_ptr)
        return hop.genop('ptr_ne', vlist, resulttype=Bool)


class __extend__(pairtype(Repr, PtrRepr)):

    def rtype_eq((r_any, r_ptr), hop):
        vlist = hop.inputargs(r_ptr, r_ptr)
        return hop.genop('ptr_eq', vlist, resulttype=Bool)

    def rtype_ne((r_any, r_ptr), hop):
        vlist = hop.inputargs(r_ptr, r_ptr)
        return hop.genop('ptr_ne', vlist, resulttype=Bool)

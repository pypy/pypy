from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomePtr, SomeInteger
from pypy.rpython.lltype import ContainerType, Void, Signed, Bool


class __extend__(SomePtr):

    def lowleveltype(s_ptr):
        if s_ptr.is_constant():   # constant NULL
            return Void
        else:
            return s_ptr.ll_ptrtype

    def rtype_getattr(s_ptr, hop):
        attr = hop.args_s[1].const
        FIELD_TYPE = getattr(s_ptr.ll_ptrtype.TO, attr)
        if isinstance(FIELD_TYPE, ContainerType):
            newopname = 'getsubstruct'
        else:
            newopname = 'getfield'
        vlist = hop.inputargs(s_ptr, Void)
        return hop.genop(newopname, vlist,
                         resulttype = hop.s_result.lowleveltype())

    def rtype_setattr(s_ptr, hop):
        attr = hop.args_s[1].const
        FIELD_TYPE = getattr(s_ptr.ll_ptrtype.TO, attr)
        assert not isinstance(FIELD_TYPE, ContainerType)
        vlist = hop.inputargs(s_ptr, Void, FIELD_TYPE)
        hop.genop('setfield', vlist)

    def rtype_len(s_ptr, hop):
        vlist = hop.inputargs(s_ptr)
        return hop.genop('getarraysize', vlist,
                         resulttype = hop.s_result.lowleveltype())

    def rtype_is_true(s_ptr, hop):
        vlist = hop.inputargs(s_ptr)
        return hop.genop('ptr_nonzero', vlist, resulttype=Bool)


class __extend__(pairtype(SomePtr, SomeInteger)):

    def rtype_getitem((s_ptr, s_int), hop):
        vlist = hop.inputargs(s_ptr, Signed)
        return hop.genop('getarrayitem', vlist,
                         resulttype = hop.s_result.lowleveltype())


class __extend__(pairtype(SomePtr, SomePtr)):

    def rtype_eq(_, hop):
        vlist = hop.inputargs(SomePtr(), SomePtr())
        return hop.genop('ptr_eq', vlist, resulttype=Bool)

    def rtype_ne(_, hop):
        vlist = hop.inputargs(SomePtr(), SomePtr())
        return hop.genop('ptr_ne', vlist, resulttype=Bool)

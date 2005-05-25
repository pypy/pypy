from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomePtr, SomeInteger
from pypy.rpython.lltype import ContainerType, Void, Signed
from pypy.rpython.rtyper import receive, receiveconst
from pypy.rpython.rtyper import peek_at_result_annotation, direct_op


class __extend__(SomePtr):

    def lowleveltype(s_ptr):
        return s_ptr.ll_ptrtype

    def rtype_getattr(s_ptr, s_attr):
        attr = s_attr.const
        FIELD_TYPE = getattr(s_ptr.ll_ptrtype.TO, attr)
        if isinstance(FIELD_TYPE, ContainerType):
            newopname = 'getsubstruct'
        else:
            newopname = 'getfield'
        v_ptr = receive(s_ptr, arg=0)
        v_attr = receiveconst(Void, attr)
        s_result = peek_at_result_annotation()
        return direct_op(newopname, [v_ptr, v_attr],
                         resulttype = s_result.lowleveltype())

    def rtype_setattr(s_ptr, s_attr, s_value):
        attr = s_attr.const
        FIELD_TYPE = getattr(s_ptr.ll_ptrtype.TO, attr)
        assert not isinstance(FIELD_TYPE, ContainerType)
        v_ptr = receive(s_ptr, arg=0)
        v_attr = receiveconst(Void, attr)
        v_value = receive(FIELD_TYPE, arg=2)
        direct_op('setfield', [v_ptr, v_attr, v_value])

    def rtype_len(s_ptr):
        v_ptr = receive(s_ptr, arg=0)
        s_result = peek_at_result_annotation()
        return direct_op('getarraysize', [v_ptr],
                         resulttype = s_result.lowleveltype())


class __extend__(pairtype(SomePtr, SomeInteger)):

    def rtype_getitem((s_ptr, s_int)):
        v_ptr = receive(s_ptr, arg=0)
        v_index = receive(Signed, arg=1)
        s_result = peek_at_result_annotation()
        return direct_op('getarrayitem', [v_ptr, v_index],
                         resulttype = s_result.lowleveltype())

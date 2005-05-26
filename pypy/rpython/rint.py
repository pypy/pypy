from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeInteger, SomeBool
from pypy.rpython.lltype import Signed, Unsigned, Bool
from pypy.rpython.rtyper import peek_at_result_annotation, receive, direct_op
from pypy.rpython.rtyper import TyperError


class __extend__(pairtype(SomeInteger, SomeInteger)):

    def rtype_convert_from_to((s_from, s_to), v):
        # assume that converting between signed and unsigned doesn't need
        # an operation for now
        return v

    def rtype_add((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = receive(Unsigned, arg=0)
            v_int2 = receive(Unsigned, arg=1)
            return direct_op('uint_add', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = receive(Signed, arg=0)
            v_int2 = receive(Signed, arg=1)
            return direct_op('int_add', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_add = rtype_add

    def rtype_sub((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = receive(Unsigned, arg=0)
            v_int2 = receive(Unsigned, arg=1)
            return direct_op('uint_sub', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = receive(Signed, arg=0)
            v_int2 = receive(Signed, arg=1)
            return direct_op('int_sub', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_sub = rtype_sub

    def rtype_lt((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            if not s_int1.nonneg or not s_int2.nonneg:
                raise TyperError("comparing a signed and an unsigned number")
            v_int1 = receive(Unsigned, arg=0)
            v_int2 = receive(Unsigned, arg=1)
            return direct_op('uint_lt', [v_int1, v_int2], resulttype=Bool)
        else:
            v_int1 = receive(Signed, arg=0)
            v_int2 = receive(Signed, arg=1)
            return direct_op('int_lt', [v_int1, v_int2], resulttype=Bool)


class __extend__(SomeInteger):

    def rtype_is_true(s_int):
        v_int = receive(Signed, arg=0)
        return direct_op('int_is_true', [v_int], resulttype=Bool)


class __extend__(SomeBool):

    def rtype_is_true(s_bool):
        v_bool = receive(Bool, arg=0)
        return v_bool

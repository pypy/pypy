from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeInteger
from pypy.rpython.lltype import Signed, Unsigned
from pypy.rpython.rtyper import peek_at_result_annotation, receive, direct_op


class __extend__(pairtype(SomeInteger, SomeInteger)):

    def rtype_add((s_int1, s_int2)):
        if peek_at_result_annotation().unsigned:
            v_int1 = receive(Unsigned, arg=0)
            v_int2 = receive(Unsigned, arg=1)
            return direct_op('uint_add', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = receive(Signed, arg=0)
            v_int2 = receive(Signed, arg=1)
            return direct_op('int_add', [v_int1, v_int2], resulttype=Signed)

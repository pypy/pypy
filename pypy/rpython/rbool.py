from pypy.annotation.pairtype import pairtype
from pypy.annotation.model import SomeFloat, SomeInteger, SomeBool, SomePBC
from pypy.rpython.lltype import Signed, Unsigned, Bool, Float
from pypy.rpython.rtyper import receive, direct_op
from pypy.rpython.rtyper import TyperError


debug = False

class __extend__(pairtype(SomeBool, SomeInteger)):

    def rtype_convert_from_to((s_from, s_to), v):
        if s_to.unsigned:
            if debug: print 'explicit cast_bool_to_uint'
            return direct_op('cast_bool_to_uint', [v], resulttype=Unsigned)
        else:
            if debug: print 'explicit cast_bool_to_int'
            return direct_op('cast_bool_to_int', [v], resulttype=Signed)


class __extend__(pairtype(SomeBool, SomeFloat)):

    def rtype_convert_from_to((s_from, s_to), v):
        if debug: print 'explicit cast_bool_to_float'
        return direct_op('cast_bool_to_float', [v], resulttype=Float)


class __extend__(SomeBool):

    def rtype_is_true(s_bool):
        v_bool = receive(Bool, 0)
        return v_bool

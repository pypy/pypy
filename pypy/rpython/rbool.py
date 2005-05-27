from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeBool, SomeFloat, SomeInteger
from pypy.rpython.lltype import Bool
from pypy.rpython.rtyper import receive


debug = True

class __extend__(pairtype(SomeBool, SomeInteger)):

    def rtype_convert_from_to((s_from, s_to), v):
        if debug: print 'XXX TODO cast SomeBool->SomeInteger'
        return v


class __extend__(pairtype(SomeBool, SomeFloat)):

    def rtype_convert_from_to((s_from, s_to), v):
        if debug: print 'XXX TODO cast SomeBool->SomeFloat'
        return v


class __extend__(SomeBool):

    def rtype_is_true(s_bool):
        v_bool = receive(Bool, arg=0)
        return v_bool

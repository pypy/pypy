from pypy.annotation.pairtype import pairtype
from pypy.annotation.model import SomeFloat, SomeInteger, SomeBool, SomePBC
from pypy.rpython.lltype import Signed, Unsigned, Bool, Float
from pypy.rpython.rtyper import TyperError


debug = False

class __extend__(pairtype(SomeBool, SomeInteger)):

    def rtype_convert_from_to((s_from, s_to), v, llops):
        if s_to.unsigned:
            if debug: print 'explicit cast_bool_to_uint'
            return llops.genop('cast_bool_to_uint', [v], resulttype=Unsigned)
        else:
            if debug: print 'explicit cast_bool_to_int'
            return llops.genop('cast_bool_to_int', [v], resulttype=Signed)


class __extend__(pairtype(SomeBool, SomeFloat)):

    def rtype_convert_from_to((s_from, s_to), v, llops):
        if debug: print 'explicit cast_bool_to_float'
        return llops.genop('cast_bool_to_float', [v], resulttype=Float)


class __extend__(SomeBool):

    def rtype_is_true(_, hop):
        vlist = hop.inputargs(Bool)
        return vlist[0]

    def rtype_int(_, hop):
        vlist = hop.inputargs(Signed)
        return vlist[0]

    def rtype_float(_, hop):
        vlist = hop.inputargs(Float)
        return vlist[0]

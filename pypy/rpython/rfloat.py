from pypy.annotation.pairtype import pairtype
from pypy.annotation.model import SomeFloat, SomeInteger, SomeBool, SomePBC
from pypy.rpython.lltype import Signed, Unsigned, Bool, Float
from pypy.rpython.rtyper import TyperError


debug = False

class __extend__(pairtype(SomeFloat, SomeFloat)):

    #Arithmetic

    def rtype_add(_, hop):
        return _rtype_template(hop, 'add')

    rtype_inplace_add = rtype_add

    def rtype_sub(_, hop):
        return _rtype_template(hop, 'sub')

    rtype_inplace_sub = rtype_sub

    def rtype_mul(_, hop):
        return _rtype_template(hop, 'mul')

    rtype_inplace_mul = rtype_mul

    def rtype_div(_, hop):
        return _rtype_template(hop, 'div')

    rtype_inplace_div = rtype_div

    def rtype_pow(_, hop):
        s_float3 = hop.args_s[2]
        if s_float3.is_constant() and s_float3.const is None:
            vlist = hop.inputargs(Float, Float, Void)[:2]
        else:
            vlist = hop.inputargs(Float, Float, Float)
        return hop.genop('float_pow', vlist, resulttype=Float)

    def rtype_inplace_pow(_, hop):
        return _rtype_template(hop, 'pow')

    #comparisons: eq is_ ne lt le gt ge

    def rtype_eq(_, hop):
        return _rtype_compare_template(hop, 'eq')

    rtype_is_ = rtype_eq

    def rtype_ne(_, hop):
        return _rtype_compare_template(hop, 'ne')

    def rtype_lt(_, hop):
        return _rtype_compare_template(hop, 'lt')

    def rtype_le(_, hop):
        return _rtype_compare_template(hop, 'le')

    def rtype_gt(_, hop):
        return _rtype_compare_template(hop, 'gt')

    def rtype_ge(_, hop):
        return _rtype_compare_template(hop, 'ge')


#Helpers SomeFloat,Somefloat

def _rtype_template(hop, func):
    vlist = hop.inputargs(Float, Float)
    return hop.genop('float_'+func, vlist, resulttype=Float)

def _rtype_compare_template(hop, func):
    vlist = hop.inputargs(Float, Float)
    return hop.genop('float_'+func, vlist, resulttype=Bool)


#

## XXX we have probably no implicit casts from float to integer
##class __extend__(pairtype(SomeFloat, SomeInteger)):

##    def rtype_convert_from_to((s_from, s_to), v):
##        if s_to.unsigned:
##            if debug: print 'explicit cast_float_to_uint'
##            return direct_op('cast_float_to_uint', [v], resulttype=Unsigned)
##        else:
##            if debug: print 'explicit cast_float_to_int'
##            return direct_op('cast_float_to_int', [v], resulttype=Signed)


#

class __extend__(pairtype(SomeInteger, SomeFloat)):

    def rtype_convert_from_to((s_from, s_to), v, llops):
        if s_from.unsigned:
            if debug: print 'explicit cast_uint_to_float'
            return llops.genop('cast_uint_to_float', [v], resulttype=Float)
        else:
            if debug: print 'explicit cast_int_to_float'
            return llops.genop('cast_int_to_float', [v], resulttype=Float)


#

## XXX we have probably no implicit casts from float to bool
##class __extend__(pairtype(SomeFloat, SomeBool)):

##    def rtype_convert_from_to((s_from, s_to), v):
##        if debug: print 'explicit cast_float_to_bool'
##        return direct_op('cast_float_to_bool', [v], resulttype=Bool)  #XXX or can 'float_is_true' be reused here? 


#

class __extend__(SomeFloat):

    def rtype_is_true(_, hop):
        vlist = hop.inputargs(Float)
        return hop.genop('float_is_true', vlist, resulttype=Bool)

    rtype_nonzero = rtype_is_true

    def rtype_neg(s_int):
        vlist = receive(Float)
        return hop.genop('float_neg', vlist, resulttype=Float)

    def rtype_pos(s_int):
        v_list = receive(Float)
        return vlist[0]

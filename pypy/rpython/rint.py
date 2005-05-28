from pypy.annotation.pairtype import pairtype
from pypy.annotation.model import SomeFloat, SomeInteger, SomeBool, SomePBC
from pypy.rpython.lltype import Signed, Unsigned, Bool, Float
from pypy.rpython.rtyper import TyperError


debug = False

class __extend__(pairtype(SomeInteger, SomeInteger)):

    def rtype_convert_from_to((s_from, s_to), v, llops):
        if s_from.unsigned != s_to.unsigned:
            if s_to.unsigned:
                if debug: print 'explicit cast_int_to_uint'
                return llops.genop('cast_int_to_uint', [v], resulttype=Unsigned)
            else:
                if debug: print 'explicit cast_uint_to_int'
                return llops.genop('cast_uint_to_int', [v], resulttype=Signed)
        return v

    #arithmetic

    def rtype_add(_, hop):
        return _rtype_template(hop, 'add')
    rtype_inplace_add = rtype_add

    def rtype_add_ovf(_, hop):
        return _rtype_template(hop, 'add_ovf')
    rtype_inplace_add_ovf = rtype_add_ovf

    def rtype_sub(_, hop):
        return _rtype_template(hop, 'sub')
    rtype_inplace_sub = rtype_sub

    def rtype_sub_ovf(_, hop):
        return _rtype_template(hop, 'sub_ovf')
    rtype_inplace_sub_ovf = rtype_sub_ovf

    def rtype_mul(_, hop):
        return _rtype_template(hop, 'mul')
    rtype_inplace_mul = rtype_mul

    def rtype_div(_, hop):
        return _rtype_template(hop, 'div')
    rtype_inplace_div = rtype_div

    def rtype_mod(_, hop):
        return _rtype_template(hop, 'mod')
    rtype_inplace_mod = rtype_mod

    def rtype_xor(_, hop):
        return _rtype_template(hop, 'xor')
    rtype_inplace_xor = rtype_xor

    def rtype_and_(_, hop):
        return _rtype_template(hop, 'and')
    rtype_inplace_and = rtype_and_

    def rtype_or_(_, hop):
        return _rtype_template(hop, 'or')
    rtype_inplace_or = rtype_or_

    def rtype_lshift(_, hop):
        return _rtype_template(hop, 'lshift')
    rtype_inplace_lshift = rtype_lshift

    def rtype_lshift_ovf(_, hop):
        return _rtype_template(hop, 'lshift_ovf')
    rtype_inplace_lshift_ovf = rtype_lshift_ovf

    def rtype_rshift(_, hop):
        return _rtype_template(hop, 'rshift')
    rtype_inplace_rshift = rtype_rshift

    def rtype_rshift_ovf(_, hop):
        return _rtype_template(hop, 'rshift_ovf')
    rtype_inplace_rshift_ovf = rtype_rshift_ovf

    def rtype_pow(_, hop):
        s_int3 = hop.args_s[2]
        if hop.s_result.unsigned:
            if s_int3.is_constant() and s_int3.const is None:
                vlist = hop.inputargs(Unsigned, Unsigned, Void)[:2]
            else:
                vlist = hop.inputargs(Unsigned, Unsigned, Unsigned)
            return hop.genop('uint_pow', vlist, resulttype=Unsigned)
        else:
            if s_int3.is_constant() and s_int3.const is None:
                vlist = hop.inputargs(Signed, Signed, Void)[:2]
            else:
                vlist = hop.inputargs(Signed, Signed, Signed)
            return hop.genop('int_pow', vlist, resulttype=Signed)

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

#Helper functions

def _rtype_template(hop, func):
    if hop.s_result.unsigned:
        vlist = hop.inputargs(Unsigned, Unsigned)
        return hop.genop('uint_'+func, vlist, resulttype=Unsigned)
    else:
        vlist = hop.inputargs(Signed, Signed)
        return hop.genop('int_'+func, vlist, resulttype=Signed)

#Helper functions for comparisons

def _rtype_compare_template(hop, func):
    s_int1, s_int2 = hop.args_s
    if s_int1.unsigned or s_int2.unsigned:
        if not s_int1.nonneg or not s_int2.nonneg:
            raise TyperError("comparing a signed and an unsigned number")
        vlist = hop.inputargs(Unsigned, Unsigned)
        return hop.genop('uint_'+func, vlist, resulttype=Bool)
    else:
        vlist = hop.inputargs(Signed, Signed)
        return hop.genop('int_'+func, vlist, resulttype=Bool)


#

class __extend__(SomeInteger):

    def rtype_is_true(s_int, hop):
        if s_int.unsigned:
            vlist = hop.inputargs(Unsigned)
            return hop.genop('uint_is_true', vlist, resulttype=Bool)
        else:
            vlist = hop.inputargs(Signed)
            return hop.genop('int_is_true', vlist, resulttype=Bool)

    rtype_nonzero = rtype_is_true

    #Unary arithmetic operations    
    
    def rtype_abs(_, hop):
        if hop.s_result.unsigned:
            vlist = hop.inputargs(Unsigned)
            return vlist[0]
        else:
            vlist = hop.inputargs(Signed)
            return hop.genop('int_abs', vlist, resulttype=Signed)

    def rtype_abs_ovf(_, hop):
        if hop.s_result.unsigned:
            vlist = hop.inputargs(Unsigned)
            return vlist[0]
        else:
            vlist = hop.inputargs(Signed)
            return hop.genop('int_abs_ovf', vlist, resulttype=Signed)

    def rtype_invert(_, hop):
        if hop.s_result.unsigned:
            vlist = hop.inputargs(Unsigned)
            return hop.genop('uint_invert', vlist, resulttype=Unsigned)
        else:
            vlist = hop.inputargs(Signed)
            return hop.genop('int_invert', vlist, resulttype=Signed)

    def rtype_neg(_, hop):
        if hop.s_result.unsigned:
            vlist = hop.inputargs(Unsigned)
            return hop.genop('uint_neg', vlist, resulttype=Unsigned)
        else:
            vlist = hop.inputargs(Signed)
            return hop.genop('int_neg', vlist, resulttype=Signed)

    def rtype_pos(_, hop):
        if s_int.unsigned:
            vlist = hop.inputargs(Unsigned)
        else:
            vlist = hop.inputargs(Signed)
        return vlist[0]

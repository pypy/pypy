from pypy.annotation.pairtype import pairtype
from pypy.annotation.model import SomeFloat, SomeInteger, SomeBool, SomePBC
from pypy.rpython.lltype import Signed, Unsigned, Bool, Float
from pypy.rpython.rtyper import receive, direct_op
from pypy.rpython.rtyper import TyperError


debug = False

class __extend__(pairtype(SomeInteger, SomeInteger)):

    def rtype_convert_from_to((s_from, s_to), v):
        if s_from.unsigned != s_to.unsigned:        #XXX Can _receive_may_cast(...) be used here?
            if s_to.unsigned:
                if debug: print 'explicit cast_int_to_uint'
                return direct_op('cast_int_to_uint', [v], resulttype=Unsigned)
            else:
                if debug: print 'explicit cast_uint_to_int'
                return direct_op('cast_uint_to_int', [v], resulttype=Signed)
        return v

    #arithmetic
    
    def rtype_add((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = _receive_may_cast(s_int1, Unsigned, 0)
            v_int2 = _receive_may_cast(s_int2, Unsigned, 1)
            return direct_op('uint_add', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = _receive_may_cast(s_int1, Signed, 0)
            v_int2 = _receive_may_cast(s_int2, Signed, 1)
            return direct_op('int_add', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_add = rtype_add

    def rtype_add_ovf((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = _receive_may_cast(s_int1, Unsigned, 0)
            v_int2 = _receive_may_cast(s_int2, Unsigned, 1)
            return direct_op('uint_add_ovf', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = _receive_may_cast(s_int1, Signed, 0)
            v_int2 = _receive_may_cast(s_int2, Signed, 1)
            return direct_op('int_add_ovf', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_add_ovf = rtype_add_ovf

    def rtype_sub((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = _receive_may_cast(s_int1, Unsigned, 0)
            v_int2 = _receive_may_cast(s_int2, Unsigned, 1)
            return direct_op('uint_sub', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = _receive_may_cast(s_int1, Signed, 0)
            v_int2 = _receive_may_cast(s_int2, Signed, 1)
            return direct_op('int_sub', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_sub = rtype_sub

    def rtype_sub_ovf((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = _receive_may_cast(s_int1, Unsigned, 0)
            v_int2 = _receive_may_cast(s_int2, Unsigned, 1)
            return direct_op('uint_sub_ovf', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = _receive_may_cast(s_int1, Signed, 0)
            v_int2 = _receive_may_cast(s_int2, Signed, 1)
            return direct_op('int_sub_ovf', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_sub_ovf = rtype_sub_ovf

    def rtype_mul((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = _receive_may_cast(s_int1, Unsigned, 0)
            v_int2 = _receive_may_cast(s_int2, Unsigned, 1)
            return direct_op('uint_mul', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = _receive_may_cast(s_int1, Signed, 0)
            v_int2 = _receive_may_cast(s_int2, Signed, 1)
            return direct_op('int_mul', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_mul = rtype_mul

    def rtype_div((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = _receive_may_cast(s_int1, Unsigned, 0)
            v_int2 = _receive_may_cast(s_int2, Unsigned, 1)
            return direct_op('uint_div', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = _receive_may_cast(s_int1, Signed, 0)
            v_int2 = _receive_may_cast(s_int2, Signed, 1)
            return direct_op('int_div', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_div = rtype_div

    def rtype_mod((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = _receive_may_cast(s_int1, Unsigned, 0)
            v_int2 = _receive_may_cast(s_int2, Unsigned, 1)
            return direct_op('uint_mod', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = _receive_may_cast(s_int1, Signed, 0)
            v_int2 = _receive_may_cast(s_int2, Signed, 1)
            return direct_op('int_mod', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_mod = rtype_mod

    def rtype_xor((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = _receive_may_cast(s_int1, Unsigned, 0)
            v_int2 = _receive_may_cast(s_int2, Unsigned, 1)
            return direct_op('uint_xor', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = _receive_may_cast(s_int1, Signed, 0)
            v_int2 = _receive_may_cast(s_int2, Signed, 1)
            return direct_op('int_xor', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_xor = rtype_xor

    def rtype_and_((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = _receive_may_cast(s_int1, Unsigned, 0)
            v_int2 = _receive_may_cast(s_int2, Unsigned, 1)
            return direct_op('uint_and', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = _receive_may_cast(s_int1, Signed, 0)
            v_int2 = _receive_may_cast(s_int2, Signed, 1)
            return direct_op('int_and', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_and = rtype_and_

    def rtype_or_((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = _receive_may_cast(s_int1, Unsigned, 0)
            v_int2 = _receive_may_cast(s_int2, Unsigned, 1)
            return direct_op('uint_or', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = _receive_may_cast(s_int1, Signed, 0)
            v_int2 = _receive_may_cast(s_int2, Signed, 1)
            return direct_op('int_or', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_or = rtype_or_

    def rtype_lshift((s_int1, s_int2)):
        if s_int1.unsigned:
            v_int1 = _receive_may_cast(s_int1, Unsigned, 0)
            v_int2 = _receive_may_cast(s_int2, Unsigned, 1)
            return direct_op('uint_lshift', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = _receive_may_cast(s_int1, Signed, 0)
            v_int2 = _receive_may_cast(s_int2, Signed, 1)
            return direct_op('int_lshift', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_lshift = rtype_lshift

    def rtype_rshift((s_int1, s_int2)):
        if s_int1.unsigned:
            v_int1 = _receive_may_cast(s_int1, Unsigned, 0)
            v_int2 = _receive_may_cast(s_int2, Unsigned, 1)
            return direct_op('uint_rshift', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = _receive_may_cast(s_int1, Signed, 0)
            v_int2 = _receive_may_cast(s_int2, Signed, 1)
            return direct_op('int_rshift', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_rshift = rtype_rshift

    def rtype_lshift_ovf((s_int1, s_int2)):
        if s_int1.unsigned:
            v_int1 = _receive_may_cast(s_int1, Unsigned, 0)
            v_int2 = _receive_may_cast(s_int2, Unsigned, 1)
            return direct_op('uint_lshift_ovf', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = _receive_may_cast(s_int1, Signed, 0)
            v_int2 = _receive_may_cast(s_int2, Signed, 1)
            return direct_op('int_lshift_ovf', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_lshift_ovf = rtype_lshift_ovf

    def rtype_rshift_ovf((s_int1, s_int2)):
        if s_int1.unsigned:
            v_int1 = _receive_may_cast(s_int1, Unsigned, 0)
            v_int2 = _receive_may_cast(s_int2, Unsigned, 1)
            return direct_op('uint_rshift_ovf', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = _receive_may_cast(s_int1, Signed, 0)
            v_int2 = _receive_may_cast(s_int2, Signed, 1)
            return direct_op('int_rshift_ovf', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_rshift_ovf = rtype_rshift_ovf

    def rtype_pow((s_int1, s_int2), s_int3=SomePBC({None: True})):
        if isinstance(s_int3, SomeInteger):
            if s_int3.unsigned:
                v_int3_list = [_receive_may_cast(s_int1, Unsigned, 2)]
            else:
                v_int3_list = [_receive_may_cast(s_int1, Signed, 2)]
        elif s_int3.is_constant() and s_int3.const is None:
            v_int3_list = []
        else:
            raise TyperError("pow() 3rd argument must be int or None")
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = _receive_may_cast(s_int1, Unsigned, 0)
            v_int2 = _receive_may_cast(s_int2, Unsigned, 1)
            return direct_op('uint_pow', [v_int1, v_int2] + v_int3_list, resulttype=Unsigned)
        else:
            v_int1 = _receive_may_cast(s_int1, Signed, 0)
            v_int2 = _receive_may_cast(s_int2, Signed, 1)
            return direct_op('int_pow', [v_int1, v_int2] + v_int3_list, resulttype=Signed)

    rtype_inplace_pow = rtype_pow

    #comparisons: eq is_ ne lt le gt ge

    def rtype_eq(args): 
        return _rtype_compare_template(args, 'eq')

    rtype_is_ = rtype_eq

    def rtype_ne(args):
        return _rtype_compare_template(args, 'ne')

    def rtype_lt(args):
        return _rtype_compare_template(args, 'lt')

    def rtype_le(args):
        return _rtype_compare_template(args, 'le')

    def rtype_gt(args):
        return _rtype_compare_template(args, 'gt')

    def rtype_ge(args):
        return _rtype_compare_template(args, 'ge')

#Helper functions

def _receive_may_cast(s_var, s_requested, arg):
    v = receive(s_requested, arg)
    s = (Signed,Unsigned)[s_var.unsigned]
    if s != s_requested:
        if s_requested is Unsigned:
            if debug: print 'cast_int_to_uint'
            return direct_op('cast_int_to_uint', [v], resulttype=Unsigned)
        else:
            if debug: print 'cast_uint_to_int'
            return direct_op('cast_uint_to_int', [v], resulttype=Signed)
    #elif debug:
    #    if s_requested is Unsigned:
    #        if debug: print 'fake cast_uint_to_uint'
    #        return direct_op('cast_uint_to_uint', [v], resulttype=Unsigned)
    #    else:
    #        if debug: print 'fake cast_int_to_int'
    #        return direct_op('cast_int_to_int', [v], resulttype=Signed)
    return v
    
#Helper functions for comparisons

def _rtype_compare_template((s_int1, s_int2), func):
    if s_int1.unsigned or s_int2.unsigned:
        if not s_int1.nonneg or not s_int2.nonneg:
            raise TyperError("comparing a signed and an unsigned number")
        v_int1 = _receive_may_cast(s_int1, Unsigned, 0)
        v_int2 = _receive_may_cast(s_int2, Unsigned, 1)
        return direct_op('uint_'+func, [v_int1, v_int2], resulttype=Bool)
    else:
        v_int1 = _receive_may_cast(s_int1, Signed, 0)
        v_int2 = _receive_may_cast(s_int2, Signed, 1)
        return direct_op('int_'+func, [v_int1, v_int2], resulttype=Bool)


#

class __extend__(SomeInteger):

    def rtype_is_true(s_int):
        v_int = _receive_may_cast(s_int, Signed, 0)
        return direct_op('int_is_true', [v_int], resulttype=Bool)

    #Unary arithmetic operations    
    
    def rtype_abs(s_int):
        if s_int.unsigned:
            return _receive_may_cast(s_int, Unsigned, 0)
        else:
            v_int = _receive_may_cast(s_int, Signed, 0)
            return direct_op('int_abs', [v_int], resulttype=Signed) #XXX I would like to make this Unsigned, but the annotator insists it is Signed!

    def rtype_abs_ovf(s_int):
        if s_int.unsigned:
            return _receive_may_cast(s_int, Unsigned, 0)
        else:
            v_int = _receive_may_cast(s_int, Signed, 0)
            direct_op('int_abs_ovf', [v_int], resulttype=Signed) #XXX I would like to make this Unsigned, but the annotator insists it is Signed!

    def rtype_invert(s_int):
        v_int = _receive_may_cast(s_int, Signed, 0)
        return direct_op('int_invert', [v_int], resulttype=Signed)

    def rtype_neg(s_int):
        v_int = _receive_may_cast(s_int, Signed, 0)
        return direct_op('int_neg', [v_int], resulttype=Signed)

    def rtype_pos(s_int):
        if s_int.unsigned:
            return _receive_may_cast(s_int, Unsigned, 0)
        else:
            return _receive_may_cast(s_int, Signed, 0)

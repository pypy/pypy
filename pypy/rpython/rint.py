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

    #arithmetic
    
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

    def rtype_add_ovf((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = receive(Unsigned, arg=0)
            v_int2 = receive(Unsigned, arg=1)
            return direct_op('uint_add_ovf', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = receive(Signed, arg=0)
            v_int2 = receive(Signed, arg=1)
            return direct_op('int_add_ovf', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_add_ovf = rtype_add_ovf

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

    def rtype_sub_ovf((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = receive(Unsigned, arg=0)
            v_int2 = receive(Unsigned, arg=1)
            return direct_op('uint_sub_ovf', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = receive(Signed, arg=0)
            v_int2 = receive(Signed, arg=1)
            return direct_op('int_sub_ovf', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_sub_ovf = rtype_sub_ovf

    def rtype_mul((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = receive(Unsigned, arg=0)
            v_int2 = receive(Unsigned, arg=1)
            return direct_op('uint_mul', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = receive(Signed, arg=0)
            v_int2 = receive(Signed, arg=1)
            return direct_op('int_mul', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_mul = rtype_mul

    def rtype_div((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = receive(Unsigned, arg=0)
            v_int2 = receive(Unsigned, arg=1)
            return direct_op('uint_div', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = receive(Signed, arg=0)
            v_int2 = receive(Signed, arg=1)
            return direct_op('int_div', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_div = rtype_div

    def rtype_mod((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = receive(Unsigned, arg=0)
            v_int2 = receive(Unsigned, arg=1)
            return direct_op('uint_mod', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = receive(Signed, arg=0)
            v_int2 = receive(Signed, arg=1)
            return direct_op('int_mod', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_mod = rtype_mod

    def rtype_xor((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = receive(Unsigned, arg=0)
            v_int2 = receive(Unsigned, arg=1)
            return direct_op('uint_xor', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = receive(Signed, arg=0)
            v_int2 = receive(Signed, arg=1)
            return direct_op('int_xor', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_xor = rtype_xor

    def rtype_and_((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = receive(Unsigned, arg=0)
            v_int2 = receive(Unsigned, arg=1)
            return direct_op('uint_and', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = receive(Signed, arg=0)
            v_int2 = receive(Signed, arg=1)
            return direct_op('int_and', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_and = rtype_and_

    def rtype_or_((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = receive(Unsigned, arg=0)
            v_int2 = receive(Unsigned, arg=1)
            return direct_op('uint_or', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = receive(Signed, arg=0)
            v_int2 = receive(Signed, arg=1)
            return direct_op('int_or', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_or = rtype_or_

    def rtype_lshift((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = receive(Unsigned, arg=0)
            v_int2 = receive(Unsigned, arg=1)
            return direct_op('uint_lshift', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = receive(Signed, arg=0)
            v_int2 = receive(Signed, arg=1)
            return direct_op('int_lshift', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_lshift = rtype_lshift

    def rtype_rshift((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = receive(Unsigned, arg=0)
            v_int2 = receive(Unsigned, arg=1)
            return direct_op('uint_rshift', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = receive(Signed, arg=0)
            v_int2 = receive(Signed, arg=1)
            return direct_op('int_rshift', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_rshift = rtype_rshift

    def rtype_lshift_ovf((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = receive(Unsigned, arg=0)
            v_int2 = receive(Unsigned, arg=1)
            return direct_op('uint_lshift_ovf', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = receive(Signed, arg=0)
            v_int2 = receive(Signed, arg=1)
            return direct_op('int_lshift_ovf', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_lshift_ovf = rtype_lshift_ovf

    def rtype_rshift_ovf((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = receive(Unsigned, arg=0)
            v_int2 = receive(Unsigned, arg=1)
            return direct_op('uint_rshift_ovf', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = receive(Signed, arg=0)
            v_int2 = receive(Signed, arg=1)
            return direct_op('int_rshift_ovf', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_rshift_ovf = rtype_rshift_ovf

    def rtype_pow((s_int1, s_int2)):
        #XXX RPythonTyper gives this error: TypeError: rtype_pow() takes exactly 1 argument (2 given)
        if s_int1.unsigned or s_int2.unsigned:
            v_int1 = receive(Unsigned, arg=0)
            v_int2 = receive(Unsigned, arg=1)
            return direct_op('uint_pow', [v_int1, v_int2], resulttype=Unsigned)
        else:
            v_int1 = receive(Signed, arg=0)
            v_int2 = receive(Signed, arg=1)
            return direct_op('int_pow', [v_int1, v_int2], resulttype=Signed)

    rtype_inplace_pow = rtype_pow

    #comparisons: eq is_ ne lt le gt ge

    def rtype_eq((s_int1, s_int2)):
        v_int1 = receive(Signed, arg=0)
        v_int2 = receive(Signed, arg=1)
        return direct_op('int_eq', [v_int1, v_int2], resulttype=Bool)
        
    rtype_is_ = rtype_eq

    def rtype_ne((s_int1, s_int2)):
        v_int1 = receive(Signed, arg=0)
        v_int2 = receive(Signed, arg=1)
        return direct_op('int_ne', [v_int1, v_int2], resulttype=Bool)

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

    def rtype_le((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            if not s_int1.nonneg or not s_int2.nonneg:
                raise TyperError("comparing a signed and an unsigned number")
            v_int1 = receive(Unsigned, arg=0)
            v_int2 = receive(Unsigned, arg=1)
            return direct_op('uint_le', [v_int1, v_int2], resulttype=Bool)
        else:
            v_int1 = receive(Signed, arg=0)
            v_int2 = receive(Signed, arg=1)
            return direct_op('int_le', [v_int1, v_int2], resulttype=Bool)

    def rtype_gt((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            if not s_int1.nonneg or not s_int2.nonneg:
                raise TyperError("comparing a signed and an unsigned number")
            v_int1 = receive(Unsigned, arg=0)
            v_int2 = receive(Unsigned, arg=1)
            return direct_op('uint_gt', [v_int1, v_int2], resulttype=Bool)
        else:
            v_int1 = receive(Signed, arg=0)
            v_int2 = receive(Signed, arg=1)
            return direct_op('int_gt', [v_int1, v_int2], resulttype=Bool)

    def rtype_ge((s_int1, s_int2)):
        if s_int1.unsigned or s_int2.unsigned:
            if not s_int1.nonneg or not s_int2.nonneg:
                raise TyperError("comparing a signed and an unsigned number")
            v_int1 = receive(Unsigned, arg=0)
            v_int2 = receive(Unsigned, arg=1)
            return direct_op('uint_ge', [v_int1, v_int2], resulttype=Bool)
        else:
            v_int1 = receive(Signed, arg=0)
            v_int2 = receive(Signed, arg=1)
            return direct_op('int_ge', [v_int1, v_int2], resulttype=Bool)


class __extend__(SomeInteger):

    def rtype_is_true(s_int):
        v_int = receive(Signed, arg=0)
        return direct_op('int_is_true', [v_int], resulttype=Bool)

    #Unary arithmetic operations    
    
    def rtype_abs(s_int):
        v_int = receive(Signed, arg=0)
        return direct_op('int_abs', [v_int], resulttype=Signed)

    def rtype_abs_ovf(s_int):
        v_int = receive(Signed, arg=0)
        return direct_op('int_abs_ovf', [v_int], resulttype=Signed)

    def rtype_invert(s_int):
        v_int = receive(Signed, arg=0)
        return direct_op('int_invert', [v_int], resulttype=Signed)

    def rtype_neg(s_int):
        v_int = receive(Signed, arg=0)
        return direct_op('int_neg', [v_int], resulttype=Signed)

    def rtype_pos(s_int):
        #XXX I think this is a nop and should really be removed from the graph
        v_int = receive(Signed, arg=0)
        return direct_op('int_pos', [v_int], resulttype=Signed)


class __extend__(SomeBool):

    def rtype_is_true(s_bool):
        v_bool = receive(Bool, arg=0)
        return v_bool

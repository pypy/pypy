from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeFloat, SomeInteger, SomeBool, SomePBC
from pypy.rpython.lltype import Signed, Unsigned, Bool, Float
from pypy.rpython.rtyper import peek_at_result_annotation, receive, direct_op
from pypy.rpython.rtyper import TyperError


class __extend__(pairtype(SomeFloat, SomeFloat)):

    def rtype_add(args):
        return _rtype_template(args, 'add')

    rtype_inplace_add = rtype_add

    def rtype_sub(args):
        return _rtype_template(args, 'sub')

    rtype_inplace_sub = rtype_sub

    def rtype_mul(args):
        return _rtype_template(args, 'mul')

    rtype_inplace_mul = rtype_mul

    def rtype_div(args):
        return _rtype_template(args, 'div')

    rtype_inplace_div = rtype_div

    def rtype_pow((s_float1, s_float2), s_float3=SomePBC({None: True})):
        if isinstance(s_float3, SomeInteger):
            v_float3_list = [receive(Float, arg=2)]
        elif s_float3.is_constant() and s_float3.const is None:
            v_float3_list = []
        else:
            raise TyperError("pow() 3rd argument must be int or None")
        v_float1 = receive(Float, arg=0)
        v_float2 = receive(Float, arg=1)
        return direct_op('float_pow', [v_float1, v_float2] + v_float3_list, resulttype=Float)

    rtype_inplace_pow = rtype_pow


#Helpers SomeFloat,Somefloat

def _rtype_template((s_float1, s_float2), func):
        v_float1 = receive(Float, arg=0)
        v_float2 = receive(Float, arg=1)
        return direct_op('float_'+func, [v_float1, v_float2], resulttype=Float)


#

class __extend__(pairtype(SomeFloat, SomeInteger)):
    pass


class __extend__(SomeFloat):

    def rtype_is_true(s_float):
        v_float = receive(Float, arg=0)
        return direct_op('float_is_true', [v_float], resulttype=Bool)

    def rtype_neg(s_int):
        v_int = receive(Float, arg=0)
        return direct_op('float_neg', [v_int], resulttype=Float)

    def rtype_pos(s_int):
        return receive(Float, arg=0)

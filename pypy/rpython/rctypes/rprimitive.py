from pypy.rpython.rmodel import inputconst
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.rstr import CharRepr, UniCharRepr
from pypy.tool.pairtype import pairtype
from pypy.rpython.rmodel import IntegerRepr, FloatRepr
from pypy.rpython.error import TyperError
from pypy.rpython.rctypes.rmodel import CTypesValueRepr


class PrimitiveRepr(CTypesValueRepr):

    def __init__(self, rtyper, s_ctypesobject, ll_type):
        CTypesValueRepr.__init__(self, rtyper, s_ctypesobject, ll_type)
        if isinstance(ll_type, lltype.Number):
            normalized_lltype = ll_type.normalized()
        else:
            normalized_lltype = ll_type
        self.value_repr = rtyper.getprimitiverepr(ll_type)
        self.normalized_value_repr = rtyper.getprimitiverepr(normalized_lltype)
            
    def return_c_data(self, llops, v_c_data):
        """Read out the atomic data from a raw C pointer.
        Used when the data is returned from an operation or C function call.
        """
        v_value = self.getvalue_from_c_data(llops, v_c_data)
        return self.return_value(llops, v_value)

    def return_value(self, llops, v_value):
        # like return_c_data(), but when the input is only the value
        # field instead of the c_data pointer
        return llops.convertvar(v_value, self.value_repr,
                               self.normalized_value_repr)

    def rtype_getattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        assert s_attr.const == 'value'
        v_primitive = hop.inputarg(self, 0)
        hop.exception_cannot_occur()
        v_c_data = self.get_c_data(hop.llops, v_primitive)
        return self.return_c_data(hop.llops, v_c_data)

    def rtype_setattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        assert s_attr.const == 'value'
        v_primitive, v_attr, v_value = hop.inputargs(self, lltype.Void,
                                                        self.ll_type)
        self.setvalue(hop.llops, v_primitive, v_value)

    def rtype_is_true(self, hop):
        [v_box] = hop.inputargs(self)
        v_value = self.return_value(hop.llops, self.getvalue(hop.llops, v_box))
        if v_value.concretetype in (lltype.Char, lltype.UniChar):
            llfn = ll_c_char_is_true
        else:
            llfn = ll_is_true
        return hop.gendirectcall(llfn, v_value)

    def initialize_const(self, p, value):
        if isinstance(value, self.ctype):
            value = value.value
        p.c_data[0] = lltype.cast_primitive(self.ll_type, value)

def ll_is_true(x):
    return bool(x)

def ll_c_char_is_true(x):
    return bool(ord(x))

class __extend__(pairtype(IntegerRepr, PrimitiveRepr),
                 pairtype(FloatRepr, PrimitiveRepr),
                 pairtype(CharRepr, PrimitiveRepr),
                 pairtype(UniCharRepr, PrimitiveRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        # first convert 'v' to the precise expected low-level type
        r_input = r_to.rtyper.getprimitiverepr(r_to.ll_type)
        v = llops.convertvar(v, r_from, r_input)
        # allocate a memory-owning box to hold a copy of the ll value 'v'
        r_temp = r_to.r_memoryowner
        v_owned_box = r_temp.allocate_instance(llops)
        r_temp.setvalue(llops, v_owned_box, v)
        # return this box possibly converted to the expected output repr,
        # which might be a memory-aliasing box
        return llops.convertvar(v_owned_box, r_temp, r_to)

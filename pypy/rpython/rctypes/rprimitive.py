from pypy.rpython.rmodel import inputconst
from pypy.rpython.lltypesystem import lltype
from pypy.annotation.pairtype import pairtype
from pypy.rpython.rmodel import IntegerRepr, FloatRepr, CharRepr
from pypy.rpython.error import TyperError
from pypy.rpython.rctypes.rmodel import CTypesValueRepr


class PrimitiveRepr(CTypesValueRepr):

    def return_c_data(self, llops, v_c_data):
        """Read out the atomic data from a raw C pointer.
        Used when the data is returned from an operation or C function call.
        """
        return self.getvalue_from_c_data(llops, v_c_data)

    def return_value(self, llops, v_value):
        # like return_c_data(), but when the input is only the value
        # field instead of the c_data pointer
        return v_value

    def rtype_getattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        assert s_attr.const == 'value'
        v_primitive = hop.inputarg(self, 0)
        return self.getvalue(hop.llops, v_primitive)

    def rtype_setattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        assert s_attr.const == 'value'
        v_primitive, v_attr, v_value = hop.inputargs(self, lltype.Void,
                                                        self.ll_type)
        self.setvalue(hop.llops, v_primitive, v_value)


class __extend__(pairtype(IntegerRepr, PrimitiveRepr),
                 pairtype(FloatRepr, PrimitiveRepr),
                 pairtype(CharRepr, PrimitiveRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        # first convert 'v' to the precise expected low-level type
        r_input = r_to.rtyper.primitive_to_repr[r_to.ll_type]
        v = llops.convertvar(v, r_from, r_input)
        # allocate a memory-owning box to hold a copy of the ll value 'v'
        r_temp = r_to.r_memoryowner
        v_owned_box = r_temp.allocate_instance(llops)
        r_temp.setvalue(llops, v_owned_box, v)
        # return this box possibly converted to the expected output repr,
        # which might be a memory-aliasing box
        return llops.convertvar(v_owned_box, r_temp, r_to)

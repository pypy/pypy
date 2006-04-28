from pypy.rpython.rctypes.implementation import CTypesCallEntry, CTypesObjEntry
from pypy.annotation.model import SomeString

from ctypes import c_char_p


class CallEntry(CTypesCallEntry):
    "Annotation and rtyping of calls to c_char_p."
    _about_ = c_char_p

    def specialize_call(self, hop):
        string_repr = hop.rtyper.type_system.rstr.string_repr
        r_char_p = hop.r_result
        v_result = r_char_p.allocate_instance(hop.llops)
        if len(hop.args_s):
            v_value, = hop.inputargs(string_repr)
            r_char_p.setstring(hop.llops, v_result, v_value)
        return v_result


class ObjEntry(CTypesObjEntry):
    "Annotation and rtyping of c_char_p instances."
    _type_ = c_char_p

    s_return_trick = SomeString(can_be_None=True)

    def get_field_annotation(self, s_char_p, fieldname):
        assert fieldname == 'value'
        return self.s_return_trick

    def get_repr(self, rtyper, s_char_p):
        from pypy.rpython.rctypes import rchar_p
        return rchar_p.CCharPRepr(rtyper, s_char_p, rchar_p.CCHARP)

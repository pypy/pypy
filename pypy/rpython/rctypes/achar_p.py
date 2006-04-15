from pypy.rpython import extregistry
from pypy.annotation import model as annmodel

from ctypes import c_char_p


def c_char_p_compute_result_annotation(s_arg=None):
    return annmodel.SomeCTypesObject(c_char_p,
            annmodel.SomeCTypesObject.OWNSMEMORY)

def c_char_p_specialize_call(hop):
    from pypy.rpython.rstr import string_repr
    r_char_p = hop.r_result
    v_result = r_char_p.allocate_instance(hop.llops)
    if len(hop.args_s):
        v_value, = hop.inputargs(string_repr)
        r_char_p.setstring(hop.llops, v_result, v_value)
    return v_result

extregistry.register_value(c_char_p,
    compute_result_annotation=c_char_p_compute_result_annotation,
    specialize_call=c_char_p_specialize_call
    )

def c_char_compute_annotation(the_type, instance):
    return annmodel.SomeCTypesObject(c_char_p,
                                     annmodel.SomeCTypesObject.OWNSMEMORY)

def c_char_p_get_repr(rtyper, s_char_p):
    from pypy.rpython.rctypes import rchar_p
    return rchar_p.CCharPRepr(rtyper, s_char_p, rchar_p.CCHARP)

entry = extregistry.register_type(c_char_p,
        compute_annotation = c_char_compute_annotation,
        get_repr           = c_char_p_get_repr,
        )
s_value_annotation = annmodel.SomeString(can_be_None=True)
def c_char_p_get_field_annotation(s_char_p, fieldname):
    assert fieldname == 'value'
    return s_value_annotation
entry.get_field_annotation = c_char_p_get_field_annotation
entry.s_return_trick = s_value_annotation

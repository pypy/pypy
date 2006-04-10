from pypy.rpython import extregistry
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.rstr import string_repr
from pypy.rpython.rctypes.rmodel import CTypesValueRepr
from pypy.annotation import model as annmodel

from ctypes import c_char_p


class CCharPRepr(CTypesValueRepr):

    def get_content_keepalives(self):
        "Return an extra keepalive field used for the RPython string."
        return [('keepalive_str', string_repr.lowleveltype)]

    def getstring(self, llops, v_box):
        v_c_data = self.get_c_data(llops, v_box)
        return llops.gendirectcall(ll_getstring, v_box, v_c_data)

    def setstring(self, llops, v_box, v_str):
        v_c_data = self.get_c_data(llops, v_box)
        llops.gendirectcall(ll_setstring, v_box, v_c_data, v_str)

    def rtype_getattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        assert s_attr.const == 'value'
        v_char_p = hop.inputarg(self, 0)
        return self.getstring(hop.llops, v_char_p)

    def rtype_setattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        assert s_attr.const == 'value'
        v_char_p, v_attr, v_value = hop.inputargs(self, lltype.Void,
                                                  string_repr)
        self.setstring(hop.llops, v_char_p, v_value)


CCHARP = llmemory.Address    # char *
FIRSTITEMOFS = llmemory.ArrayItemsOffset(string_repr.lowleveltype.TO.chars)

def ll_strlen(p):
    i = 0
    while ord(p.char[i]) != 0:
        i += 1
    return i

def ll_strnlen(p, maxlen):
    i = 0
    while i < maxlen and ord(p.char[i]) != 0:
        i += 1
    return i

def ll_str2charp(s):
    return llmemory.cast_ptr_to_adr(s.chars) + FIRSTITEMOFS

def ll_getstring(box, c_data):
    p = c_data.value
    if p:
        if (box.keepalive_str and ll_str2charp(box.keepalive_str) == p):
            maxlen = len(box.keepalive_str.chars)
            length = ll_strnlen(p, maxlen)
            if length == maxlen:
                # no embedded zero in the string
                return box.keepalive_str
        else:
            length = ll_strlen(p)
        newstr = lltype.malloc(string_repr.lowleveltype.TO, length)
        for i in range(length):
            newstr.chars[i] = p.char[i]
        return newstr
    else:
        return lltype.nullptr(string_repr.lowleveltype.TO)

def ll_setstring(box, c_data, string):
    if string:
        c_data.value = ll_str2charp(string)
    else:
        c_data.value = llmemory.NULL
    box.keepalive_str = string


def c_char_p_compute_result_annotation(s_arg=None):
    return annmodel.SomeCTypesObject(c_char_p,
            annmodel.SomeCTypesObject.OWNSMEMORY)

def c_char_p_specialize_call(hop):
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

def c_char_p_get_repr(rtyper, s_char_p):
    return CCharPRepr(rtyper, s_char_p, CCHARP)

entry = extregistry.register_type(c_char_p,
        compute_annotation = annmodel.SomeCTypesObject(c_char_p,
                                       annmodel.SomeCTypesObject.OWNSMEMORY),
        get_repr = c_char_p_get_repr,
        )
def c_char_p_get_field_annotation(s_char_p, fieldname):
    assert fieldname == 'value'
    return annmodel.SomeString(can_be_None=True)
entry.get_field_annotation = c_char_p_get_field_annotation

from pypy.rpython import extregistry
from pypy.rpython.rmodel import inputconst
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.rstr import StringRepr, string_repr
from pypy.rpython.rctypes.rmodel import CTypesValueRepr
from pypy.rpython.rctypes.rarray import ArrayRepr
from pypy.annotation import model as annmodel
from pypy.annotation.pairtype import pairtype

from ctypes import c_char, c_char_p


class CCharPRepr(CTypesValueRepr):

    def get_content_keepalives(self):
        "Return an extra keepalive field used for the RPython string."
        return [('keepalive_str', string_repr.lowleveltype)]

    def getstring(self, llops, v_box):
        return llops.gendirectcall(ll_getstring, v_box)

    def setstring(self, llops, v_box, v_str):
        llops.gendirectcall(ll_setstring, v_box, v_str)

    def initialize_const(self, p, string):
        if isinstance(string, c_char_p):
            string = string.value
        llstring = string_repr.convert_const(string)
        ll_setstring(p, llstring)

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


class __extend__(pairtype(StringRepr, CCharPRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        # r_from could be char_repr: first convert it to string_repr
        v = llops.convertvar(v, r_from, string_repr)
        r_temp = r_to.r_memoryowner
        v_owned_box = r_temp.allocate_instance(llops)
        r_temp.setstring(llops, v_owned_box, v)
        return llops.convertvar(v_owned_box, r_temp, r_to)

##class __extend__(pairtype(ArrayRepr, CCharPRepr)):
##    def convert_from_to((r_from, r_to), v, llops):
##        if r_from.r_item.ctype != c_char:
##            return NotImplemented
##        # warning: no keepalives, only for short-lived conversions like
##        # in argument passing
##        r_temp = r_to.r_memoryowner
##        v_owned_box = r_temp.allocate_instance(llops)
##        v_char_array_ptr = r_from.get_c_data(llops, v)
##        v_char_array_adr = llops.genop('cast_ptr_to_adr', [v_char_array_ptr],
##                                       resulttype = llmemory.Address)
##        cofs = inputconst(lltype.Signed,
##                          llmemory.itemoffsetof(r_from.ll_type) +
##                          llmemory.offsetof(r_from.ll_type.OF, 'value'))
##        v_first_char_adr = llops.genop('adr_add', [v_char_array_adr, cofs],
##                                       resulttype = llmemory.Address)
##        r_temp.setvalue(llops, v_owned_box, v_first_char_adr)
##        return llops.convertvar(v_owned_box, r_temp, r_to)


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

def ll_getstring(box):
    p = box.c_data.value
    if p:
        if box.keepalive_str and ll_str2charp(box.keepalive_str) == p:
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

def ll_setstring(box, string):
    if string:
        box.c_data.value = ll_str2charp(string)
    else:
        box.c_data.value = llmemory.NULL
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

def c_char_compute_annotation(the_type, instance):
    return annmodel.SomeCTypesObject(c_char_p,
                                     annmodel.SomeCTypesObject.OWNSMEMORY)

def c_char_p_get_repr(rtyper, s_char_p):
    return CCharPRepr(rtyper, s_char_p, CCHARP)

entry = extregistry.register_type(c_char_p,
        compute_annotation = c_char_compute_annotation,
        get_repr           = c_char_p_get_repr,
        )
def c_char_p_get_field_annotation(s_char_p, fieldname):
    assert fieldname == 'value'
    return annmodel.SomeString(can_be_None=True)
entry.get_field_annotation = c_char_p_get_field_annotation

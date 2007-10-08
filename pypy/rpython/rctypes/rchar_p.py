from pypy.rpython.rmodel import inputconst
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rstr import AbstractStringRepr
from pypy.rpython.lltypesystem.rstr import string_repr
from pypy.rpython.rctypes.rmodel import CTypesValueRepr, C_ZERO
from pypy.rpython.rctypes.rmodel import unsafe_getfield
from pypy.rpython.rctypes.rarray import ArrayRepr
from pypy.rpython.rctypes.rstringbuf import StringBufRepr
from pypy.tool.pairtype import pairtype

from ctypes import c_char, c_char_p, cast


class CCharPRepr(CTypesValueRepr):

    def return_c_data(self, llops, v_c_data):
        """Read out the RPython string from a raw C pointer.
        Used when the data is returned from an operation or C function call.
        """
        v_char_p = self.getvalue_from_c_data(llops, v_c_data)
        return llops.gendirectcall(ll_charp2str, v_char_p)

    def return_value(self, llops, v_value):
        # like return_c_data(), but when the input is only the value
        # field instead of the c_data pointer
        return llops.gendirectcall(ll_charp2str, v_value)

    def cast_return_value(self, llops, v_value):
        # This should not return a string but a char pointer
        return CTypesValueRepr.return_value(self, llops, v_value)

    def get_content_keepalive_type(self):
        "An extra keepalive used for the RPython string."
        return string_repr.lowleveltype

    def getstring(self, llops, v_box):
        return llops.gendirectcall(ll_getstring, v_box)

    def setstring(self, llops, v_box, v_str):
        llops.gendirectcall(ll_setstring, v_box, v_str)

    def convert_const(self, value):
        if value is not None and not isinstance(value, (str, c_char_p)):
            # maybe an array of characters? cast to a c_char_p
            assert type(value)._type_ == c_char
            value = cast(value, c_char_p)
        return super(CCharPRepr, self).convert_const(value)

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
        hop.exception_cannot_occur()
        return self.getstring(hop.llops, v_char_p)

    def rtype_setattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        assert s_attr.const == 'value'
        v_char_p, v_attr, v_value = hop.inputargs(self, lltype.Void,
                                                  string_repr)
        self.setstring(hop.llops, v_char_p, v_value)


class __extend__(pairtype(AbstractStringRepr, CCharPRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        # r_from could be char_repr: first convert it to string_repr
        v = llops.convertvar(v, r_from, string_repr)
        r_temp = r_to.r_memoryowner
        v_owned_box = r_temp.allocate_instance(llops)
        r_temp.setstring(llops, v_owned_box, v)
        return llops.convertvar(v_owned_box, r_temp, r_to)

class __extend__(pairtype(ArrayRepr, CCharPRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        if r_from.r_item.ctype != c_char:
            return NotImplemented
        # warning: no keepalives, only for short-lived conversions like
        # in argument passing
        r_temp = r_to.r_memoryowner
        v_owned_box = r_temp.allocate_instance(llops)
        v_c_array = r_from.get_c_data_of_item(llops, v, C_ZERO)
        r_temp.setvalue(llops, v_owned_box, v_c_array)
        return llops.convertvar(v_owned_box, r_temp, r_to)

class __extend__(pairtype(StringBufRepr, CCharPRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        # warning: no keepalives, only for short-lived conversions like
        # in argument passing
        r_temp = r_to.r_memoryowner
        v_owned_box = r_temp.allocate_instance(llops)
        v_c_array = r_from.get_c_data_of_item(llops, v, C_ZERO)
        r_temp.setvalue(llops, v_owned_box, v_c_array)
        return llops.convertvar(v_owned_box, r_temp, r_to)
        # XXX some code duplication above


CCHARP = lltype.Ptr(lltype.FixedSizeArray(lltype.Char, 1))

def ll_strlen(p):
    i = 0
    while ord(p[i]) != 0:
        i += 1
    return i

def ll_strnlen(p, maxlen):
    i = 0
    while i < maxlen and ord(p[i]) != 0:
        i += 1
    return i

def ll_str2charp(s):
    return lltype.direct_arrayitems(unsafe_getfield(s, 'chars'))

def ll_charp2str(p):
    if not p:
        return lltype.nullptr(string_repr.lowleveltype.TO)
    length = ll_strlen(p)
    newstr = lltype.malloc(string_repr.lowleveltype.TO, length)
    newstr.hash = 0
    for i in range(length):
        newstr.chars[i] = p[i]
    return newstr

def ll_getstring(box):
    p = box.c_data[0]
    if p:
        if box.keepalive and ll_str2charp(box.keepalive) == p:
            maxlen = len(box.keepalive.chars)
            length = ll_strnlen(p, maxlen)
            if length == maxlen:
                # no embedded zero in the string
                return box.keepalive
        else:
            length = ll_strlen(p)
        newstr = lltype.malloc(string_repr.lowleveltype.TO, length)
        newstr.hash = 0
        for i in range(length):
            newstr.chars[i] = p[i]
        return newstr
    else:
        return lltype.nullptr(string_repr.lowleveltype.TO)

def ll_setstring(box, string):
    if string:
        box.c_data[0] = ll_str2charp(string)
    else:
        box.c_data[0] = lltype.nullptr(CCHARP.TO)
    box.keepalive = string

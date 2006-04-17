from pypy.rpython import extregistry
from pypy.annotation import model as annmodel

from ctypes import create_string_buffer, c_char


class StringBufferType(object):
    """Placeholder for the result type of create_string_buffer(),
    which cannot be represented as a regular ctypes type because
    the length is not an annotation-time constant.
    """
    _type_ = c_char
    #_length_ = unspecified


def stringbuf_compute_result_annotation(s_length):
    if s_length.knowntype != int:
        raise Exception("rctypes only supports create_string_buffer(length)")
    return annmodel.SomeCTypesObject(StringBufferType,
            annmodel.SomeCTypesObject.OWNSMEMORY)

def stringbuf_specialize_call(hop):
    from pypy.rpython.lltypesystem import lltype
    [v_length] = hop.inputargs(lltype.Signed)
    r_stringbuf = hop.r_result
    return hop.genop("malloc_varsize", [
        hop.inputconst(lltype.Void, r_stringbuf.lowleveltype.TO),
        v_length,
        ], resulttype=r_stringbuf.lowleveltype,
    )

extregistry.register_value(create_string_buffer,
    compute_result_annotation=stringbuf_compute_result_annotation,
    specialize_call=stringbuf_specialize_call,
    )

def stringbuf_get_repr(rtyper, s_stringbuf):
    from pypy.rpython.rctypes import rstringbuf
    return rstringbuf.StringBufRepr(rtyper, s_stringbuf, rstringbuf.STRBUFTYPE)

extregistry.register_type(StringBufferType,
    get_repr=stringbuf_get_repr)

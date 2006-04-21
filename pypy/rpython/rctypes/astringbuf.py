from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.rctypes.implementation import CTypesObjEntry
from pypy.annotation.model import SomeCTypesObject, SomeString

from ctypes import create_string_buffer, c_char


class StringBufferType(object):
    """Placeholder for the result type of create_string_buffer(),
    which cannot be represented as a regular ctypes type because
    the length is not an annotation-time constant.
    """
    _type_ = c_char
    #_length_ = unspecified


class CreateStringBufferFnEntry(ExtRegistryEntry):
    "Annotation and rtyping of calls to ctypes.create_string_buffer()"
    _about_ = create_string_buffer

    def compute_result_annotation(self, s_length):
        if s_length.knowntype != int:
            raise Exception("only supports create_string_buffer(length)")
        return SomeCTypesObject(StringBufferType, SomeCTypesObject.OWNSMEMORY)

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        [v_length] = hop.inputargs(lltype.Signed)
        r_stringbuf = hop.r_result
        return hop.genop("malloc_varsize", [
            hop.inputconst(lltype.Void, r_stringbuf.lowleveltype.TO),
            v_length,
            ], resulttype=r_stringbuf.lowleveltype,
        )


class ObjEntry(CTypesObjEntry):
    "Annotation and rtyping of instances of the pseudo-ctype StringBufferType"
    _type_ = StringBufferType

    def get_field_annotation(self, s_array, fieldname):
        assert fieldname == 'value'
        return SomeString()   # can_be_None = False

    def get_repr(self, rtyper, s_stringbuf):
        from pypy.rpython.rctypes import rstringbuf
        return rstringbuf.StringBufRepr(rtyper, s_stringbuf,
                                        rstringbuf.STRBUFTYPE)

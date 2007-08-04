from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.rctypes.implementation import CTypesObjEntry
from pypy.annotation.model import SomeCTypesObject, SomeString, SomeInteger
from pypy.rlib.rarithmetic import r_uint
from ctypes import create_string_buffer, c_char, sizeof

######################################################################
#  NOTE: astringbuf and rstringbuf should be removed and replaced    #
#        with a regular var-sized array of char, now that we         #
#        support var-sized arrays.                                   #
######################################################################


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
        if s_length.knowntype not in (int, r_uint):
            raise Exception("only supports create_string_buffer(length)")
        return SomeCTypesObject(StringBufferType, ownsmemory=True)

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        [v_length] = hop.inputargs(lltype.Signed)
        r_stringbuf = hop.r_result
        hop.exception_cannot_occur()
        return hop.genop("malloc_varsize", [
            hop.inputconst(lltype.Void, r_stringbuf.lowleveltype.TO),
            hop.inputconst(lltype.Void, {'flavor': 'gc', 'zero': True}),
            v_length,
            ], resulttype=r_stringbuf.lowleveltype,
        )


class ObjEntry(CTypesObjEntry):
    "Annotation and rtyping of instances of the pseudo-ctype StringBufferType"
    _type_ = StringBufferType

    def get_field_annotation(self, s_array, fieldname):
        assert fieldname in ('value', 'raw')
        return SomeString()   # can_be_None = False

    def get_repr(self, rtyper, s_stringbuf):
        from pypy.rpython.rctypes import rstringbuf
        return rstringbuf.StringBufRepr(rtyper, s_stringbuf,
                                        rstringbuf.STRBUFTYPE)


class SizeOfFnEntry(ExtRegistryEntry):
    "Annotation and rtyping of calls to ctypes.sizeof()"
    _about_ = sizeof

    def compute_result_annotation(self, s_arg):
        return SomeInteger(nonneg=True)

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype, llmemory
        from pypy.rpython.error import TyperError
        [s_arg] = hop.args_s
        [r_arg] = hop.args_r
        hop.exception_cannot_occur()
        if isinstance(s_arg, SomeCTypesObject):
            if s_arg.knowntype is StringBufferType:
                # sizeof(string_buffer) == len(string_buffer)
                return r_arg.rtype_len(hop)
        else:
            if not s_arg.is_constant():
                raise TyperError("ctypes.sizeof(non_constant_type)")
            # XXX check that s_arg.const is really a ctypes type
            ctype = s_arg.const
            s_arg = SomeCTypesObject(ctype, ownsmemory=True)
            r_arg = hop.rtyper.getrepr(s_arg)
        return hop.inputconst(lltype.Signed, llmemory.sizeof(r_arg.ll_type))

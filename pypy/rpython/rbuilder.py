
from pypy.rpython.rmodel import Repr
from pypy.rpython.lltypesystem import lltype
from pypy.rlib.rstring import INIT_SIZE
from pypy.annotation.model import SomeChar, SomeUnicodeCodePoint

class AbstractStringBuilderRepr(Repr):
    def rtyper_new(self, hop):
        if len(hop.args_v) == 0:
            v_arg = hop.inputconst(lltype.Signed, INIT_SIZE)
        else:
            v_arg = hop.inputarg(lltype.Signed, 0)
        hop.exception_cannot_occur()
        return hop.gendirectcall(self.ll_new, v_arg)

    def rtype_method_append(self, hop):
        if isinstance(hop.args_s[1], (SomeChar, SomeUnicodeCodePoint)):
            vlist = hop.inputargs(self, self.char_repr)
            func = self.ll_append_char
        else:
            vlist = hop.inputargs(self, self.string_repr)
            func = self.ll_append
        hop.exception_cannot_occur()
        return hop.gendirectcall(func, *vlist)

    def rtype_method_append_slice(self, hop):
        vlist = hop.inputargs(self, self.string_repr,
                              lltype.Signed, lltype.Signed)
        hop.exception_cannot_occur()
        return hop.gendirectcall(self.ll_append_slice, *vlist)

    def rtype_method_append_multiple_char(self, hop):
        vlist = hop.inputargs(self, self.char_repr, lltype.Signed)
        hop.exception_cannot_occur()
        return hop.gendirectcall(self.ll_append_multiple_char, *vlist)

    def rtype_method_append_charpsize(self, hop):
        vlist = hop.inputargs(self, self.raw_ptr_repr, lltype.Signed)
        hop.exception_cannot_occur()
        return hop.gendirectcall(self.ll_append_charpsize, *vlist)

    def rtype_method_getlength(self, hop):
        vlist = hop.inputargs(self)
        hop.exception_cannot_occur()
        return hop.gendirectcall(self.ll_getlength, *vlist)

    def rtype_method_build(self, hop):
        vlist = hop.inputargs(self)
        hop.exception_cannot_occur()
        return hop.gendirectcall(self.ll_build, *vlist)

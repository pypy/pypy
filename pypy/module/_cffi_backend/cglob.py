from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.module._cffi_backend.cdataobj import W_CData
from pypy.module._cffi_backend import newtype
from rpython.rlib.objectmodel import we_are_translated
from rpython.rtyper.lltypesystem import lltype, rffi

FNPTR = rffi.CCallback([], rffi.VOIDP)


class W_GlobSupport(W_Root):
    _immutable_fields_ = ['w_ctype', 'ptr', 'fetch_addr']

    def __init__(self, space, w_ctype, ptr=lltype.nullptr(rffi.CCHARP.TO),
                 fetch_addr=lltype.nullptr(rffi.VOIDP.TO)):
        self.space = space
        self.w_ctype = w_ctype
        self.ptr = ptr
        self.fetch_addr = rffi.cast(FNPTR, fetch_addr)

    def fetch_global_var_addr(self):
        if self.ptr:
            return self.ptr
        result = self.fetch_addr()
        return rffi.cast(rffi.CCHARP, result)

    def read_global_var(self):
        return self.w_ctype.convert_to_object(self.fetch_global_var_addr())

    def write_global_var(self, w_newvalue):
        self.w_ctype.convert_from_object(self.fetch_global_var_addr(),
                                         w_newvalue)

    def address(self):
        w_ctypeptr = newtype.new_pointer_type(self.space, self.w_ctype)
        return W_CData(self.space, self.fetch_global_var_addr(), w_ctypeptr)

W_GlobSupport.typedef = TypeDef("FFIGlobSupport")
W_GlobSupport.typedef.acceptable_as_base_class = False

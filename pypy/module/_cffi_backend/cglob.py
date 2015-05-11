from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.module._cffi_backend.cdataobj import W_CData
from pypy.module._cffi_backend import newtype


class W_GlobSupport(W_Root):
    def __init__(self, space, w_ctype, ptr):
        self.space = space
        self.w_ctype = w_ctype
        self.ptr = ptr

    def read_global_var(self):
        return self.w_ctype.convert_to_object(self.ptr)

    def write_global_var(self, w_newvalue):
        self.w_ctype.convert_from_object(self.ptr, w_newvalue)

    def address(self):
        w_ctypeptr = newtype.new_pointer_type(self.space, self.w_ctype)
        return W_CData(self.space, self.ptr, w_ctypeptr)

W_GlobSupport.typedef = TypeDef("FFIGlobSupport")
W_GlobSupport.typedef.acceptable_as_base_class = False

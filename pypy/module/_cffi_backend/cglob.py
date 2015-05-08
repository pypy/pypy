from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.module._cffi_backend.cdataobj import W_CData


class W_GlobSupport(W_Root):
    def __init__(self, space, w_ctype, ptr):
        self.space = space
        self.w_ctype = w_ctype
        self.ptr = ptr

    def read_global_var(self):
        return self.w_ctype.convert_to_object(self.ptr)

W_GlobSupport.typedef = TypeDef("FFIGlobSupport")
W_GlobSupport.typedef.acceptable_as_base_class = False

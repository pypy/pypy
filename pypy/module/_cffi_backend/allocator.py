from pypy.interpreter.error import oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault

from rpython.rtyper.lltypesystem import lltype, rffi


class W_Allocator(W_Root):
    _immutable_ = True

    def __init__(self, ffi, should_clear_after_alloc):
        self.ffi = ffi
        self.should_clear_after_alloc = should_clear_after_alloc

    def allocate(self, space, datasize, ctype, length=-1):
        from pypy.module._cffi_backend.cdataobj import W_CDataNewStd
        if self.should_clear_after_alloc:
            ptr = lltype.malloc(rffi.CCHARP.TO, datasize,
                                flavor='raw', zero=True)
        else:
            ptr = lltype.malloc(rffi.CCHARP.TO, datasize,
                                flavor='raw', zero=False)
        return W_CDataNewStd(space, ptr, ctype, length)

    @unwrap_spec(w_init=WrappedDefault(None))
    def descr_call(self, space, w_arg, w_init):
        from pypy.module._cffi_backend.ctypeobj import W_CType
        if isinstance(w_arg, W_CType):
            w_ctype = w_arg
        else:
            ffi = self.ffi
            if ffi is None:
                raise oefmt(space.w_TypeError,
                            "expected a ctype object, got '%T'", w_arg)
            w_ctype = ffi.ffi_type(w_arg, ffi.ACCEPT_STRING)
        return w_ctype.newp(w_init, self)


W_Allocator.typedef = TypeDef(
        'FFIAllocator',
        __call__ = interp2app(W_Allocator.descr_call),
        )
W_Allocator.typedef.acceptable_as_base_class = False


default_allocator = W_Allocator(ffi=None, should_clear_after_alloc=True)
nonzero_allocator = W_Allocator(ffi=None, should_clear_after_alloc=False)

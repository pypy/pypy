from pypy.interpreter.error import oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault

from rpython.rtyper.lltypesystem import lltype, rffi


class W_Allocator(W_Root):
    _immutable_ = True

    def __init__(self, ffi, w_alloc, w_free, should_clear_after_alloc):
        self.ffi = ffi    # may be None
        self.w_alloc = w_alloc
        self.w_free = w_free
        self.should_clear_after_alloc = should_clear_after_alloc

    def allocate(self, space, datasize, ctype, length=-1):
        from pypy.module._cffi_backend import cdataobj, ctypeptr, ffi_obj
        if self.w_alloc is None:
            if self.should_clear_after_alloc:
                ptr = lltype.malloc(rffi.CCHARP.TO, datasize,
                                    flavor='raw', zero=True)
            else:
                ptr = lltype.malloc(rffi.CCHARP.TO, datasize,
                                    flavor='raw', zero=False)
            return cdataobj.W_CDataNewStd(space, ptr, ctype, length)
        else:
            w_raw_cdata = space.call_function(self.w_alloc,
                                              space.wrap(datasize))
            if not isinstance(w_raw_cdata, cdataobj.W_CData):
                raise oefmt(ffi_obj.get_ffi_error(space),
                            "expected cdata object from the call to %R, "
                            "got '%T'", self.w_alloc, w_raw_cdata)
            if not isinstance(w_raw_cdata.ctype, ctypeptr.W_CTypePtrOrArray):
                raise oefmt(ffi_obj.get_ffi_error(space),
                            "expected cdata pointer from the call to %R, "
                            "got '%s'", self.w_alloc, w_raw_cdata.ctype.name)
            #
            ptr = w_raw_cdata.unsafe_escaping_ptr()
            if self.should_clear_after_alloc:
                rffi.c_memset(rffi.cast(rffi.VOIDP, ptr), 0,
                              rffi.cast(rffi.SIZE_T, datasize))
            #
            if self.w_free is None:
                # use this class which does not have a __del__, but still
                # keeps alive w_raw_cdata
                res = cdataobj.W_CDataNewNonStdNoFree(space, ptr, ctype, length)
            else:
                res = cdataobj.W_CDataNewNonStdFree(space, ptr, ctype, length)
                res.w_free = self.w_free
            res.w_raw_cdata = w_raw_cdata
            return res

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


def new_allocator(space, ffi, w_alloc, w_free, should_clear_after_alloc):
    if space.is_none(w_alloc):
        w_alloc = None
    if space.is_none(w_free):
        w_free = None
    if w_alloc is None and w_free is not None:
        raise oefmt(space.w_TypeError, "cannot pass 'free' without 'alloc'")
    alloc = W_Allocator(ffi, w_alloc, w_free, bool(should_clear_after_alloc))
    return space.wrap(alloc)


default_allocator = W_Allocator(None, None, None, should_clear_after_alloc=True)
nonzero_allocator = W_Allocator(None, None, None,should_clear_after_alloc=False)

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app

from pypy.module._cffi_backend.cdataobj import W_CData
from pypy.module._cffi_backend.ctypestruct import W_CTypeStructOrUnion
from pypy.module._cffi_backend.ctypefunc import W_CTypeFunc


class W_StructWrapper(W_Root):
    def __init__(self, w_cdata, locs, rawfunctype):
        self.w_cdata = w_cdata
        self.locs = locs
        self.rawfunctype = rawfunctype

    def typeof(self, ffi):
        return self.rawfunctype.unwrap_as_fnptr(ffi)

    def descr_call(self, args_w):
        ctype = self.w_cdata.ctype
        assert isinstance(ctype, W_CTypeFunc)
        args_w = args_w[:]
        for loc in self.locs:
            if loc >= len(args_w):
                continue    # the real call will complain
            w_arg = args_w[loc]
            if not isinstance(w_arg, W_CData):
                continue    # the real call will complain
            if not isinstance(w_arg.ctype, W_CTypeStructOrUnion):
                continue    # the real call will complain
            w_arg = W_CData(w_arg.space, w_arg.unsafe_escaping_ptr(),
                            ctype.fargs[loc])
            args_w[loc] = w_arg
        return self.w_cdata.call(args_w)


W_StructWrapper.typedef = TypeDef(
        'FFIStructWrapper',
        __call__ = interp2app(W_StructWrapper.descr_call),
        )
W_StructWrapper.typedef.acceptable_as_base_class = False

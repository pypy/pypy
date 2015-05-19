from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app
from rpython.rlib import jit

from pypy.module._cffi_backend.cdataobj import W_CData
from pypy.module._cffi_backend.cdataobj import W_CDataPtrToStructOrUnion
from pypy.module._cffi_backend.ctypeptr import W_CTypePtrOrArray
from pypy.module._cffi_backend.ctypefunc import W_CTypeFunc
from pypy.module._cffi_backend.ctypestruct import W_CTypeStructOrUnion


class W_StructWrapper(W_Root):
    """A wrapper around a real W_CData which points to a function
    generated in the C code.  The real W_CData has got no struct/union
    argument (only pointers to it), and no struct/union return type
    (it is replaced by a hidden pointer as first argument).  This
    wrapper is callable, and the arguments it expects and returns
    are directly the struct/union.  Calling ffi.typeof(wrapper)
    also returns the original struct/union signature.
    """
    _immutable_ = True

    def __init__(self, w_cdata, locs, rawfunctype):
        space = w_cdata.space
        ctype = w_cdata.ctype
        assert isinstance(ctype, W_CTypeFunc)
        assert len(ctype.fargs) == len(locs)
        #
        self.space = space
        self.w_cdata = w_cdata
        self.locs = locs
        self.fargs = ctype.fargs
        self.rawfunctype = rawfunctype

    def typeof(self, ffi):
        return self.rawfunctype.unwrap_as_fnptr(ffi)

    @jit.unroll_safe
    def _prepare(self, args_w, start_index):
        # replaces struct/union arguments with ptr-to-struct/union arguments
        space = self.space
        locs = self.locs
        result_w = args_w[:]
        for i in range(start_index, min(len(args_w), len(locs))):
            if locs[i] != 'A':
                continue
            w_arg = args_w[i]
            farg = self.fargs[i]      # <ptr to struct/union>
            assert isinstance(farg, W_CTypePtrOrArray)
            if isinstance(w_arg, W_CData) and w_arg.ctype is farg.ctitem:
                # fast way: we are given a W_CData "struct", so just make
                # a new W_CData "ptr-to-struct" which points to the same
                # raw memory.  We use unsafe_escaping_ptr(), so we have to
                # make sure the original 'w_arg' stays alive; the easiest
                # is to build an instance of W_CDataPtrToStructOrUnion.
                w_arg = W_CDataPtrToStructOrUnion(
                    space, w_arg.unsafe_escaping_ptr(), farg, w_arg)
            else:
                # slow way: build a new "ptr to struct" W_CData by calling
                # the equivalent of ffi.new()
                if space.is_w(w_arg, space.w_None):
                    continue
                w_arg = farg.newp(w_arg)
            result_w[i] = w_arg
        return result_w

    def descr_call(self, args_w):
        # If the result we want to present to the user is "returns struct",
        # then internally allocate the struct and pass a pointer to it as
        # a first argument.
        if self.locs[0] == 'R':
            w_result_cdata = self.fargs[0].newp(self.space.w_None)
            args_w = [w_result_cdata] + args_w
            self.w_cdata.call(self._prepare(args_w, 1))
            assert isinstance(w_result_cdata, W_CDataPtrToStructOrUnion)
            return w_result_cdata.structobj
        else:
            return self.w_cdata.call(self._prepare(args_w, 0))


W_StructWrapper.typedef = TypeDef(
        'FFIFuncStructWrapper',
        __call__ = interp2app(W_StructWrapper.descr_call),
        )
W_StructWrapper.typedef.acceptable_as_base_class = False

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import oefmt
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app
from rpython.rlib.objectmodel import keepalive_until_here

from pypy.module._cffi_backend.cdataobj import W_CData
from pypy.module._cffi_backend.cdataobj import W_CDataPtrToStructOrUnion
from pypy.module._cffi_backend.ctypestruct import W_CTypeStructOrUnion
from pypy.module._cffi_backend.ctypefunc import W_CTypeFunc


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
        ctype = w_cdata.ctype
        assert isinstance(ctype, W_CTypeFunc)
        self.ctype = ctype      # this type takes pointers
        self.w_cdata = w_cdata
        if locs[-1] == -1:      # return value is a struct/union
            locs = locs[:-1]
            self.ctresptrtype = ctype.fargs[0]
        else:
            self.ctresptrtype = None
        self.locs = locs
        self.rawfunctype = rawfunctype

    def typeof(self, ffi):
        return self.rawfunctype.unwrap_as_fnptr(ffi)

    def descr_call(self, args_w):
        space = self.w_cdata.space
        ctype = self.ctype
        shift = (self.ctresptrtype is not None)
        expected_num_args = len(ctype.fargs) - shift
        if len(args_w) != expected_num_args:
            raise oefmt(space.w_TypeError,
                        "'%s' expects %d arguments, got %d",
                        ctype.name, expected_num_args, len(args_w))

        # Fix the arguments that are so far "struct/union" and that need
        # to be "ptr to struct/union"
        original_args_w = args_w
        if len(self.locs) > 0:
            args_w = args_w[:]
            for loc in self.locs:
                w_arg = args_w[loc]
                if (not isinstance(w_arg, W_CData) or
                        not isinstance(w_arg.ctype, W_CTypeStructOrUnion)):
                    raise oefmt(space.w_TypeError,
                                "wrong type for argument %d", loc)
                w_arg = W_CData(space, w_arg.unsafe_escaping_ptr(),
                                self.ctype.fargs[loc + shift])
                args_w[loc] = w_arg

        # If the result we want to present to the user is "returns struct",
        # then internally allocate the struct and pass a pointer to it as
        # a first argument
        if self.ctresptrtype is not None:
            w_result_cdata = self.ctresptrtype.newp(space.w_None)
            self.w_cdata.call([w_result_cdata] + args_w)
            assert isinstance(w_result_cdata, W_CDataPtrToStructOrUnion)
            w_result = w_result_cdata.structobj
        else:
            w_result = self.w_cdata.call(args_w)
        keepalive_until_here(original_args_w)
        return w_result


W_StructWrapper.typedef = TypeDef(
        'FFIStructWrapper',
        __call__ = interp2app(W_StructWrapper.descr_call),
        )
W_StructWrapper.typedef.acceptable_as_base_class = False

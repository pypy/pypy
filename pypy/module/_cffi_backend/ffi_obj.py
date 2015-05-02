from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, unwrap_spec
from rpython.rlib import jit, rgc

from pypy.module._cffi_backend import parse_c_type, realize_c_type


ACCEPT_STRING   = 1
ACCEPT_CTYPE    = 2
ACCEPT_CDATA    = 4
ACCEPT_ALL      = ACCEPT_STRING | ACCEPT_CTYPE | ACCEPT_CDATA
CONSIDER_FN_AS_FNPTR  = 8


class W_FFIObject(W_Root):

    def __init__(self, space, src_ctx=parse_c_type.NULL_CTX):
        self.space = space
        self.types_dict = {}
        self.ctxobj = parse_c_type.allocate_ctxobj(src_ctx)
        if src_ctx:
            self.cached_types = [None] * parse_c_type.get_num_types(src_ctx)
        else:
            self.cached_types = None

    @rgc.must_be_light_finalizer
    def __del__(self):
        parse_c_type.free_ctxobj(self.ctxobj)

    @jit.elidable
    def parse_string_to_type(self, x):
        try:
            return self.types_dict[x]
        except KeyError:
            pass

        index = parse_c_type.parse_c_type(self.ctxobj.info, x)
        if index < 0:
            xxxx
        ct = realize_c_type.realize_c_type(self, self.ctxobj.info.c_output,
                                           index)
        self.types_dict[x] = ct
        return ct

    def ffi_type(self, w_x, accept):
        space = self.space
        if (accept & ACCEPT_STRING) and space.isinstance_w(w_x, space.w_str):
            return self.parse_string_to_type(space.str_w(w_x))
        yyyy

    def descr_new(self):
        XXX

    def descr_typeof(self, w_x):
        return self.ffi_type(w_x, ACCEPT_STRING | ACCEPT_CDATA)


#@unwrap_spec()
def W_FFIObject___new__(space, w_subtype):
    r = space.allocate_instance(W_FFIObject, w_subtype)
    r.__init__(space)
    return space.wrap(r)

W_FFIObject.typedef = TypeDef(
        'CompiledFFI',
        __new__ = interp2app(W_FFIObject___new__),
        new = interp2app(W_FFIObject.descr_new),
        typeof = interp2app(W_FFIObject.descr_typeof),
        )

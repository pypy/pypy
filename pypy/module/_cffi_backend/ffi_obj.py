from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from rpython.rlib import jit, rgc

from pypy.module._cffi_backend import parse_c_type, realize_c_type
from pypy.module._cffi_backend import newtype


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


    def descr_init(self):
        pass       # if any argument is passed, gets a TypeError

    @unwrap_spec(w_init=WrappedDefault(None))
    def descr_new(self, w_arg, w_init):
        """\
Allocate an instance according to the specified C type and return a
pointer to it.  The specified C type must be either a pointer or an
array: ``new('X *')`` allocates an X and returns a pointer to it,
whereas ``new('X[n]')`` allocates an array of n X'es and returns an
array referencing it (which works mostly like a pointer, like in C).
You can also use ``new('X[]', n)`` to allocate an array of a
non-constant length n.

The memory is initialized following the rules of declaring a global
variable in C: by default it is zero-initialized, but an explicit
initializer can be given which can be used to fill all or part of the
memory.

When the returned <cdata> object goes out of scope, the memory is
freed.  In other words the returned <cdata> object has ownership of
the value of type 'cdecl' that it points to.  This means that the raw
data can be used as long as this object is kept alive, but must not be
used for a longer time.  Be careful about that when copying the
pointer to the memory somewhere else, e.g. into another structure."""
        #
        w_ctype = self.ffi_type(w_arg, ACCEPT_STRING | ACCEPT_CTYPE)
        return w_ctype.newp(w_init)


    def descr_typeof(self, w_arg):
        """\
Parse the C type given as a string and return the
corresponding <ctype> object.
It can also be used on 'cdata' instance to get its C type."""
        #
        return self.ffi_type(w_arg, ACCEPT_STRING | ACCEPT_CDATA)


def W_FFIObject___new__(space, w_subtype, __args__):
    r = space.allocate_instance(W_FFIObject, w_subtype)
    r.__init__(space)
    return space.wrap(r)

W_FFIObject.typedef = TypeDef(
        'CompiledFFI',
        __new__ = interp2app(W_FFIObject___new__),
        __init__ = interp2app(W_FFIObject.descr_init),
        new = interp2app(W_FFIObject.descr_new),
        typeof = interp2app(W_FFIObject.descr_typeof),
        )

def _startup(space):
    ctvoidp = newtype.new_pointer_type(space, newtype.new_void_type(space))
    w_NULL = ctvoidp.cast(space.wrap(0))
    w_ffitype = space.gettypefor(W_FFIObject)
    w_ffitype.dict_w['NULL'] = w_NULL

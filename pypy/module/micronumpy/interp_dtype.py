from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from pypy.objspace.std.floatobject import float2string
from pypy.rlib.rfloat import DTSF_STR_PRECISION
from pypy.rlib.unroll import unrolling_iterable
from pypy.rpython.lltypesystem import lltype, llmemory, rffi

SIGNEDLTR = "i"

class W_Dtype(Wrappable):
    aliases = []
    applevel_types = []

    def __init__(self, space):
        pass

    def descr__new__(space, w_subtype, w_dtype):
        if space.isinstance_w(w_dtype, space.w_str):
            dtype = space.str_w(w_dtype)
            for alias, dtype_class in dtypes_by_alias:
                if alias == dtype:
                    return space.fromcache(dtype_class)
        elif isinstance(space.interpclass_w(w_dtype), W_Dtype):
            return w_dtype
        elif space.isinstance_w(w_dtype, space.w_type):
            for typename, dtype_class in dtypes_by_apptype:
                if space.is_w(getattr(space, "w_%s" % typename), w_dtype):
                    return space.fromcache(dtype_class)
        assert False

    def descr_repr(self, space):
        return space.wrap("dtype('%s')" % self.name)

    def descr_str(self, space):
        return space.wrap(self.name)

class LowLevelDtype(object):
    _mixin_ = True

    def erase(self, storage):
        return rffi.cast(VOID_TP, storage)

    def unerase(self, storage):
        return rffi.cast(self.TP, storage)

    def unwrap(self, space, w_item):
        raise NotImplementedError

    def malloc(self, size):
        # XXX find out why test_zjit explodes with tracking of allocations
        return self.erase(lltype.malloc(self.TP.TO, size,
            zero=True, flavor="raw",
            track_allocation=False, add_memory_pressure=True
        ))

    def getitem(self, storage, i):
        return self.unerase(storage)[i]

    def setitem(self, storage, i, item):
        self.unerase(storage)[i] = item

    def setitem_w(self, space, storage, i, w_item):
        self.setitem(storage, i, self.unwrap(space, w_item))

    def str_format(self, item):
        return str(item)

def make_array_ptr(T):
    return lltype.Ptr(lltype.Array(T, hints={"nolength": True}))

VOID_TP = make_array_ptr(lltype.Void)

class W_BoolDtype(LowLevelDtype, W_Dtype):
    num = 0
    name = "bool"
    aliases = ["?"]
    applevel_types = ["bool"]
    TP = make_array_ptr(lltype.Bool)

    def unwrap(self, space, w_item):
        return space.is_true(w_item)

class W_Int8Dtype(LowLevelDtype, W_Dtype):
    num = 1
    kind = SIGNEDLTR
    aliases = ["int8"]
    TP = make_array_ptr(rffi.SIGNEDCHAR)

class W_Int32Dtype(LowLevelDtype, W_Dtype):
    num = 5
    kind = SIGNEDLTR
    aliases = ["i"]
    TP = make_array_ptr(rffi.INT)

class W_LongDtype(LowLevelDtype, W_Dtype):
    num = 7
    kind = SIGNEDLTR
    aliases = ["l"]
    applevel_types = ["int"]
    TP = make_array_ptr(rffi.LONG)

    def unwrap(self, space, w_item):
        return space.int_w(space.int(w_item))

class W_Int64Dtype(LowLevelDtype, W_Dtype):
    num = 9
    applevel_types = ["long"]
    TP = make_array_ptr(rffi.LONGLONG)

class W_Float64Dtype(LowLevelDtype, W_Dtype):
    num = 12
    applevel_types = ["float"]
    TP = make_array_ptr(lltype.Float)

    def unwrap(self, space, w_item):
        return space.float_w(space.float(w_item))

    def str_format(self, item):
        return float2string(item, 'g', DTSF_STR_PRECISION)


ALL_DTYPES = [
    W_BoolDtype, W_Int8Dtype, W_Int32Dtype, W_LongDtype, W_Int64Dtype, W_Float64Dtype
]

dtypes_by_alias = unrolling_iterable([
    (alias, dtype)
    for dtype in ALL_DTYPES
    for alias in dtype.aliases
])
dtypes_by_apptype = unrolling_iterable([
    (apptype, dtype)
    for dtype in ALL_DTYPES
    for apptype in dtype.applevel_types
])

W_Dtype.typedef = TypeDef("dtype",
    __new__ = interp2app(W_Dtype.descr__new__.im_func),

    __repr__ = interp2app(W_Dtype.descr_repr),
    __str__ = interp2app(W_Dtype.descr_str),

    num = interp_attrproperty("num", cls=W_Dtype),
    kind = interp_attrproperty("kind", cls=W_Dtype),
)
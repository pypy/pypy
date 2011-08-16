import functools
import math

from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from pypy.objspace.std.floatobject import float2string
from pypy.rlib import rfloat
from pypy.rlib.objectmodel import specialize
from pypy.rlib.unroll import unrolling_iterable
from pypy.rpython.lltypesystem import lltype, llmemory, rffi


SIGNEDLTR = "i"
BOOLLTR = "b"
FLOATINGLTR = "f"

class W_Dtype(Wrappable):
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


class BaseBox(object):
    pass

VOID_TP = lltype.Ptr(lltype.Array(lltype.Void, hints={'nolength': True}))

def create_low_level_dtype(num, kind, name, aliases, applevel_types, T, valtype):
    class Box(BaseBox):
        def __init__(self, val):
            assert isinstance(val, valtype)
            self.val = val

        def wrap(self, space):
            return space.wrap(self.val)

        def convert_to(self, dtype):
            return dtype.adapt_val(self.val)
    Box.__name__ = "%sBox" % T._name

    TP = lltype.Ptr(lltype.Array(T, hints={'nolength': True}))
    class W_LowLevelDtype(W_Dtype):
        def erase(self, storage):
            return rffi.cast(VOID_TP, storage)

        def unerase(self, storage):
            return rffi.cast(TP, storage)

        @specialize.argtype(1)
        def box(self, value):
            return Box(value)

        def unwrap(self, space, w_item):
            raise NotImplementedError

        def malloc(self, size):
            # XXX find out why test_zjit explodes with tracking of allocations
            return self.erase(lltype.malloc(TP.TO, size,
                zero=True, flavor="raw",
                track_allocation=False, add_memory_pressure=True
            ))

        def getitem(self, storage, i):
            return Box(self.unerase(storage)[i])

        def setitem(self, storage, i, item):
            assert isinstance(item, Box)
            self.unerase(storage)[i] = item.val

        def setitem_w(self, space, storage, i, w_item):
            self.setitem(storage, i, self.unwrap(space, w_item))

        @specialize.argtype(1)
        def adapt_val(self, val):
            return Box(rffi.cast(TP.TO.OF, val))

        def str_format(self, item):
            assert isinstance(item, Box)
            return str(item.val)

        # Operations.
        def binop(func):
            @functools.wraps(func)
            def impl(self, v1, v2):
                assert isinstance(v1, Box)
                assert isinstance(v2, Box)
                return Box(func(self, v1.val, v2.val))
            return impl
        def unaryop(func):
            @functools.wraps(func)
            def impl(self, v):
                assert isinstance(v, Box)
                return Box(func(self, v.val))
            return impl

        @binop
        def add(self, v1, v2):
            return v1 + v2
        @binop
        def sub(self, v1, v2):
            return v1 - v2
        @binop
        def mul(self, v1, v2):
            return v1 * v2
        @binop
        def div(self, v1, v2):
            return v1 / v2
        @binop
        def mod(self, v1, v2):
            return math.fmod(v1, v2)
        @binop
        def pow(self, v1, v2):
            return math.pow(v1, v2)
        @binop
        def max(self, v1, v2):
            return max(v1, v2)
        @binop
        def min(self, v1, v2):
            return min(v1, v2)
        @binop
        def copysign(self, v1, v2):
            return math.copysign(v1, v2)
        @unaryop
        def neg(self, v):
            return -v
        @unaryop
        def pos(self, v):
            return v
        @unaryop
        def abs(self, v):
            return abs(v)
        @unaryop
        def sign(self, v):
            if v == 0.0:
                return 0.0
            return rfloat.copysign(1.0, v)
        @unaryop
        def fabs(self, v):
            return math.fabs(v)
        @unaryop
        def reciprocal(self, v):
            if v == 0.0:
                return rfloat.copysign(rfloat.INFINITY, v)
            return 1.0 / v
        @unaryop
        def floor(self, v):
            return math.floor(v)
        @unaryop
        def exp(self, v):
            try:
                return math.exp(v)
            except OverflowError:
                return rfloat.INFINITY
        @unaryop
        def sin(self, v):
            return math.sin(v)
        @unaryop
        def cos(self, v):
            return math.cos(v)
        @unaryop
        def tan(self, v):
            return math.tan(v)
        @unaryop
        def arcsin(self, v):
            if v < -1.0 or  v > 1.0:
                return rfloat.NAN
            return math.asin(v)
        @unaryop
        def arccos(self, v):
            if v < -1.0 or v > 1.0:
                return rfloat.NAN
            return math.acos(v)
        @unaryop
        def arctan(self, v):
            return math.atan(v)

        # Comparisons, they return unwraped results (for now)
        def ne(self, v1, v2):
            assert isinstance(v1, Box)
            assert isinstance(v2, Box)
            return v1.val != v2.val
        def bool(self, v):
            assert isinstance(v, Box)
            return bool(v.val)

    W_LowLevelDtype.__name__ = "W_%sDtype" % name.capitalize()
    W_LowLevelDtype.num = num
    W_LowLevelDtype.kind = kind
    W_LowLevelDtype.name = name
    W_LowLevelDtype.aliases = aliases
    W_LowLevelDtype.applevel_types = applevel_types
    return W_LowLevelDtype


W_BoolDtype = create_low_level_dtype(
    num = 0, kind = BOOLLTR, name = "bool",
    aliases = ["?"],
    applevel_types = ["bool"],
    T = lltype.Bool,
    valtype = bool,
)
class W_BoolDtype(W_BoolDtype):
    def unwrap(self, space, w_item):
        return self.box(space.is_true(w_item))

W_Int8Dtype = create_low_level_dtype(
    num = 1, kind = SIGNEDLTR, name = "int8",
    aliases = ["int8"],
    applevel_types = [],
    T = rffi.SIGNEDCHAR,
    valtype = rffi.SIGNEDCHAR._type,
)
W_Int32Dtype = create_low_level_dtype(
    num = 5, kind = SIGNEDLTR, name = "int32",
    aliases = ["i"],
    applevel_types = [],
    T = rffi.INT,
    valtype = rffi.INT._type,
)
W_LongDtype = create_low_level_dtype(
    num = 7, kind = SIGNEDLTR, name = "???",
    aliases = ["l"],
    applevel_types = ["int"],
    T = rffi.LONG,
    valtype = int,
)
class W_LongDtype(W_LongDtype):
    def unwrap(self, space, w_item):
        return self.box(space.int_w(space.int(w_item)))

W_Int64Dtype = create_low_level_dtype(
    num = 9, kind = SIGNEDLTR, name = "int64",
    aliases = [],
    applevel_types = ["long"],
    T = rffi.LONGLONG,
    valtype = int,
)
W_Float64Dtype = create_low_level_dtype(
    num = 12, kind = FLOATINGLTR, name = "float64",
    aliases = [],
    applevel_types = ["float"],
    T = lltype.Float,
    valtype = float,
)
class W_Float64Dtype(W_Float64Dtype):
    def unwrap(self, space, w_item):
        return self.box(space.float_w(space.float(w_item)))

    def str_format(self, item):
        return float2string(item.val, 'g', rfloat.DTSF_STR_PRECISION)


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
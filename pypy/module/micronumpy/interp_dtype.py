import functools
import math

from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, interp_attrproperty, GetSetProperty
from pypy.module.micronumpy import signature
from pypy.objspace.std.floatobject import float2string
from pypy.rlib import rarithmetic, rfloat
from pypy.rlib.rarithmetic import LONG_BIT, widen
from pypy.rlib.objectmodel import specialize, enforceargs
from pypy.rlib.unroll import unrolling_iterable
from pypy.rpython.lltypesystem import lltype, rffi


UNSIGNEDLTR = "u"
SIGNEDLTR = "i"
BOOLLTR = "b"
FLOATINGLTR = "f"

class W_Dtype(Wrappable):
    def __init__(self, space):
        pass

    def descr__new__(space, w_subtype, w_dtype):
        if space.is_w(w_dtype, space.w_None):
            return space.fromcache(W_Float64Dtype)
        elif space.isinstance_w(w_dtype, space.w_str):
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
        raise OperationError(space.w_TypeError, space.wrap("data type not understood"))

    def descr_repr(self, space):
        return space.wrap("dtype('%s')" % self.name)

    def descr_str(self, space):
        return space.wrap(self.name)

    def descr_get_shape(self, space):
        return space.newtuple([])


class BaseBox(object):
    pass

VOID_TP = lltype.Ptr(lltype.Array(lltype.Void, hints={'nolength': True, "uncast_on_llgraph": True}))

def create_low_level_dtype(num, kind, name, aliases, applevel_types, T, valtype,
    expected_size=None):

    class Box(BaseBox):
        def __init__(self, val):
            self.val = val

        def wrap(self, space):
            val = self.val
            if valtype is rarithmetic.r_singlefloat:
                val = float(val)
            return space.wrap(val)

        def convert_to(self, dtype):
            return dtype.adapt_val(self.val)
    Box.__name__ = "%sBox" % T._name

    TP = lltype.Ptr(lltype.Array(T, hints={'nolength': True}))
    class W_LowLevelDtype(W_Dtype):
        signature = signature.BaseSignature()

        def erase(self, storage):
            return rffi.cast(VOID_TP, storage)

        def unerase(self, storage):
            return rffi.cast(TP, storage)

        @enforceargs(None, valtype)
        def box(self, value):
            return Box(value)

        def unbox(self, box):
            assert isinstance(box, Box)
            return box.val

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
            self.unerase(storage)[i] = self.unbox(item)

        def setitem_w(self, space, storage, i, w_item):
            self.setitem(storage, i, self.unwrap(space, w_item))

        def fill(self, storage, item, start, stop):
            storage = self.unerase(storage)
            item = self.unbox(item)
            for i in xrange(start, stop):
                storage[i] = item

        @specialize.argtype(1)
        def adapt_val(self, val):
            return self.box(rffi.cast(TP.TO.OF, val))

    W_LowLevelDtype.__name__ = "W_%sDtype" % name.capitalize()
    W_LowLevelDtype.num = num
    W_LowLevelDtype.kind = kind
    W_LowLevelDtype.name = name
    W_LowLevelDtype.aliases = aliases
    W_LowLevelDtype.applevel_types = applevel_types
    W_LowLevelDtype.num_bytes = rffi.sizeof(T)
    if expected_size is not None:
        assert W_LowLevelDtype.num_bytes == expected_size
    return W_LowLevelDtype


def binop(func):
    @functools.wraps(func)
    def impl(self, v1, v2):
        return self.adapt_val(func(self,
            self.for_computation(self.unbox(v1)),
            self.for_computation(self.unbox(v2)),
        ))
    return impl

def raw_binop(func):
    # Returns the result unwrapped.
    @functools.wraps(func)
    def impl(self, v1, v2):
        return func(self,
            self.for_computation(self.unbox(v1)),
            self.for_computation(self.unbox(v2))
        )
    return impl

def unaryop(func):
    @functools.wraps(func)
    def impl(self, v):
        return self.adapt_val(func(self, self.for_computation(self.unbox(v))))
    return impl

class ArithmeticTypeMixin(object):
    _mixin_ = True

    @binop
    def add(self, v1, v2):
        return v1 + v2
    @binop
    def sub(self, v1, v2):
        return v1 - v2
    @binop
    def mul(self, v1, v2):
        return v1 * v2

    @unaryop
    def pos(self, v):
        return +v
    @unaryop
    def neg(self, v):
        return -v
    @unaryop
    def abs(self, v):
        return abs(v)

    @binop
    def max(self, v1, v2):
        return max(v1, v2)
    @binop
    def min(self, v1, v2):
        return min(v1, v2)

    def bool(self, v):
        return bool(self.for_computation(self.unbox(v)))
    @raw_binop
    def eq(self, v1, v2):
        return v1 == v2
    @raw_binop
    def ne(self, v1, v2):
        return v1 != v2
    @raw_binop
    def lt(self, v1, v2):
        return v1 < v2
    @raw_binop
    def le(self, v1, v2):
        return v1 <= v2
    @raw_binop
    def gt(self, v1, v2):
        return v1 > v2
    @raw_binop
    def ge(self, v1, v2):
        return v1 >= v2


class FloatArithmeticDtype(ArithmeticTypeMixin):
    _mixin_ = True

    def unwrap(self, space, w_item):
        return self.adapt_val(space.float_w(space.float(w_item)))

    def for_computation(self, v):
        return float(v)

    def str_format(self, item):
        return float2string(self.for_computation(self.unbox(item)), 'g', rfloat.DTSF_STR_PRECISION)

    @binop
    def div(self, v1, v2):
        try:
            return v1 / v2
        except ZeroDivisionError:
            if v1 == v2 == 0.0:
                return rfloat.NAN
            return rfloat.copysign(rfloat.INFINITY, v1 * v2)
    @binop
    def mod(self, v1, v2):
        return math.fmod(v1, v2)
    @binop
    def pow(self, v1, v2):
        return math.pow(v1, v2)

    @unaryop
    def sign(self, v):
        if v == 0.0:
            return 0.0
        return rfloat.copysign(1.0, v)
    @unaryop
    def reciprocal(self, v):
        if v == 0.0:
            return rfloat.copysign(rfloat.INFINITY, v)
        return 1.0 / v
    @unaryop
    def fabs(self, v):
        return math.fabs(v)
    @unaryop
    def floor(self, v):
        return math.floor(v)

    @binop
    def copysign(self, v1, v2):
        return math.copysign(v1, v2)
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
        if not -1.0 <= v <= 1.0:
            return rfloat.NAN
        return math.asin(v)
    @unaryop
    def arccos(self, v):
        if not -1.0 <= v <= 1.0:
            return rfloat.NAN
        return math.acos(v)
    @unaryop
    def arctan(self, v):
        return math.atan(v)
    @unaryop
    def arcsinh(self, v):
        return math.asinh(v)
    @unaryop
    def arctanh(self, v):
        if v == 1.0 or v == -1.0:
            return math.copysign(rfloat.INFINITY, v)
        if not -1.0 < v < 1.0:
            return rfloat.NAN
        return math.atanh(v)

class IntegerArithmeticDtype(ArithmeticTypeMixin):
    _mixin_ = True

    def unwrap(self, space, w_item):
        return self.adapt_val(space.int_w(space.int(w_item)))

    def for_computation(self, v):
        return widen(v)

    def str_format(self, item):
        return str(widen(self.unbox(item)))

    @binop
    def div(self, v1, v2):
        if v2 == 0:
            return 0
        return v1 / v2
    @binop
    def mod(self, v1, v2):
        return v1 % v2

class SignedIntegerArithmeticDtype(IntegerArithmeticDtype):
    _mixin_ = True

    @unaryop
    def sign(self, v):
        if v > 0:
            return 1
        elif v < 0:
            return -1
        else:
            assert v == 0
            return 0

class UnsignedIntegerArithmeticDtype(IntegerArithmeticDtype):
    _mixin_ = True

    @unaryop
    def sign(self, v):
        return int(v != 0)


W_BoolDtype = create_low_level_dtype(
    num = 0, kind = BOOLLTR, name = "bool",
    aliases = ["?", "bool", "bool8"],
    applevel_types = ["bool"],
    T = lltype.Bool,
    valtype = bool,
)
class W_BoolDtype(SignedIntegerArithmeticDtype, W_BoolDtype):
    def unwrap(self, space, w_item):
        return self.adapt_val(space.is_true(w_item))

    def str_format(self, item):
        v = self.unbox(item)
        return "True" if v else "False"

    def for_computation(self, v):
        return int(v)

W_Int8Dtype = create_low_level_dtype(
    num = 1, kind = SIGNEDLTR, name = "int8",
    aliases = ["b", "int8", "i1"],
    applevel_types = [],
    T = rffi.SIGNEDCHAR,
    valtype = rffi.SIGNEDCHAR._type,
    expected_size = 1,
)
class W_Int8Dtype(SignedIntegerArithmeticDtype, W_Int8Dtype):
    pass

W_UInt8Dtype = create_low_level_dtype(
    num = 2, kind = UNSIGNEDLTR, name = "uint8",
    aliases = ["B", "uint8", "I1"],
    applevel_types = [],
    T = rffi.UCHAR,
    valtype = rffi.UCHAR._type,
    expected_size = 1,
)
class W_UInt8Dtype(UnsignedIntegerArithmeticDtype, W_UInt8Dtype):
    pass

W_Int16Dtype = create_low_level_dtype(
    num = 3, kind = SIGNEDLTR, name = "int16",
    aliases = ["h", "int16", "i2"],
    applevel_types = [],
    T = rffi.SHORT,
    valtype = rffi.SHORT._type,
    expected_size = 2,
)
class W_Int16Dtype(SignedIntegerArithmeticDtype, W_Int16Dtype):
    pass

W_UInt16Dtype = create_low_level_dtype(
    num = 4, kind = UNSIGNEDLTR, name = "uint16",
    aliases = ["H", "uint16", "I2"],
    applevel_types = [],
    T = rffi.USHORT,
    valtype = rffi.USHORT._type,
    expected_size = 2,
)
class W_UInt16Dtype(UnsignedIntegerArithmeticDtype, W_UInt16Dtype):
    pass

W_Int32Dtype = create_low_level_dtype(
    num = 5, kind = SIGNEDLTR, name = "int32",
    aliases = ["i", "int32", "i4"],
    applevel_types = [],
    T = rffi.INT,
    valtype = rffi.INT._type,
    expected_size = 4,
)
class W_Int32Dtype(SignedIntegerArithmeticDtype, W_Int32Dtype):
    pass

W_UInt32Dtype = create_low_level_dtype(
    num = 6, kind = UNSIGNEDLTR, name = "uint32",
    aliases = ["I", "uint32", "I4"],
    applevel_types = [],
    T = rffi.UINT,
    valtype = rffi.UINT._type,
    expected_size = 4,
)
class W_UInt32Dtype(UnsignedIntegerArithmeticDtype, W_UInt32Dtype):
    pass

W_Int64Dtype = create_low_level_dtype(
    num = 9, kind = SIGNEDLTR, name = "int64",
    aliases = ["q", "int64", "i8"],
    applevel_types = ["long"],
    T = rffi.LONGLONG,
    valtype = rffi.LONGLONG._type,
    expected_size = 8,
)
class W_Int64Dtype(SignedIntegerArithmeticDtype, W_Int64Dtype):
    pass

W_UInt64Dtype = create_low_level_dtype(
    num = 10, kind = UNSIGNEDLTR, name = "uint64",
    aliases = ["Q", "uint64", "I8"],
    applevel_types = [],
    T = rffi.ULONGLONG,
    valtype = rffi.ULONGLONG._type,
    expected_size = 8,
)
class W_UInt64Dtype(UnsignedIntegerArithmeticDtype, W_UInt64Dtype):
    pass

if LONG_BIT == 32:
    long_dtype = W_Int32Dtype
    ulong_dtype = W_UInt32Dtype
elif LONG_BIT == 64:
    long_dtype = W_Int64Dtype
    ulong_dtype = W_UInt64Dtype
else:
    assert False

class W_LongDtype(long_dtype):
    num = 7
    aliases = ["l"]
    applevel_types = ["int"]

class W_ULongDtype(ulong_dtype):
    num = 8
    aliases = ["L"]

W_Float32Dtype = create_low_level_dtype(
    num = 11, kind = FLOATINGLTR, name = "float32",
    aliases = ["f", "float32", "f4"],
    applevel_types = [],
    T = lltype.SingleFloat,
    valtype = rarithmetic.r_singlefloat,
    expected_size = 4,
)
class W_Float32Dtype(FloatArithmeticDtype, W_Float32Dtype):
    pass

W_Float64Dtype = create_low_level_dtype(
    num = 12, kind = FLOATINGLTR, name = "float64",
    aliases = ["d", "float64", "f8"],
    applevel_types = ["float"],
    T = lltype.Float,
    valtype = float,
    expected_size = 8,
)
class W_Float64Dtype(FloatArithmeticDtype, W_Float64Dtype):
    pass

ALL_DTYPES = [
    W_BoolDtype,
    W_Int8Dtype, W_UInt8Dtype, W_Int16Dtype, W_UInt16Dtype,
    W_Int32Dtype, W_UInt32Dtype, W_LongDtype, W_ULongDtype,
    W_Int64Dtype, W_UInt64Dtype,
    W_Float32Dtype, W_Float64Dtype,
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
dtypes_by_num_bytes = unrolling_iterable(sorted([
    (dtype.num_bytes, dtype)
    for dtype in ALL_DTYPES
]))

W_Dtype.typedef = TypeDef("dtype",
    __module__ = "numpy",
    __new__ = interp2app(W_Dtype.descr__new__.im_func),

    __repr__ = interp2app(W_Dtype.descr_repr),
    __str__ = interp2app(W_Dtype.descr_str),

    num = interp_attrproperty("num", cls=W_Dtype),
    kind = interp_attrproperty("kind", cls=W_Dtype),
    itemsize = interp_attrproperty("num_bytes", cls=W_Dtype),
    shape = GetSetProperty(W_Dtype.descr_get_shape),
)
W_Dtype.typedef.acceptable_as_base_class = False

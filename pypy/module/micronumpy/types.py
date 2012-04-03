import functools
import math
import struct

from pypy.interpreter.error import OperationError
from pypy.module.micronumpy import interp_boxes
from pypy.objspace.std.floatobject import float2string
from pypy.rlib import rfloat, libffi, clibffi
from pypy.rlib.objectmodel import specialize, we_are_translated
from pypy.rlib.rarithmetic import widen, byteswap
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rstruct.runpack import runpack
from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib import jit

VOID_STORAGE = lltype.Array(lltype.Char, hints={'nolength': True,
                                                'render_as_void': True})
degToRad = math.pi / 180.0
log2 = math.log(2)

def simple_unary_op(func):
    specialize.argtype(1)(func)
    @functools.wraps(func)
    def dispatcher(self, v):
        return self.box(
            func(
                self,
                self.for_computation(self.unbox(v))
            )
        )
    return dispatcher

def raw_unary_op(func):
    specialize.argtype(1)(func)
    @functools.wraps(func)
    def dispatcher(self, v):
        return func(
            self,
            self.for_computation(self.unbox(v))
        )
    return dispatcher

def simple_binary_op(func):
    specialize.argtype(1, 2)(func)
    @functools.wraps(func)
    def dispatcher(self, v1, v2):
        return self.box(
            func(
                self,
                self.for_computation(self.unbox(v1)),
                self.for_computation(self.unbox(v2)),
            )
        )
    return dispatcher

def raw_binary_op(func):
    specialize.argtype(1, 2)(func)
    @functools.wraps(func)
    def dispatcher(self, v1, v2):
        return func(self,
            self.for_computation(self.unbox(v1)),
            self.for_computation(self.unbox(v2))
        )
    return dispatcher

class BaseType(object):
    _attrs_ = ()
    
    def _unimplemented_ufunc(self, *args):
        raise NotImplementedError

    def malloc(self, size):
        # XXX find out why test_zjit explodes with tracking of allocations
        return lltype.malloc(VOID_STORAGE, size,
                             zero=True, flavor="raw",
                             track_allocation=False, add_memory_pressure=True)

    def __repr__(self):
        return self.__class__.__name__

class Primitive(object):
    _mixin_ = True

    def get_element_size(self):
        return rffi.sizeof(self.T)

    @specialize.argtype(1)
    def box(self, value):
        return self.BoxType(rffi.cast(self.T, value))

    def unbox(self, box):
        assert isinstance(box, self.BoxType)
        return box.value

    def coerce(self, space, dtype, w_item):
        if isinstance(w_item, self.BoxType):
            return w_item
        return self.coerce_subtype(space, space.gettypefor(self.BoxType), w_item)

    def coerce_subtype(self, space, w_subtype, w_item):
        # XXX: ugly
        w_obj = space.allocate_instance(self.BoxType, w_subtype)
        assert isinstance(w_obj, self.BoxType)
        w_obj.__init__(self._coerce(space, w_item).value)
        return w_obj

    def to_builtin_type(self, space, box):
        return space.wrap(self.for_computation(self.unbox(box)))

    def _coerce(self, space, w_item):
        raise NotImplementedError

    def default_fromstring(self, space):
        raise NotImplementedError

    def _read(self, storage, width, i, offset):
        if we_are_translated():
            return libffi.array_getitem(clibffi.cast_type_to_ffitype(self.T),
                                        width, storage, i, offset)
        else:
            return libffi.array_getitem_T(self.T, width, storage, i, offset)

    def read(self, arr, width, i, offset, dtype=None):
        return self.box(self._read(arr.storage, width, i, offset))

    def read_bool(self, arr, width, i, offset):
        return bool(self.for_computation(self._read(arr.storage, width, i, offset)))

    def _write(self, storage, width, i, offset, value):
        if we_are_translated():
            libffi.array_setitem(clibffi.cast_type_to_ffitype(self.T),
                                 width, storage, i, offset, value)
        else:
            libffi.array_setitem_T(self.T, width, storage, i, offset, value)
        

    def store(self, arr, width, i, offset, box):
        self._write(arr.storage, width, i, offset, self.unbox(box))

    def fill(self, storage, width, box, start, stop, offset):
        value = self.unbox(box)
        for i in xrange(start, stop, width):
            self._write(storage, 1, i, offset, value)

    def runpack_str(self, s):
        return self.box(runpack(self.format_code, s))

    def pack_str(self, box):
        return struct.pack(self.format_code, self.unbox(box))

    @simple_binary_op
    def add(self, v1, v2):
        return v1 + v2

    @simple_binary_op
    def sub(self, v1, v2):
        return v1 - v2

    @simple_binary_op
    def mul(self, v1, v2):
        return v1 * v2

    @simple_unary_op
    def pos(self, v):
        return +v

    @simple_unary_op
    def neg(self, v):
        return -v

    @simple_unary_op
    def abs(self, v):
        return abs(v)

    @raw_unary_op
    def isnan(self, v):
        return False

    @raw_unary_op
    def isinf(self, v):
        return False

    @raw_unary_op
    def isneginf(self, v):
        return False

    @raw_unary_op
    def isposinf(self, v):
        return False

    @raw_binary_op
    def eq(self, v1, v2):
        return v1 == v2

    @raw_binary_op
    def ne(self, v1, v2):
        return v1 != v2

    @raw_binary_op
    def lt(self, v1, v2):
        return v1 < v2

    @raw_binary_op
    def le(self, v1, v2):
        return v1 <= v2

    @raw_binary_op
    def gt(self, v1, v2):
        return v1 > v2

    @raw_binary_op
    def ge(self, v1, v2):
        return v1 >= v2

    @raw_binary_op
    def logical_and(self, v1, v2):
        return bool(v1) and bool(v2)

    @raw_binary_op
    def logical_or(self, v1, v2):
        return bool(v1) or bool(v2)

    @raw_unary_op
    def logical_not(self, v):
        return not bool(v)

    @raw_binary_op
    def logical_xor(self, v1, v2):
        return bool(v1) ^ bool(v2)

    def bool(self, v):
        return bool(self.for_computation(self.unbox(v)))

    @simple_binary_op
    def max(self, v1, v2):
        return max(v1, v2)

    @simple_binary_op
    def min(self, v1, v2):
        return min(v1, v2)

class NonNativePrimitive(Primitive):
    _mixin_ = True
    
    def _read(self, storage, width, i, offset):
        if we_are_translated():
            res = libffi.array_getitem(clibffi.cast_type_to_ffitype(self.T),
                                        width, storage, i, offset)
        else:
            res = libffi.array_getitem_T(self.T, width, storage, i, offset)
        return byteswap(res)

    def _write(self, storage, width, i, offset, value):
        value = byteswap(value)
        if we_are_translated():
            libffi.array_setitem(clibffi.cast_type_to_ffitype(self.T),
                                 width, storage, i, offset, value)
        else:
            libffi.array_setitem_T(self.T, width, storage, i, offset, value)

    def pack_str(self, box):
        return struct.pack(self.format_code, byteswap(self.unbox(box)))

class Bool(BaseType, Primitive):
    _attrs_ = ()

    T = lltype.Bool
    BoxType = interp_boxes.W_BoolBox
    format_code = "?"

    True = BoxType(True)
    False = BoxType(False)

    @specialize.argtype(1)
    def box(self, value):
        box = Primitive.box(self, value)
        if box.value:
            return self.True
        else:
            return self.False

    def coerce_subtype(self, space, w_subtype, w_item):
        # Doesn't return subclasses so it can return the constants.
        return self._coerce(space, w_item)

    def _coerce(self, space, w_item):
        return self.box(space.is_true(w_item))

    def to_builtin_type(self, space, w_item):
        return space.wrap(self.unbox(w_item))

    def str_format(self, box):
        return "True" if self.unbox(box) else "False"

    def for_computation(self, v):
        return int(v)

    def default_fromstring(self, space):
        return self.box(False)

    @simple_binary_op
    def bitwise_and(self, v1, v2):
        return v1 & v2

    @simple_binary_op
    def bitwise_or(self, v1, v2):
        return v1 | v2

    @simple_binary_op
    def bitwise_xor(self, v1, v2):
        return v1 ^ v2

    @simple_unary_op
    def invert(self, v):
        return ~v

NonNativeBool = Bool

class Integer(Primitive):
    _mixin_ = True

    def _base_coerce(self, space, w_item):
        return self.box(space.int_w(space.call_function(space.w_int, w_item)))
    def _coerce(self, space, w_item):
        return self._base_coerce(space, w_item)

    def str_format(self, box):
        return str(self.for_computation(self.unbox(box)))

    def for_computation(self, v):
        return widen(v)

    def default_fromstring(self, space):
        return self.box(0)

    @simple_binary_op
    def div(self, v1, v2):
        if v2 == 0:
            return 0
        return v1 / v2

    @simple_binary_op
    def floordiv(self, v1, v2):
        if v2 == 0:
            return 0
        return v1 // v2

    @simple_binary_op
    def mod(self, v1, v2):
        return v1 % v2

    @simple_binary_op
    def pow(self, v1, v2):
        if v2 < 0:
            return 0
        res = 1
        while v2 > 0:
            if v2 & 1:
                res *= v1
            v2 >>= 1
            if v2 == 0:
                break
            v1 *= v1
        return res

    @simple_binary_op
    def lshift(self, v1, v2):
        return v1 << v2

    @simple_binary_op
    def rshift(self, v1, v2):
        return v1 >> v2

    @simple_unary_op
    def sign(self, v):
        if v > 0:
            return 1
        elif v < 0:
            return -1
        else:
            assert v == 0
            return 0

    @simple_binary_op
    def bitwise_and(self, v1, v2):
        return v1 & v2

    @simple_binary_op
    def bitwise_or(self, v1, v2):
        return v1 | v2

    @simple_binary_op
    def bitwise_xor(self, v1, v2):
        return v1 ^ v2

    @simple_unary_op
    def invert(self, v):
        return ~v

class NonNativeInteger(NonNativePrimitive, Integer):
    _mixin_ = True

class Int8(BaseType, Integer):
    _attrs_ = ()

    T = rffi.SIGNEDCHAR
    BoxType = interp_boxes.W_Int8Box
    format_code = "b"
NonNativeInt8 = Int8

class UInt8(BaseType, Integer):
    _attrs_ = ()

    T = rffi.UCHAR
    BoxType = interp_boxes.W_UInt8Box
    format_code = "B"
NonNativeUInt8 = UInt8

class Int16(BaseType, Integer):
    _attrs_ = ()

    T = rffi.SHORT
    BoxType = interp_boxes.W_Int16Box
    format_code = "h"

class NonNativeInt16(BaseType, NonNativeInteger):
    _attrs_ = ()

    T = rffi.SHORT
    BoxType = interp_boxes.W_Int16Box
    format_code = "h"

class UInt16(BaseType, Integer):
    _attrs_ = ()

    T = rffi.USHORT
    BoxType = interp_boxes.W_UInt16Box
    format_code = "H"

class NonNativeUInt16(BaseType, NonNativeInteger):
    _attrs_ = ()

    T = rffi.USHORT
    BoxType = interp_boxes.W_UInt16Box
    format_code = "H"

class Int32(BaseType, Integer):
    _attrs_ = ()

    T = rffi.INT
    BoxType = interp_boxes.W_Int32Box
    format_code = "i"

class NonNativeInt32(BaseType, NonNativeInteger):
    _attrs_ = ()

    T = rffi.INT
    BoxType = interp_boxes.W_Int32Box
    format_code = "i"

class UInt32(BaseType, Integer):
    _attrs_ = ()

    T = rffi.UINT
    BoxType = interp_boxes.W_UInt32Box
    format_code = "I"

class NonNativeUInt32(BaseType, NonNativeInteger):
    _attrs_ = ()

    T = rffi.UINT
    BoxType = interp_boxes.W_UInt32Box
    format_code = "I"

class Long(BaseType, Integer):
    _attrs_ = ()

    T = rffi.LONG
    BoxType = interp_boxes.W_LongBox
    format_code = "l"

class NonNativeLong(BaseType, NonNativeInteger):
    _attrs_ = ()

    T = rffi.LONG
    BoxType = interp_boxes.W_LongBox
    format_code = "l"

class ULong(BaseType, Integer):
    _attrs_ = ()

    T = rffi.ULONG
    BoxType = interp_boxes.W_ULongBox
    format_code = "L"

class NonNativeULong(BaseType, NonNativeInteger):
    _attrs_ = ()

    T = rffi.ULONG
    BoxType = interp_boxes.W_ULongBox
    format_code = "L"

def _int64_coerce(self, space, w_item):
    try:
        return self._base_coerce(space, w_item)
    except OperationError, e:
        if not e.match(space, space.w_OverflowError):
            raise
    bigint = space.bigint_w(w_item)
    try:
        value = bigint.tolonglong()
    except OverflowError:
        raise OperationError(space.w_OverflowError, space.w_None)
    return self.box(value)

class Int64(BaseType, Integer):
    _attrs_ = ()

    T = rffi.LONGLONG
    BoxType = interp_boxes.W_Int64Box
    format_code = "q"

    _coerce = func_with_new_name(_int64_coerce, '_coerce')

class NonNativeInt64(BaseType, NonNativeInteger):
    _attrs_ = ()

    T = rffi.LONGLONG
    BoxType = interp_boxes.W_Int64Box
    format_code = "q"    

    _coerce = func_with_new_name(_int64_coerce, '_coerce')

def _uint64_coerce(self, space, w_item):
    try:
        return self._base_coerce(space, w_item)
    except OperationError, e:
        if not e.match(space, space.w_OverflowError):
            raise
    bigint = space.bigint_w(w_item)
    try:
        value = bigint.toulonglong()
    except OverflowError:
        raise OperationError(space.w_OverflowError, space.w_None)
    return self.box(value)

class UInt64(BaseType, Integer):
    _attrs_ = ()

    T = rffi.ULONGLONG
    BoxType = interp_boxes.W_UInt64Box
    format_code = "Q"

    _coerce = func_with_new_name(_uint64_coerce, '_coerce')

class NonNativeUInt64(BaseType, NonNativeInteger):
    _attrs_ = ()

    T = rffi.ULONGLONG
    BoxType = interp_boxes.W_UInt64Box
    format_code = "Q"

    _coerce = func_with_new_name(_uint64_coerce, '_coerce')

class Float(Primitive):
    _mixin_ = True

    def _coerce(self, space, w_item):
        return self.box(space.float_w(space.call_function(space.w_float, w_item)))

    def str_format(self, box):
        return float2string(self.for_computation(self.unbox(box)), "g",
                            rfloat.DTSF_STR_PRECISION)

    def for_computation(self, v):
        return float(v)

    def default_fromstring(self, space):
        return self.box(-1.0)

    @simple_binary_op
    def div(self, v1, v2):
        try:
            return v1 / v2
        except ZeroDivisionError:
            if v1 == v2 == 0.0:
                return rfloat.NAN
            return rfloat.copysign(rfloat.INFINITY, v1 * v2)

    @simple_binary_op
    def floordiv(self, v1, v2):
        try:
            return math.floor(v1 / v2)
        except ZeroDivisionError:
            if v1 == v2 == 0.0:
                return rfloat.NAN
            return rfloat.copysign(rfloat.INFINITY, v1 * v2)

    @simple_binary_op
    def mod(self, v1, v2):
        return math.fmod(v1, v2)

    @simple_binary_op
    def pow(self, v1, v2):
        try:
            return math.pow(v1, v2)
        except ValueError:
            return rfloat.NAN
        except OverflowError:
            if math.modf(v2)[0] == 0 and math.modf(v2 / 2)[0] != 0:
                # Odd integer powers result in the same sign as the base
                return rfloat.copysign(rfloat.INFINITY, v1)
            return rfloat.INFINITY

    @simple_binary_op
    def copysign(self, v1, v2):
        return math.copysign(v1, v2)

    @simple_unary_op
    def sign(self, v):
        if v == 0.0:
            return 0.0
        return rfloat.copysign(1.0, v)

    @raw_unary_op
    def signbit(self, v):
        return rfloat.copysign(1.0, v) < 0.0

    @simple_unary_op
    def fabs(self, v):
        return math.fabs(v)

    @simple_binary_op
    def fmax(self, v1, v2):
        if math.isnan(v1):
            return v1
        elif math.isnan(v2):
            return v2
        return max(v1, v2)

    @simple_binary_op
    def fmin(self, v1, v2):
        if math.isnan(v1):
            return v1
        elif math.isnan(v2):
            return v2
        return min(v1, v2)

    @simple_binary_op
    def fmod(self, v1, v2):
        try:
            return math.fmod(v1, v2)
        except ValueError:
            return rfloat.NAN

    @simple_unary_op
    def reciprocal(self, v):
        if v == 0.0:
            return rfloat.copysign(rfloat.INFINITY, v)
        return 1.0 / v

    @simple_unary_op
    def floor(self, v):
        return math.floor(v)

    @simple_unary_op
    def ceil(self, v):
        return math.ceil(v)

    @simple_unary_op
    def trunc(self, v):
        try:
            return int(v)
        except OverflowError:
            return rfloat.copysign(rfloat.INFINITY, v)
        except ValueError:
            return v

    @simple_unary_op
    def exp(self, v):
        try:
            return math.exp(v)
        except OverflowError:
            return rfloat.INFINITY

    @simple_unary_op
    def exp2(self, v):
        try:
            return math.pow(2, v)
        except OverflowError:
            return rfloat.INFINITY

    @simple_unary_op
    def expm1(self, v):
        try:
            return rfloat.expm1(v)
        except OverflowError:
            return rfloat.INFINITY

    @simple_unary_op
    def sin(self, v):
        return math.sin(v)

    @simple_unary_op
    def cos(self, v):
        return math.cos(v)

    @simple_unary_op
    def tan(self, v):
        return math.tan(v)

    @simple_unary_op
    def arcsin(self, v):
        if not -1.0 <= v <= 1.0:
            return rfloat.NAN
        return math.asin(v)

    @simple_unary_op
    def arccos(self, v):
        if not -1.0 <= v <= 1.0:
            return rfloat.NAN
        return math.acos(v)

    @simple_unary_op
    def arctan(self, v):
        return math.atan(v)

    @simple_binary_op
    def arctan2(self, v1, v2):
        return math.atan2(v1, v2)

    @simple_unary_op
    def sinh(self, v):
        return math.sinh(v)

    @simple_unary_op
    def cosh(self, v):
        return math.cosh(v)

    @simple_unary_op
    def tanh(self, v):
        return math.tanh(v)

    @simple_unary_op
    def arcsinh(self, v):
        return math.asinh(v)

    @simple_unary_op
    def arccosh(self, v):
        if v < 1.0:
            return rfloat.NAN
        return math.acosh(v)

    @simple_unary_op
    def arctanh(self, v):
        if v == 1.0 or v == -1.0:
            return math.copysign(rfloat.INFINITY, v)
        if not -1.0 < v < 1.0:
            return rfloat.NAN
        return math.atanh(v)

    @simple_unary_op
    def sqrt(self, v):
        try:
            return math.sqrt(v)
        except ValueError:
            return rfloat.NAN

    @simple_unary_op
    def square(self, v):
        return v*v

    @raw_unary_op
    def isnan(self, v):
        return rfloat.isnan(v)

    @raw_unary_op
    def isinf(self, v):
        return rfloat.isinf(v)

    @raw_unary_op
    def isneginf(self, v):
        return rfloat.isinf(v) and v < 0

    @raw_unary_op
    def isposinf(self, v):
        return rfloat.isinf(v) and v > 0

    @raw_unary_op
    def isfinite(self, v):
        return not (rfloat.isinf(v) or rfloat.isnan(v))

    @simple_unary_op
    def radians(self, v):
        return v * degToRad
    deg2rad = radians

    @simple_unary_op
    def degrees(self, v):
        return v / degToRad

    @simple_unary_op
    def log(self, v):
        try:
            return math.log(v)
        except ValueError:
            if v == 0.0:
                # CPython raises ValueError here, so we have to check
                # the value to find the correct numpy return value
                return -rfloat.INFINITY
            return rfloat.NAN

    @simple_unary_op
    def log2(self, v):
        try:
            return math.log(v) / log2
        except ValueError:
            if v == 0.0:
                # CPython raises ValueError here, so we have to check
                # the value to find the correct numpy return value
                return -rfloat.INFINITY
            return rfloat.NAN

    @simple_unary_op
    def log10(self, v):
        try:
            return math.log10(v)
        except ValueError:
            if v == 0.0:
                # CPython raises ValueError here, so we have to check
                # the value to find the correct numpy return value
                return -rfloat.INFINITY
            return rfloat.NAN

    @simple_unary_op
    def log1p(self, v):
        try:
            return rfloat.log1p(v)
        except OverflowError:
            return -rfloat.INFINITY
        except ValueError:
            return rfloat.NAN

    @simple_binary_op
    def logaddexp(self, v1, v2):
        try:
            v1e = math.exp(v1)
        except OverflowError:
            v1e = rfloat.INFINITY
        try:
            v2e = math.exp(v2)
        except OverflowError:
            v2e = rfloat.INFINITY

        v12e = v1e + v2e
        try:
            return math.log(v12e)
        except ValueError:
            if v12e == 0.0:
                # CPython raises ValueError here, so we have to check
                # the value to find the correct numpy return value
                return -rfloat.INFINITY
            return rfloat.NAN

    @simple_binary_op
    def logaddexp2(self, v1, v2):
        try:
            v1e = math.pow(2, v1)
        except OverflowError:
            v1e = rfloat.INFINITY
        try:
            v2e = math.pow(2, v2)
        except OverflowError:
            v2e = rfloat.INFINITY

        v12e = v1e + v2e
        try:
            return math.log(v12e) / log2
        except ValueError:
            if v12e == 0.0:
                # CPython raises ValueError here, so we have to check
                # the value to find the correct numpy return value
                return -rfloat.INFINITY
            return rfloat.NAN

class NonNativeFloat(NonNativePrimitive, Float):
    _mixin_ = True

    def _read(self, storage, width, i, offset):
        if we_are_translated():
            res = libffi.array_getitem(clibffi.cast_type_to_ffitype(self.T),
                                        width, storage, i, offset)
        else:
            res = libffi.array_getitem_T(self.T, width, storage, i, offset)
        #return byteswap(res)
        return res

    def _write(self, storage, width, i, offset, value):
        #value = byteswap(value) XXX
        if we_are_translated():
            libffi.array_setitem(clibffi.cast_type_to_ffitype(self.T),
                                 width, storage, i, offset, value)
        else:
            libffi.array_setitem_T(self.T, width, storage, i, offset, value)

    def pack_str(self, box):
        # XXX byteswap
        return struct.pack(self.format_code, self.unbox(box))


class Float32(BaseType, Float):
    _attrs_ = ()

    T = rffi.FLOAT
    BoxType = interp_boxes.W_Float32Box
    format_code = "f"

class NonNativeFloat32(BaseType, NonNativeFloat):
    _attrs_ = ()

    T = rffi.FLOAT
    BoxType = interp_boxes.W_Float32Box
    format_code = "f"    

class Float64(BaseType, Float):
    _attrs_ = ()

    T = rffi.DOUBLE
    BoxType = interp_boxes.W_Float64Box
    format_code = "d"

class NonNativeFloat64(BaseType, NonNativeFloat):
    _attrs_ = ()

    T = rffi.DOUBLE
    BoxType = interp_boxes.W_Float64Box
    format_code = "d"

class BaseStringType(object):
    _mixin_ = True
    
    def __init__(self, size=0):
        self.size = size

    def get_element_size(self):
        return self.size * rffi.sizeof(self.T)

class StringType(BaseType, BaseStringType):
    T = lltype.Char

class VoidType(BaseType, BaseStringType):
    T = lltype.Char

NonNativeVoidType = VoidType
NonNativeStringType = StringType

class UnicodeType(BaseType, BaseStringType):
    T = lltype.UniChar

NonNativeUnicodeType = UnicodeType

class RecordType(BaseType):

    T = lltype.Char

    def __init__(self, offsets_and_fields, size):
        self.offsets_and_fields = offsets_and_fields
        self.size = size

    def get_element_size(self):
        return self.size
    
    def read(self, arr, width, i, offset, dtype=None):
        if dtype is None:
            dtype = arr.dtype
        return interp_boxes.W_VoidBox(arr, i + offset, dtype)

    @jit.unroll_safe
    def coerce(self, space, dtype, w_item): 
        from pypy.module.micronumpy.interp_numarray import W_NDimArray

        if isinstance(w_item, interp_boxes.W_VoidBox):
            return w_item
        # we treat every sequence as sequence, no special support
        # for arrays
        if not space.issequence_w(w_item):
            raise OperationError(space.w_TypeError, space.wrap(
                "expected sequence"))
        if len(self.offsets_and_fields) != space.int_w(space.len(w_item)):
            raise OperationError(space.w_ValueError, space.wrap(
                "wrong length"))
        items_w = space.fixedview(w_item)
        # XXX optimize it out one day, but for now we just allocate an
        #     array
        arr = W_NDimArray([1], dtype)
        for i in range(len(items_w)):
            subdtype = dtype.fields[dtype.fieldnames[i]][1]
            ofs, itemtype = self.offsets_and_fields[i]
            w_item = items_w[i]
            w_box = itemtype.coerce(space, subdtype, w_item)
            itemtype.store(arr, 1, 0, ofs, w_box)
        return interp_boxes.W_VoidBox(arr, 0, arr.dtype)

    @jit.unroll_safe
    def store(self, arr, _, i, ofs, box):
        assert isinstance(box, interp_boxes.W_VoidBox)
        for k in range(self.get_element_size()):
            arr.storage[k + i] = box.arr.storage[k + box.ofs]

    @jit.unroll_safe
    def str_format(self, box):
        assert isinstance(box, interp_boxes.W_VoidBox)
        pieces = ["("]
        first = True
        for ofs, tp in self.offsets_and_fields:
            if first:
                first = False
            else:
                pieces.append(", ")
            pieces.append(tp.str_format(tp.read(box.arr, 1, box.ofs, ofs)))
        pieces.append(")")
        return "".join(pieces)

for tp in [Int32, Int64]:
    if tp.T == lltype.Signed:
        IntP = tp
        break
for tp in [UInt32, UInt64]:
    if tp.T == lltype.Unsigned:
        UIntP = tp
        break
del tp

def _setup():
    # compute alignment
    for tp in globals().values():
        if isinstance(tp, type) and hasattr(tp, 'T'):
            tp.alignment = clibffi.cast_type_to_ffitype(tp.T).c_alignment
_setup()
del _setup

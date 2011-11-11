import math

from pypy.module.micronumpy import interp_boxes
from pypy.objspace.std.floatobject import float2string
from pypy.rlib import rfloat
from pypy.rlib.rarithmetic import LONG_BIT
from pypy.rpython.lltypesystem import lltype, rffi


def simple_unary_op(func):
    def dispatcher(self, v):
        return self.box(func(self, self.unbox(v)))
    return dispatcher

def simple_binary_op(func):
    def dispatcher(self, v1, v2):
        return self.box(func(self, self.unbox(v1), self.unbox(v2)))
    return dispatcher

class BaseType(object):
    def _unimplemented_ufunc(self, *args):
        raise NotImplementedError
    add = sub = mul = div = mod = pow = eq = ne = lt = le = gt = ge = max = \
        min = copysign = pos = neg = abs = sign = reciprocal = fabs = floor = \
        exp = sin = cos = tan = arcsin = arccos = arctan = arcsinh = \
        arctanh = _unimplemented_ufunc

class Primitive(BaseType):
    def get_element_size(self):
        return rffi.sizeof(self.T)

    def box(self, value):
        return self.BoxType(rffi.cast(self.T, value))

    def unbox(self, box):
        assert isinstance(box, self.BoxType)
        return box.value

    def coerce(self, space, w_item):
        if isinstance(w_item, self.BoxType):
            return w_item
        return self._coerce(space, w_item)

    def _coerce(self, space, w_item):
        raise NotImplementedError

    def read(self, ptr, offset):
        ptr = rffi.ptradd(ptr, offset)
        return self.box(
            rffi.cast(lltype.Ptr(lltype.Array(self.T, hints={"nolength": True})), ptr)[0]
        )

    def store(self, ptr, offset, box):
        value = self.unbox(box)
        ptr = rffi.ptradd(ptr, offset)
        rffi.cast(lltype.Ptr(lltype.Array(self.T, hints={"nolength": True})), ptr)[0] = value

    def fill(self, ptr, box, n):
        value = self.unbox(box)
        for i in xrange(n):
            rffi.cast(lltype.Ptr(lltype.Array(self.T, hints={"nolength": True})), ptr)[0] = value
            ptr = rffi.ptradd(ptr, self.get_element_size())

    def add(self, v1, v2):
        return self.box(self.unbox(v1) + self.unbox(v2))

    def sub(self, v1, v2):
        return self.box(self.unbox(v1) - self.unbox(v2))

    def mul(self, v1, v2):
        return self.box(self.unbox(v1) * self.unbox(v2))

    def pos(self, v):
        return self.box(+self.unbox(v))

    def neg(self, v):
        return self.box(-self.unbox(v))

    @simple_unary_op
    def abs(self, v):
        return abs(v)

    def eq(self, v1, v2):
        return self.unbox(v1) == self.unbox(v2)

    def ne(self, v1, v2):
        return self.unbox(v1) != self.unbox(v2)

    def lt(self, v1, v2):
        return self.unbox(v1) < self.unbox(v2)

    def le(self, v1, v2):
        return self.unbox(v1) <= self.unbox(v2)

    def gt(self, v1, v2):
        return self.unbox(v1) > self.unbox(v2)

    def ge(self, v1, v2):
        return self.unbox(v1) >= self.unbox(v2)

    def bool(self, v):
        return bool(self.unbox(v))

    def max(self, v1, v2):
        return self.box(max(self.unbox(v1), self.unbox(v2)))

    def min(self, v1, v2):
        return self.box(min(self.unbox(v1), self.unbox(v2)))

class Bool(Primitive):
    T = lltype.Bool
    BoxType = interp_boxes.W_BoolBox

    True = BoxType(True)
    False = BoxType(False)

    def box(self, value):
        box = Primitive.box(self, value)
        if box.value:
            return self.True
        else:
            return self.False

    def _coerce(self, space, w_item):
        return self.box(space.is_true(w_item))

    def str_format(self, box):
        value = self.unbox(box)
        return "True" if value else "False"

class Integer(Primitive):
    def _coerce(self, space, w_item):
        return self.box(space.int_w(space.int(w_item)))

    def str_format(self, box):
        value = self.unbox(box)
        return str(value)

    @simple_binary_op
    def div(self, v1, v2):
        if v2 == 0:
            return 0
        return v1 / v2

    @simple_binary_op
    def mod(self, v1, v2):
        return v1 % v2

    @simple_unary_op
    def sign(self, v):
        if v > 0:
            return 1
        elif v < 0:
            return -1
        else:
            assert v == 0
            return 0

class Int8(Integer):
    T = rffi.SIGNEDCHAR
    BoxType = interp_boxes.W_Int8Box

class UInt8(Integer):
    T = rffi.UCHAR
    BoxType = interp_boxes.W_UInt8Box

class Int16(Integer):
    T = rffi.SHORT
    BoxType = interp_boxes.W_Int16Box

class UInt16(Integer):
    T = rffi.USHORT
    BoxType = interp_boxes.W_UInt16Box

class Int32(Integer):
    T = rffi.INT
    BoxType = interp_boxes.W_Int32Box

class UInt32(Integer):
    T = rffi.UINT
    BoxType = interp_boxes.W_UInt32Box

class Long(Integer):
    T = rffi.LONG
    BoxType = interp_boxes.W_LongBox

class ULong(Integer):
    T = rffi.ULONG
    BoxType = interp_boxes.W_ULongBox

class Int64(Integer):
    T = rffi.LONGLONG
    BoxType = interp_boxes.W_Int64Box

class UInt64(Integer):
    T = rffi.ULONGLONG
    BoxType = interp_boxes.W_UInt64Box

class Float(Primitive):
    def _coerce(self, space, w_item):
        return self.box(space.float_w(space.float(w_item)))

    def str_format(self, box):
        value = self.unbox(box)
        return float2string(value, "g", rfloat.DTSF_STR_PRECISION)

    @simple_binary_op
    def div(self, v1, v2):
        try:
            return v1 / v2
        except ZeroDivisionError:
            if v1 == v2 == 0.0:
                return rfloat.NAN
            return rfloat.copysign(rfloat.INFINITY, v1 * v2)

    @simple_binary_op
    def mod(self, v1, v2):
        return math.fmod(v1, v2)

    @simple_binary_op
    def pow(self, v1, v2):
        return math.pow(v1, v2)

    @simple_binary_op
    def copysign(self, v1, v2):
        return math.copysign(v1, v2)

    @simple_unary_op
    def sign(self, v):
        if v == 0.0:
            return 0.0
        return rfloat.copysign(1.0, v)

    @simple_unary_op
    def fabs(self, v):
        return math.fabs(v)

    @simple_unary_op
    def reciprocal(self, v):
        if v == 0.0:
            return rfloat.copysign(rfloat.INFINITY, v)
        return 1.0 / v

    @simple_unary_op
    def floor(self, v):
        return math.floor(v)

    @simple_unary_op
    def exp(self, v):
        try:
            return math.exp(v)
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

    @simple_unary_op
    def arcsinh(self, v):
        return math.asinh(v)

    @simple_unary_op
    def arctanh(self, v):
        if v == 1.0 or v == -1.0:
            return math.copysign(rfloat.INFINITY, v)
        if not -1.0 < v < 1.0:
            return rfloat.NAN
        return math.atanh(v)


class Float32(Float):
    T = rffi.FLOAT
    BoxType = interp_boxes.W_Float32Box

class Float64(Float):
    T = rffi.DOUBLE
    BoxType = interp_boxes.W_Float64Box
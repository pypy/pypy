from pypy.module.micronumpy import interp_boxes
from pypy.objspace.std.floatobject import float2string
from pypy.rlib import rfloat
from pypy.rpython.lltypesystem import lltype, rffi


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

    def add(self, v1, v2):
        return self.box(self.unbox(v1) + self.unbox(v2))

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

    def coerce(self, space, w_item):
        return self.box(space.is_true(w_item))

class Integer(Primitive):
    def coerce(self, space, w_item):
        return self.box(space.int_w(space.int(w_item)))

class Int8(Primitive):
    T = rffi.SIGNEDCHAR

class UInt8(Primitive):
    T = rffi.UCHAR

class Int16(Primitive):
    T = rffi.SHORT

class UInt16(Primitive):
    T = rffi.USHORT

class Int32(Primitive):
    T = rffi.INT

class UInt32(Primitive):
    T = rffi.UINT

class Int64(Integer):
    T = rffi.LONGLONG
    BoxType = interp_boxes.W_Int64Box

class UInt64(Primitive):
    T = rffi.ULONGLONG

class Float(Primitive):
    def coerce(self, space, w_item):
        return self.box(space.float_w(space.float(w_item)))

    def str_format(self, box):
        value = self.unbox(box)
        return float2string(value, "g", rfloat.DTSF_STR_PRECISION)

class Float32(Primitive):
    T = rffi.FLOAT

class Float64(Float):
    T = rffi.DOUBLE
    BoxType = interp_boxes.W_Float64Box
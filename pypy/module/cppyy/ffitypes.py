from pypy.interpreter.error import oefmt

from rpython.rtyper.lltypesystem import rffi
from rpython.rlib.rarithmetic import r_singlefloat
from rpython.rlib.rbigint import rbigint
from rpython.rlib import jit_libffi, rfloat

# Mixins to share between converter and executor classes (in converter.py and
# executor.py, respectively). Basically these mixins allow grouping of the
# sets of jit_libffi, rffi, and different space unwrapping calls. To get the
# right mixin, a non-RPython function typeid() is used.

class BoolTypeMixin(object):
    _mixin_     = True
    _immutable_fields_ = ['libffitype', 'c_type', 'c_ptrtype']

    libffitype  = jit_libffi.types.uchar
    c_type      = rffi.UCHAR
    c_ptrtype   = rffi.UCHARP

    def _wrap_object(self, space, obj):
        return space.newbool(bool(ord(rffi.cast(rffi.CHAR, obj))))

    def _unwrap_object(self, space, w_obj):
        arg = space.c_int_w(w_obj)
        if arg != False and arg != True:
            raise oefmt(space.w_ValueError,
                        "boolean value should be bool, or integer 1 or 0")
        return arg

class CharTypeMixin(object):
    _mixin_     = True
    _immutable_fields_ = ['libffitype', 'c_type', 'c_ptrtype']

    libffitype  = jit_libffi.types.schar
    c_type      = rffi.CHAR
    c_ptrtype   = rffi.CCHARP           # there's no such thing as rffi.CHARP

    def _wrap_object(self, space, obj):
        return space.newbytes(obj)

    def _unwrap_object(self, space, w_value):
        # allow int to pass to char and make sure that str is of length 1
        if space.isinstance_w(w_value, space.w_int):
            ival = space.c_int_w(w_value)
            if ival < 0 or 256 <= ival:
                raise oefmt(space.w_ValueError, "char arg not in range(256)")

            value = rffi.cast(rffi.CHAR, space.c_int_w(w_value))
        else:
            value = space.bytes_w(w_value)

        if len(value) != 1:  
            raise oefmt(space.w_ValueError,
                        "char expected, got string of size %d", len(value))
        return value[0] # turn it into a "char" to the annotator

class BaseIntTypeMixin(object):
    _mixin_     = True

    def _wrap_object(self, space, obj):
        return space.newint(rffi.cast(rffi.INT, obj))

    def _unwrap_object(self, space, w_obj):
        return rffi.cast(self.c_type, space.c_int_w(w_obj))

class ShortTypeMixin(BaseIntTypeMixin):
    _mixin_     = True
    _immutable_fields_ = ['libffitype', 'c_type', 'c_ptrtype']

    libffitype  = jit_libffi.types.sshort
    c_type      = rffi.SHORT
    c_ptrtype   = rffi.SHORTP

class UShortTypeMixin(BaseIntTypeMixin):
    _mixin_     = True
    _immutable_fields_ = ['libffitype', 'c_type', 'c_ptrtype']

    libffitype  = jit_libffi.types.ushort
    c_type      = rffi.USHORT
    c_ptrtype   = rffi.USHORTP

class IntTypeMixin(BaseIntTypeMixin):
    _mixin_     = True
    _immutable_fields_ = ['libffitype', 'c_type', 'c_ptrtype']

    libffitype  = jit_libffi.types.sint
    c_type      = rffi.INT
    c_ptrtype   = rffi.INTP

class UIntTypeMixin(object):
    _mixin_     = True
    _immutable_fields_ = ['libffitype', 'c_type', 'c_ptrtype']

    libffitype  = jit_libffi.types.uint
    c_type      = rffi.UINT
    c_ptrtype   = rffi.UINTP

    def _wrap_object(self, space, obj):
        return space.newlong_from_rarith_int(obj)

    def _unwrap_object(self, space, w_obj):
        return rffi.cast(self.c_type, space.uint_w(w_obj))

class LongTypeMixin(object):
    _mixin_     = True
    _immutable_fields_ = ['libffitype', 'c_type', 'c_ptrtype']

    libffitype  = jit_libffi.types.slong
    c_type      = rffi.LONG
    c_ptrtype   = rffi.LONGP

    def _wrap_object(self, space, obj):
        return space.newlong(obj)

    def _unwrap_object(self, space, w_obj):
        return space.int_w(w_obj)

class ULongTypeMixin(object):
    _mixin_     = True
    _immutable_fields_ = ['libffitype', 'c_type', 'c_ptrtype']

    libffitype  = jit_libffi.types.ulong
    c_type      = rffi.ULONG
    c_ptrtype   = rffi.ULONGP

    def _wrap_object(self, space, obj):
        return space.newlong_from_rarith_int(obj)

    def _unwrap_object(self, space, w_obj):
        return space.uint_w(w_obj)

class LongLongTypeMixin(object):
    _mixin_     = True
    _immutable_fields_ = ['libffitype', 'c_type', 'c_ptrtype']

    libffitype  = jit_libffi.types.sint64
    c_type      = rffi.LONGLONG
    c_ptrtype   = rffi.LONGLONGP

    def _wrap_object(self, space, obj):
        return space.newlong_from_rarith_int(obj)

    def _unwrap_object(self, space, w_obj):
        return space.r_longlong_w(w_obj)

class ULongLongTypeMixin(object):
    _mixin_     = True
    _immutable_fields_ = ['libffitype', 'c_type', 'c_ptrtype']

    libffitype  = jit_libffi.types.uint64
    c_type      = rffi.ULONGLONG
    c_ptrtype   = rffi.ULONGLONGP

    def _wrap_object(self, space, obj):
        return space.newlong_from_rarith_int(obj)

    def _unwrap_object(self, space, w_obj):
        return space.r_ulonglong_w(w_obj)

class FloatTypeMixin(object):
    _mixin_     = True
    _immutable_fields_ = ['libffitype', 'c_type', 'c_ptrtype', 'typecode']

    libffitype  = jit_libffi.types.float
    c_type      = rffi.FLOAT
    c_ptrtype   = rffi.FLOATP
    typecode    = 'f'

    def _unwrap_object(self, space, w_obj):
        return r_singlefloat(space.float_w(w_obj))

    def _wrap_object(self, space, obj):
        return space.newfloat(float(obj))

class DoubleTypeMixin(object):
    _mixin_     = True
    _immutable_fields_ = ['libffitype', 'c_type', 'c_ptrtype', 'typecode']

    libffitype  = jit_libffi.types.double
    c_type      = rffi.DOUBLE
    c_ptrtype   = rffi.DOUBLEP
    typecode    = 'd'

    def _wrap_object(self, space, obj):
        return space.newfloat(obj)

    def _unwrap_object(self, space, w_obj):
        return space.float_w(w_obj)


def typeid(c_type):
    "NOT_RPYTHON"
    if c_type == bool:            return BoolTypeMixin
    if c_type == rffi.CHAR:       return CharTypeMixin
    if c_type == rffi.SHORT:      return ShortTypeMixin
    if c_type == rffi.USHORT:     return UShortTypeMixin
    if c_type == rffi.INT:        return IntTypeMixin
    if c_type == rffi.UINT:       return UIntTypeMixin
    if c_type == rffi.LONG:       return LongTypeMixin
    if c_type == rffi.ULONG:      return ULongTypeMixin
    if c_type == rffi.LONGLONG:   return LongLongTypeMixin
    if c_type == rffi.ULONGLONG:  return ULongLongTypeMixin
    if c_type == rffi.FLOAT:      return FloatTypeMixin
    if c_type == rffi.DOUBLE:     return DoubleTypeMixin

    # should never get here
    raise TypeError("unknown rffi type: %s" % c_type)

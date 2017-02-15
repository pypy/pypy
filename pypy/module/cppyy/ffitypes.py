from pypy.interpreter.error import oefmt

from rpython.rtyper.lltypesystem import rffi
from rpython.rlib.rarithmetic import r_singlefloat, r_longfloat

from pypy.module._cffi_backend import newtype

# Mixins to refactor type-specific codef from converter and executor classes
# (in converter.py and executor.py, respectively). To get the right mixin, a
# non-RPython function typeid() is used.

class State(object):
    def __init__(self, space):
        self.library = None
        self.capi_calls = {}

        nt = newtype     # module from _cffi_backend

        # builtin types
        self.c_void    = nt.new_void_type(space)
        self.c_bool    = nt.new_primitive_type(space, '_Bool')
        self.c_char    = nt.new_primitive_type(space, 'char')
        self.c_uchar   = nt.new_primitive_type(space, 'unsigned char')
        self.c_short   = nt.new_primitive_type(space, 'short')
        self.c_ushort  = nt.new_primitive_type(space, 'unsigned short')
        self.c_int     = nt.new_primitive_type(space, 'int')
        self.c_uint    = nt.new_primitive_type(space, 'unsigned int')
        self.c_long    = nt.new_primitive_type(space, 'long')
        self.c_ulong   = nt.new_primitive_type(space, 'unsigned long')
        self.c_llong   = nt.new_primitive_type(space, 'long long')
        self.c_ullong  = nt.new_primitive_type(space, 'unsigned long long')
        self.c_float   = nt.new_primitive_type(space, 'float')
        self.c_double  = nt.new_primitive_type(space, 'double')
        self.c_ldouble = nt.new_primitive_type(space, 'long double')
        
        # pointer types
        self.c_ccharp = nt.new_pointer_type(space, self.c_char)
        self.c_voidp  = nt.new_pointer_type(space, self.c_void)

        # special types
        self.c_size_t    = nt.new_primitive_type(space, 'size_t')
        self.c_ptrdiff_t = nt.new_primitive_type(space, 'ptrdiff_t')

class BoolTypeMixin(object):
    _mixin_     = True
    _immutable_fields_ = ['c_type', 'c_ptrtype']

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

    def _wrap_object(self, space, obj):
        return space.newbool(bool(ord(rffi.cast(rffi.CHAR, obj))))

    def cffi_type(self, space):
        state = space.fromcache(State)
        return state.c_bool

class CharTypeMixin(object):
    _mixin_     = True
    _immutable_fields_ = ['c_type', 'c_ptrtype']

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
            value = space.str_w(w_value)

        if len(value) != 1:  
            raise oefmt(space.w_ValueError,
                        "char expected, got string of size %d", len(value))
        return value[0] # turn it into a "char" to the annotator

    def cffi_type(self, space):
        state = space.fromcache(State)
        return state.c_char

class ShortTypeMixin(BaseIntTypeMixin):
    _mixin_     = True
    _immutable_fields_ = ['c_type', 'c_ptrtype']

    c_type      = rffi.SHORT
    c_ptrtype   = rffi.SHORTP

    def _unwrap_object(self, space, w_obj):
        return rffi.cast(rffi.SHORT, space.int_w(w_obj))

    def cffi_type(self, space):
        state = space.fromcache(State)
        return state.c_short

class UShortTypeMixin(BaseIntTypeMixin):
    _mixin_     = True
    _immutable_fields_ = ['c_type', 'c_ptrtype']

    c_type      = rffi.USHORT
    c_ptrtype   = rffi.USHORTP

    def _unwrap_object(self, space, w_obj):
        return rffi.cast(self.c_type, space.int_w(w_obj))

    def cffi_type(self, space):
        state = space.fromcache(State)
        return state.c_ushort

class IntTypeMixin(BaseIntTypeMixin):
    _mixin_     = True
    _immutable_fields_ = ['c_type', 'c_ptrtype']

    c_type      = rffi.INT
    c_ptrtype   = rffi.INTP

    def _unwrap_object(self, space, w_obj):
        return rffi.cast(self.c_type, space.c_int_w(w_obj))

    def cffi_type(self, space):
        state = space.fromcache(State)
        return state.c_int

class UIntTypeMixin(BaseLongTypeMixin):
    _mixin_     = True
    _immutable_fields_ = ['c_type', 'c_ptrtype']

    c_type      = rffi.UINT
    c_ptrtype   = rffi.UINTP

    def _wrap_object(self, space, obj):
        return space.newlong_from_rarith_int(obj)

    def _unwrap_object(self, space, w_obj):
        return rffi.cast(self.c_type, space.uint_w(w_obj))

    def cffi_type(self, space):
        state = space.fromcache(State)
        return state.c_uint

class LongTypeMixin(BaseLongTypeMixin):
    _mixin_     = True
    _immutable_fields_ = ['c_type', 'c_ptrtype']

    c_type      = rffi.LONG
    c_ptrtype   = rffi.LONGP

    def _wrap_object(self, space, obj):
        return space.newlong(obj)

    def _unwrap_object(self, space, w_obj):
        return space.int_w(w_obj)

    def cffi_type(self, space):
        state = space.fromcache(State)
        return state.c_long

# TODO: check ULong limits; actually, they fail if this is
#  an BaseLongTypeMixin (i.e. use of space.ewlong) ... why??
class ULongTypeMixin(BaseIntTypeMixin):
    _mixin_     = True
    _immutable_fields_ = ['c_type', 'c_ptrtype']

    c_type      = rffi.ULONG
    c_ptrtype   = rffi.ULONGP

    def _wrap_object(self, space, obj):
        return space.newlong_from_rarith_int(obj)

    def _unwrap_object(self, space, w_obj):
        return space.uint_w(w_obj)

    def cffi_type(self, space):
        state = space.fromcache(State)
        return state.c_ulong

class LongLongTypeMixin(BaseLongTypeMixin):
    _mixin_     = True
    _immutable_fields_ = ['c_type', 'c_ptrtype']

    c_type      = rffi.LONGLONG
    c_ptrtype   = rffi.LONGLONGP

    def _wrap_object(self, space, obj):
        return space.newlong_from_rarith_int(obj)

    def _unwrap_object(self, space, w_obj):
        return space.r_longlong_w(w_obj)

    def cffi_type(self, space):
        state = space.fromcache(State)
        return state.c_llong

class ULongLongTypeMixin(BaseLongTypeMixin):
    _mixin_     = True
    _immutable_fields_ = ['c_type', 'c_ptrtype']

    c_type      = rffi.ULONGLONG
    c_ptrtype   = rffi.ULONGLONGP

    def _wrap_object(self, space, obj):
        return space.newlong_from_rarith_int(obj)

    def _unwrap_object(self, space, w_obj):
        return space.r_ulonglong_w(w_obj)

    def cffi_type(self, space):
        state = space.fromcache(State)
        return state.c_ullong

class FloatTypeMixin(object):
    _mixin_     = True
    _immutable_fields_ = ['c_type', 'c_ptrtype', 'typecode']

    c_type      = rffi.FLOAT
    c_ptrtype   = rffi.FLOATP
    typecode    = 'f'

    def _unwrap_object(self, space, w_obj):
        return r_singlefloat(space.float_w(w_obj))

    def _wrap_object(self, space, obj):
        return space.newfloat(float(obj))

    def cffi_type(self, space):
        state = space.fromcache(State)
        return state.c_float

class DoubleTypeMixin(object):
    _mixin_     = True
    _immutable_fields_ = ['c_type', 'c_ptrtype', 'typecode']

    c_type      = rffi.DOUBLE
    c_ptrtype   = rffi.DOUBLEP
    typecode    = 'd'

    def _wrap_object(self, space, obj):
        return space.newfloat(obj)

    def _unwrap_object(self, space, w_obj):
        return space.float_w(w_obj)

    def cffi_type(self, space):
        state = space.fromcache(State)
        return state.c_double

class LongDoubleTypeMixin(object):
    _mixin_     = True
    _immutable_fields_ = ['c_type', 'c_ptrtype', 'typecode']

    c_type      = rffi.LONGDOUBLE
    c_ptrtype   = rffi.LONGDOUBLEP
    typecode    = 'g'

    # long double is not really supported ...
    def _unwrap_object(self, space, w_obj):
        return r_longfloat(space.float_w(w_obj))

    def _wrap_object(self, space, obj):
        return space.wrap(obj)

    def cffi_type(self, space):
        state = space.fromcache(State)
        return state.c_ldouble

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
    if c_type == rffi.LONGDOUBLE: return LongDoubleTypeMixin

    # should never get here
    raise TypeError("unknown rffi type: %s" % c_type)

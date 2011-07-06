import sys

from pypy.interpreter.error import OperationError
from pypy.interpreter.buffer import Buffer
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib.rarithmetic import r_singlefloat
from pypy.rlib import jit, libffi, clibffi

from pypy.module._rawffi.interp_rawffi import unpack_simple_shape
from pypy.module._rawffi.array import W_Array

from pypy.module.cppyy import helper, capi


NULL = lltype.nullptr(clibffi.FFI_TYPE_P.TO)

def get_rawobject(space, w_obj):
    if not space.eq_w(w_obj, space.w_None):
        from pypy.module.cppyy.interp_cppyy import W_CPPInstance
        w_cpp_instance = space.findattr(w_obj, space.wrap("_cppinstance"))
        cpp_instance = space.interp_w(W_CPPInstance, w_cpp_instance, can_be_None=True)
        if cpp_instance:
            return cpp_instance.rawobject
    return lltype.nullptr(rffi.VOIDP.TO)


class TypeConverter(object):
    _immutable = True
    libffitype = NULL

    def __init__(self, space, array_size):
        pass

    @jit.dont_look_inside
    def _get_raw_address(self, space, w_obj, offset):
        rawobject = get_rawobject(space, w_obj)
        if rawobject:
            field_address = lltype.direct_ptradd(rawobject, offset)
            fieldptr = rffi.cast(rffi.CCHARP, field_address)
        else:
            fieldptr = rffi.cast(rffi.CCHARP, offset)
        return fieldptr

    def _is_abstract(self):
        raise NotImplementedError(
            "abstract base class" ) # more detailed part is not rpython: (actual: %s)" % type(self).__name__)

    def convert_argument(self, space, w_obj):
        self._is_abstract()

    def convert_argument_libffi(self, space, w_obj, argchain):
        from pypy.module.cppyy.interp_cppyy import FastCallNotPossible
        raise FastCallNotPossible

    def from_memory(self, space, w_obj, offset):
        self._is_abstract()

    def to_memory(self, space, w_obj, w_value, offset):
        self._is_abstract()

    def free_argument(self, arg):
        lltype.free(arg, flavor='raw')


class ArrayTypeConverter(TypeConverter):
    _immutable = True
    _immutable_fields_ = ["size"]
    typecode = ''
    typesize = 0         # TODO: get sizeof(type) from system

    def __init__(self, space, array_size):
        if array_size <= 0:
            self.size = sys.maxint
        else:
            self.size = array_size

    def from_memory(self, space, w_obj, offset):
        # read access, so no copy needed
        address_value = self._get_raw_address(space, w_obj, offset)
        address = rffi.cast(rffi.UINT, address_value)
        arr = space.interp_w(W_Array, unpack_simple_shape(space, space.wrap(self.typecode)))
        return arr.fromaddress(space, address, self.size)

    def to_memory(self, space, w_obj, w_value, offset):
        # copy the full array (uses byte copy for now)
        address = self._get_raw_address(space, w_obj, offset)
        buf = space.interp_w(Buffer, w_value.getslotvalue(2))
        for i in range(min(self.size*self.typesize, buf.getlength())):
            address[i] = buf.getitem(i)


class PtrTypeConverter(ArrayTypeConverter):
    _immutable_ = True

    def _get_raw_address(self, space, w_obj, offset):
        address = TypeConverter._get_raw_address(self, space, w_obj, offset)
        ptr2ptr = rffi.cast(rffi.LONGP, address)
        return rffi.cast(rffi.CCHARP, ptr2ptr[0])


class VoidConverter(TypeConverter):
    _immutable = True
    libffitype = libffi.types.void

    def __init__(self, space, name):
        self.name = name

    def convert_argument(self, space, w_obj):
        raise OperationError(space.w_TypeError,
                             space.wrap('no converter available for type "%s"' % self.name))


class BoolConverter(TypeConverter):
    _immutable = True
    libffitype = libffi.types.sint               # TODO: probably incorrect

    def convert_argument(self, space, w_obj):
        arg = space.c_int_w(w_obj)
        if arg != False and arg != True:
            raise OperationError(space.w_TypeError,
                                 space.wrap("boolean value should be bool, or integer 1 or 0"))
        x = lltype.malloc(rffi.LONGP.TO, 1, flavor='raw')
        x[0] = arg
        return rffi.cast(rffi.VOIDP, x)

    def from_memory(self, space, w_obj, offset):
        address = self._get_raw_address(space, w_obj, offset)
        if address[0] == '\x01':
            return space.wrap(True)
        return space.wrap(False)

    def to_memory(self, space, w_obj, w_value, offset):
        address = self._get_raw_address(space, w_obj, offset)
        arg = space.c_int_w(w_value)
        if arg != False and arg != True:
            raise OperationError(space.w_TypeError,
                                 space.wrap("boolean value should be bool, or integer 1 or 0"))
        if arg:
            address[0] = '\x01'
        else:
            address[0] = '\x00'

class CharConverter(TypeConverter):
    _immutable = True
    libffitype = libffi.types.schar

    def _from_space(self, space, w_value):
        # allow int to pass to char and make sure that str is of length 1
        if space.isinstance_w(w_value, space.w_int):
            ival = space.c_int_w(w_value)
            if ival < 0 or 256 <= ival:
                raise OperationError(space.w_TypeError,
                                     space.wrap("char arg not in range(256)"))

            value = rffi.cast(rffi.CHAR, space.c_int_w(w_value))
        else:
            value = space.str_w(w_value)

        if len(value) != 1:  
            raise OperationError(space.w_TypeError,
                                 space.wrap("char expected, got string of size %d" % len(value)))
        return value[0] # turn it into a "char" to the annotator

    def convert_argument(self, space, w_obj):
        arg = self._from_space(space, w_obj)
        x = rffi.str2charp(arg)
        return rffi.cast(rffi.VOIDP, x)

    def from_memory(self, space, w_obj, offset):
        address = self._get_raw_address(space, w_obj, offset)
        return space.wrap(address[0])

    def to_memory(self, space, w_obj, w_value, offset):
        address = self._get_raw_address(space, w_obj, offset)
        address[0] = self._from_space(space, w_value)

class LongConverter(TypeConverter):
    _immutable = True
    libffitype = libffi.types.slong

    def _unwrap_object(self, space, w_obj):
        return space.c_int_w(w_obj)

    def convert_argument(self, space, w_obj):
        arg = self._unwrap_object(space, w_obj)
        x = lltype.malloc(rffi.LONGP.TO, 1, flavor='raw')
        x[0] = arg
        return rffi.cast(rffi.VOIDP, x)

    def convert_argument_libffi(self, space, w_obj, argchain):
        argchain.arg(self._unwrap_object(space, w_obj))

    def from_memory(self, space, w_obj, offset):
        address = self._get_raw_address(space, w_obj, offset)
        longptr = rffi.cast(rffi.LONGP, address)
        return space.wrap(longptr[0])

    def to_memory(self, space, w_obj, w_value, offset):
        address = self._get_raw_address(space, w_obj, offset)
        longptr = rffi.cast(rffi.LONGP, address)
        longptr[0] = space.c_int_w(w_value)

class UnsignedLongConverter(TypeConverter):
    _immutable = True
    libffitype = libffi.types.ulong

    def _unwrap_object(self, space, w_obj):
        return space.c_uint_w(w_obj)

    def convert_argument(self, space, w_obj):
        arg = self._unwrap_object(space, w_obj)
        x = lltype.malloc(rffi.ULONGP.TO, 1, flavor='raw')
        x[0] = arg
        return rffi.cast(rffi.VOIDP, x)

    def from_memory(self, space, w_obj, offset):
        address = self._get_raw_address(space, w_obj, offset)
        ulongptr = rffi.cast(rffi.ULONGP, address)
        return space.wrap(ulongptr[0])

    def to_memory(self, space, w_obj, w_value, offset):
        address = self._get_raw_address(space, w_obj, offset)
        ulongptr = rffi.cast(rffi.ULONGP, address)
        ulongptr[0] = space.c_uint_w(w_value)

class ShortConverter(LongConverter):
    _immutable = True
    libffitype = libffi.types.sshort

    def from_memory(self, space, w_obj, offset):
        address = self._get_raw_address(space, w_obj, offset)
        shortptr = rffi.cast(rffi.SHORTP, address)
        return space.wrap(shortptr[0])

    def to_memory(self, space, w_obj, w_value, offset):
        address = self._get_raw_address(space, w_obj, offset)
        shortptr = rffi.cast(rffi.SHORTP, address)
        shortptr[0] = rffi.cast(rffi.SHORT, self._unwrap_object(space, w_value))

class FloatConverter(TypeConverter):
    _immutable = True
    libffitype = libffi.types.float

    def _unwrap_object(self, space, w_obj):
        return r_singlefloat(space.float_w(w_obj))

    def convert_argument(self, space, w_obj):
        x = lltype.malloc(rffi.FLOATP.TO, 1, flavor='raw')
        x[0] = self._unwrap_object(space, w_obj)
        return rffi.cast(rffi.VOIDP, x)

    def from_memory(self, space, w_obj, offset):
        address = self._get_raw_address(space, w_obj, offset)
        floatptr = rffi.cast(rffi.FLOATP, address)
        return space.wrap(float(floatptr[0]))

    def to_memory(self, space, w_obj, w_value, offset):
        address = self._get_raw_address(space, w_obj, offset)
        floatptr = rffi.cast(rffi.FLOATP, address)
        floatptr[0] = r_singlefloat(space.float_w(w_value))

class DoubleConverter(TypeConverter):
    _immutable = True
    libffitype = libffi.types.double

    def _unwrap_object(self, space, w_obj):
        return space.float_w(w_obj)

    def convert_argument(self, space, w_obj):
        x = lltype.malloc(rffi.DOUBLEP.TO, 1, flavor='raw')
        x[0] = self._unwrap_object(space, w_obj)
        return rffi.cast(rffi.VOIDP, x)

    def convert_argument_libffi(self, space, w_obj, argchain):
        argchain.arg(self._unwrap_object(space, w_obj))

    def from_memory(self, space, w_obj, offset):
        address = self._get_raw_address(space, w_obj, offset)
        doubleptr = rffi.cast(rffi.DOUBLEP, address)
        return space.wrap(doubleptr[0])

    def to_memory(self, space, w_obj, w_value, offset):
        address = self._get_raw_address(space, w_obj, offset)
        doubleptr = rffi.cast(rffi.DOUBLEP, address)
        doubleptr[0] = space.float_w(w_value)


class CStringConverter(TypeConverter):
    _immutable = True

    def convert_argument(self, space, w_obj):
        arg = space.str_w(w_obj)
        x = rffi.str2charp(arg)
        return rffi.cast(rffi.VOIDP, x)


class ShortArrayConverter(ArrayTypeConverter):
    _immutable_=True
    typecode = 'h'
    typesize = 2

class LongArrayConverter(ArrayTypeConverter):
    _immutable_=True
    typecode = 'l'
    typesize = 4

class FloatArrayConverter(ArrayTypeConverter):
    _immutable_=True
    typecode = 'f'
    typesize = 4

class DoubleArrayConverter(ArrayTypeConverter):
    _immutable_=True
    typecode = 'd'
    typesize = 8


class ShortPtrConverter(PtrTypeConverter):
    _immutable_=True
    typecode = 'h'
    typesize = 2

    def to_memory(self, space, w_obj, w_value, offset):
        # copy only the pointer value
        rawobject = get_rawobject(space, w_obj)
        byteptr = rffi.cast(rffi.LONGP, rawobject[offset])
        # TODO: now what ... ?? AFAICS, w_value is a pure python list, not an array?
#        byteptr[0] = space.unwrap(space.id(w_value.getslotvalue(2)))

class LongPtrConverter(PtrTypeConverter):
    _immutable_=True
    typecode = 'l'
    typesize = 4

class FloatPtrConverter(PtrTypeConverter):
    _immutable_=True
    typecode = 'f'
    typesize = 4

class DoublePtrConverter(PtrTypeConverter):
    _immutable_=True
    typecode = 'd'
    typesize = 8


class InstancePtrConverter(TypeConverter):
    _immutable_ = True
    _immutable_fields_ = ["cpptype"]

    def __init__(self, space, cpptype):
        self.cpptype = cpptype

    def convert_argument(self, space, w_obj):
        from pypy.module.cppyy.interp_cppyy import W_CPPInstance
        w_cppinstance = space.findattr(w_obj, space.wrap("_cppinstance"))
        if w_cppinstance:
            w_obj = w_cppinstance
        obj = space.interpclass_w(w_obj)
        if isinstance(obj, W_CPPInstance):
            if capi.c_is_subtype(obj.cppclass.handle, self.cpptype.handle):
                offset = capi.c_base_offset(obj.cppclass.handle, self.cpptype.handle)
                obj_address = lltype.direct_ptradd(obj.rawobject, offset)
                objptr = rffi.cast(rffi.VOIDP, obj_address)
                return objptr
        raise OperationError(space.w_TypeError,
                             space.wrap("cannot pass %s as %s" % (
                                 space.type(w_obj).getname(space, "?"),
                                 self.cpptype.name)))

    def free_argument(self, arg):
        pass

class InstanceConverter(InstancePtrConverter):
    _immutable_ = True

    def from_memory(self, space, w_obj, offset):
        address = self._get_raw_address(space, w_obj, offset)
        obj_address = rffi.cast(rffi.VOIDP, address)
        from pypy.module.cppyy import interp_cppyy
        return interp_cppyy.W_CPPInstance(space, self.cpptype, obj_address)

    def free_argument(self, arg):
        pass


_converters = {}
def get_converter(space, name):
    from pypy.module.cppyy import interp_cppyy
    # The matching of the name to a converter should follow:
    #   1) full, exact match
    #   2) match of decorated, unqualified type
    #   3) accept const ref as by value
    #   4) accept ref as pointer
    #   5) generalized cases (covers basically all user classes)
    #   6) void converter, which fails on use

    from pypy.module.cppyy import interp_cppyy

    #   1) full, exact match
    try:
        return _converters[name](space, -1)
    except KeyError, k:
        pass

    #   2) match of decorated, unqualified type
    compound = helper.compound(name)
    clean_name = helper.clean_type(name)
    try:
        # array_index may be negative to indicate no size or no size found
        array_size = helper.array_size(name)
        return _converters[clean_name+compound](space, array_size)
    except KeyError, k:
        pass

    #   3) accept const ref as by value
    if compound and compound[len(compound)-1] == "&":
        try:
            return _converters[clean_name](space, -1)
        except KeyError:
            pass

    #   5) generalized cases (covers basically all user classes)
    cpptype = interp_cppyy.type_byname(space, clean_name)
    if cpptype:
        # type check for the benefit of the annotator
        from pypy.module.cppyy.interp_cppyy import W_CPPType
        cpptype = space.interp_w(W_CPPType, cpptype, can_be_None=False)
        if compound == "*" or compound == "&":
            return InstancePtrConverter(space, cpptype)
        elif compound == "":
            return InstanceConverter(space, cpptype)
    
    #   6) void converter, which fails on use
    #
    # return a void converter here, so that the class can be build even
    # when some types are unknown; this overload will simply fail on use
    return VoidConverter(space, name)


_converters["bool"]                     = BoolConverter
_converters["char"]                     = CharConverter
_converters["unsigned char"]            = CharConverter
_converters["short int"]                = ShortConverter
_converters["short int*"]               = ShortPtrConverter
_converters["short int[]"]              = ShortArrayConverter
_converters["unsigned short int"]       = ShortConverter
_converters["unsigned short int*"]      = ShortPtrConverter
_converters["unsigned short int[]"]     = ShortArrayConverter
_converters["int"]                      = LongConverter
_converters["int*"]                     = LongPtrConverter
_converters["int[]"]                    = LongArrayConverter
_converters["unsigned int"]             = UnsignedLongConverter
_converters["unsigned int*"]            = LongPtrConverter
_converters["unsigned int[]"]           = LongArrayConverter
_converters["long int"]                 = LongConverter
_converters["long int*"]                = LongPtrConverter
_converters["long int[]"]               = LongArrayConverter
_converters["unsigned long int"]        = UnsignedLongConverter
_converters["unsigned long int*"]       = LongPtrConverter
_converters["unsigned long int[]"]      = LongArrayConverter
_converters["float"]                    = FloatConverter
_converters["float*"]                   = FloatPtrConverter
_converters["float[]"]                  = FloatArrayConverter
_converters["double"]                   = DoubleConverter
_converters["double*"]                  = DoublePtrConverter
_converters["double[]"]                 = DoubleArrayConverter
_converters["const char*"]              = CStringConverter

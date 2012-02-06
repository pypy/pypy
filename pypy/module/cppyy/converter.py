import sys

from pypy.interpreter.error import OperationError
from pypy.interpreter.buffer import Buffer
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib.rarithmetic import r_singlefloat
from pypy.rlib import jit, libffi, clibffi

from pypy.module._rawffi.interp_rawffi import unpack_simple_shape
from pypy.module._rawffi.array import W_Array

from pypy.module.cppyy import helper, capi


def get_rawobject(space, w_obj):
    from pypy.module.cppyy.interp_cppyy import W_CPPInstance
    cppinstance = space.interp_w(W_CPPInstance, w_obj, can_be_None=True)
    if cppinstance:
        assert lltype.typeOf(cppinstance.rawobject) == capi.C_OBJECT
        return cppinstance.rawobject
    return capi.C_NULL_OBJECT

def _direct_ptradd(ptr, offset):        # TODO: factor out with interp_cppyy.py
    assert lltype.typeOf(ptr) == capi.C_OBJECT
    address = rffi.cast(rffi.CCHARP, ptr)
    return rffi.cast(capi.C_OBJECT, lltype.direct_ptradd(address, offset))


class TypeConverter(object):
    _immutable_ = True
    libffitype = lltype.nullptr(clibffi.FFI_TYPE_P.TO)

    name = ""

    def __init__(self, space, extra):
        pass

    @jit.dont_look_inside
    def _get_raw_address(self, space, w_obj, offset):
        rawobject = get_rawobject(space, w_obj)
        assert lltype.typeOf(rawobject) == capi.C_OBJECT
        if rawobject:
            
            fieldptr = _direct_ptradd(rawobject, offset)
        else:
            fieldptr = rffi.cast(capi.C_OBJECT, offset)
        return fieldptr

    def _is_abstract(self, space):
        raise OperationError(space.w_NotImplementedError,
                             space.wrap("no converter available")) # more detailed part is not rpython: (actual: %s)" % type(self).__name__))

    def convert_argument(self, space, w_obj, address):
        self._is_abstract(space)

    def convert_argument_libffi(self, space, w_obj, argchain):
        from pypy.module.cppyy.interp_cppyy import FastCallNotPossible
        raise FastCallNotPossible

    def from_memory(self, space, w_obj, w_type, offset):
        self._is_abstract(space)

    def to_memory(self, space, w_obj, w_value, offset):
        self._is_abstract(space)

    def free_argument(self, arg):
        pass


class ArrayCache(object):
    def __init__(self, space):
        self.space = space
    def __getattr__(self, name):
        if name.startswith('array_'):
            typecode = name[len('array_'):]
            arr = self.space.interp_w(W_Array, unpack_simple_shape(self.space, self.space.wrap(typecode)))
            setattr(self, name, arr)
            return arr
        raise AttributeError(name)

    def _freeze_(self):
        return True

class ArrayTypeConverterMixin(object):
    _mixin_ = True
    _immutable_ = True

    def __init__(self, space, array_size):
        if array_size <= 0:
            self.size = sys.maxint
        else:
            self.size = array_size

    def from_memory(self, space, w_obj, w_type, offset):
        if hasattr(space, "fake"):
            raise NotImplementedError
        # read access, so no copy needed
        address_value = self._get_raw_address(space, w_obj, offset)
        address = rffi.cast(rffi.ULONG, address_value)
        cache = space.fromcache(ArrayCache)
        arr = getattr(cache, 'array_' + self.typecode)
        return arr.fromaddress(space, address, self.size)

    def to_memory(self, space, w_obj, w_value, offset):
        # copy the full array (uses byte copy for now)
        address = rffi.cast(rffi.CCHARP, self._get_raw_address(space, w_obj, offset))
        buf = space.buffer_w(w_value)
        # TODO: report if too many items given?
        for i in range(min(self.size*self.typesize, buf.getlength())):
            address[i] = buf.getitem(i)


class PtrTypeConverterMixin(object):
    _mixin_ = True
    _immutable_ = True

    def __init__(self, space, array_size):
        self.size = sys.maxint

    def from_memory(self, space, w_obj, w_type, offset):
        # read access, so no copy needed
        address_value = self._get_raw_address(space, w_obj, offset)
        address = rffi.cast(rffi.ULONGP, address_value)
        cache = space.fromcache(ArrayCache)
        arr = getattr(cache, 'array_' + self.typecode)
        return arr.fromaddress(space, address[0], self.size)

    def to_memory(self, space, w_obj, w_value, offset):
        # copy only the pointer value
        rawobject = get_rawobject(space, w_obj)
        byteptr = rffi.cast(rffi.CCHARPP, _direct_ptradd(rawobject, offset))
        buf = space.buffer_w(w_value)
        try:
            byteptr[0] = buf.get_raw_address()
        except ValueError:
            raise OperationError(space.w_TypeError,
                                 space.wrap("raw buffer interface not supported"))


class IntTypeConverterMixin(object):
    _mixin_ = True
    _immutable_ = True
    
    def __init__(self, space, default):
        self.default = rffi.cast(self.rffitype, capi.c_strtoll(default))

    def convert_argument(self, space, w_obj, address):
        x = rffi.cast(self.rffiptype, address)
        x[0] = self._unwrap_object(space, w_obj)

    def convert_argument_libffi(self, space, w_obj, argchain):
        argchain.arg(self._unwrap_object(space, w_obj))

    def default_argument_libffi(self, space, argchain):
        argchain.arg(self.default)

    def from_memory(self, space, w_obj, w_type, offset):
        address = self._get_raw_address(space, w_obj, offset)
        intptr = rffi.cast(self.rffiptype, address)
        return space.wrap(intptr[0])

    def to_memory(self, space, w_obj, w_value, offset):
        address = self._get_raw_address(space, w_obj, offset)
        intptr = rffi.cast(self.rffiptype, address)
        intptr[0] = self._unwrap_object(space, w_value)


class VoidConverter(TypeConverter):
    _immutable_ = True
    libffitype = libffi.types.void

    def __init__(self, space, name):
        self.name = name

    def convert_argument(self, space, w_obj, address):
        raise OperationError(space.w_NotImplementedError,
                             space.wrap('no converter available for type "%s"' % self.name))


class BoolConverter(TypeConverter):
    _immutable_ = True
    libffitype = libffi.types.schar

    def _unwrap_object(self, space, w_obj):
        arg = space.c_int_w(w_obj)
        if arg != False and arg != True:
            raise OperationError(space.w_TypeError,
                                 space.wrap("boolean value should be bool, or integer 1 or 0"))
        return arg

    def convert_argument(self, space, w_obj, address):
        x = rffi.cast(rffi.LONGP, address)
        x[0] = self._unwrap_object(space, w_obj)

    def convert_argument_libffi(self, space, w_obj, argchain):
        argchain.arg(self._unwrap_object(space, w_obj))

    def from_memory(self, space, w_obj, w_type, offset):
        address = rffi.cast(rffi.CCHARP, self._get_raw_address(space, w_obj, offset))
        if address[0] == '\x01':
            return space.w_True
        return space.w_False

    def to_memory(self, space, w_obj, w_value, offset):
        address = rffi.cast(rffi.CCHARP, self._get_raw_address(space, w_obj, offset))
        arg = self._unwrap_object(space, w_value)
        if arg:
            address[0] = '\x01'
        else:
            address[0] = '\x00'

class CharConverter(TypeConverter):
    _immutable_ = True
    libffitype = libffi.types.schar

    def _unwrap_object(self, space, w_value):
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

    def convert_argument(self, space, w_obj, address):
        x = rffi.cast(rffi.CCHARP, address)
        x[0] = self._unwrap_object(space, w_obj)

    def convert_argument_libffi(self, space, w_obj, argchain): 
        argchain.arg(self._unwrap_object(space, w_obj))

    def from_memory(self, space, w_obj, w_type, offset):
        address = rffi.cast(rffi.CCHARP, self._get_raw_address(space, w_obj, offset))
        return space.wrap(address[0])

    def to_memory(self, space, w_obj, w_value, offset):
        address = rffi.cast(rffi.CCHARP, self._get_raw_address(space, w_obj, offset))
        address[0] = self._unwrap_object(space, w_value)

class IntConverter(IntTypeConverterMixin, TypeConverter):
    _immutable_ = True
    libffitype = libffi.types.sint
    rffitype = rffi.INT
    rffiptype = rffi.INTP

    def _unwrap_object(self, space, w_obj):
        return rffi.cast(rffi.INT, space.c_int_w(w_obj))

class UnsignedIntConverter(TypeConverter):
    _immutable_ = True
    libffitype = libffi.types.uint

    def _unwrap_object(self, space, w_obj):
        return rffi.cast(rffi.UINT, space.uint_w(w_obj))

    def convert_argument(self, space, w_obj, address):
        x = rffi.cast(rffi.UINTP, address)
        x[0] = self._unwrap_object(space, w_obj)

    def convert_argument_libffi(self, space, w_obj, argchain):
        argchain.arg(self._unwrap_object(space, w_obj))

    def from_memory(self, space, w_obj, w_type, offset):
        address = self._get_raw_address(space, w_obj, offset)
        ulongptr = rffi.cast(rffi.UINTP, address)
        return space.wrap(ulongptr[0])

    def to_memory(self, space, w_obj, w_value, offset):
        address = self._get_raw_address(space, w_obj, offset)
        ulongptr = rffi.cast(rffi.UINTP, address)
        ulongptr[0] = self._unwrap_object(space, w_value)

class LongConverter(IntTypeConverterMixin, TypeConverter):
    _immutable_ = True
    libffitype = libffi.types.slong
    rffitype = rffi.LONG
    rffiptype = rffi.LONGP

    def _unwrap_object(self, space, w_obj):
        return space.int_w(w_obj)

class UnsignedLongConverter(TypeConverter):
    _immutable_ = True
    libffitype = libffi.types.ulong

    def _unwrap_object(self, space, w_obj):
        return space.uint_w(w_obj)

    def convert_argument(self, space, w_obj, address):
        x = rffi.cast(rffi.ULONGP, address)
        x[0] = self._unwrap_object(space, w_obj)

    def convert_argument_libffi(self, space, w_obj, argchain):
        argchain.arg(self._unwrap_object(space, w_obj))

    def from_memory(self, space, w_obj, w_type, offset):
        address = self._get_raw_address(space, w_obj, offset)
        ulongptr = rffi.cast(rffi.ULONGP, address)
        return space.wrap(ulongptr[0])

    def to_memory(self, space, w_obj, w_value, offset):
        address = self._get_raw_address(space, w_obj, offset)
        ulongptr = rffi.cast(rffi.ULONGP, address)
        ulongptr[0] = self._unwrap_object(space, w_value)

class ShortConverter(TypeConverter):
    _immutable_ = True
    libffitype = libffi.types.sshort

    def _unwrap_object(self, space, w_obj):
        return rffi.cast(rffi.SHORT, space.int_w(w_obj))

    def convert_argument(self, space, w_obj, address):
        x = rffi.cast(rffi.SHORTP, address)
        x[0] = self._unwrap_object(space, w_obj)

    def convert_argument_libffi(self, space, w_obj, argchain):
        argchain.arg(self._unwrap_object(space, w_obj))

    def from_memory(self, space, w_obj, w_type, offset):
        address = self._get_raw_address(space, w_obj, offset)
        shortptr = rffi.cast(rffi.SHORTP, address)
        return space.wrap(shortptr[0])

    def to_memory(self, space, w_obj, w_value, offset):
        address = self._get_raw_address(space, w_obj, offset)
        shortptr = rffi.cast(rffi.SHORTP, address)
        shortptr[0] = self._unwrap_object(space, w_value)

class FloatConverter(TypeConverter):
    _immutable_ = True
    libffitype = libffi.types.float

    def _unwrap_object(self, space, w_obj):
        return r_singlefloat(space.float_w(w_obj))

    def convert_argument(self, space, w_obj, address):
        x = rffi.cast(rffi.FLOATP, address)
        x[0] = self._unwrap_object(space, w_obj)
        typecode = rffi.cast(rffi.CCHARP,
            _direct_ptradd(address, capi.c_function_arg_typeoffset()))
        typecode[0] = 'f'

    def convert_argument_libffi(self, space, w_obj, argchain):
        from pypy.rlib.rarithmetic import r_singlefloat
        fval = space.float_w(w_obj)
        sfval = r_singlefloat(fval)
        argchain.arg(sfval)

    def from_memory(self, space, w_obj, w_type, offset):
        address = self._get_raw_address(space, w_obj, offset)
        floatptr = rffi.cast(rffi.FLOATP, address)
        return space.wrap(float(floatptr[0]))

    def to_memory(self, space, w_obj, w_value, offset):
        address = self._get_raw_address(space, w_obj, offset)
        floatptr = rffi.cast(rffi.FLOATP, address)
        floatptr[0] = self._unwrap_object(space, w_value)

class DoubleConverter(TypeConverter):
    _immutable_ = True
    libffitype = libffi.types.double

    def _unwrap_object(self, space, w_obj):
        return space.float_w(w_obj)

    def convert_argument(self, space, w_obj, address):
        x = rffi.cast(rffi.DOUBLEP, address)
        x[0] = self._unwrap_object(space, w_obj)
        typecode = rffi.cast(rffi.CCHARP,
            _direct_ptradd(address, capi.c_function_arg_typeoffset()))
        typecode[0] = 'd'

    def convert_argument_libffi(self, space, w_obj, argchain):
        argchain.arg(self._unwrap_object(space, w_obj))

    def from_memory(self, space, w_obj, w_type, offset):
        address = self._get_raw_address(space, w_obj, offset)
        doubleptr = rffi.cast(rffi.DOUBLEP, address)
        return space.wrap(doubleptr[0])

    def to_memory(self, space, w_obj, w_value, offset):
        address = self._get_raw_address(space, w_obj, offset)
        doubleptr = rffi.cast(rffi.DOUBLEP, address)
        doubleptr[0] = self._unwrap_object(space, w_value)


class CStringConverter(TypeConverter):
    _immutable_ = True

    def convert_argument(self, space, w_obj, address):
        x = rffi.cast(rffi.LONGP, address)
        arg = space.str_w(w_obj)
        x[0] = rffi.cast(rffi.LONG, rffi.str2charp(arg))
        typecode = rffi.cast(rffi.CCHARP,
            _direct_ptradd(address, capi.c_function_arg_typeoffset()))
        typecode[0] = 'a'

    def from_memory(self, space, w_obj, w_type, offset):
        address = self._get_raw_address(space, w_obj, offset)
        charpptr = rffi.cast(rffi.CCHARPP, address)
        return space.wrap(rffi.charp2str(charpptr[0]))

    def free_argument(self, arg):
        lltype.free(rffi.cast(rffi.CCHARPP, arg)[0], flavor='raw')


class VoidPtrConverter(TypeConverter):
    _immutable_ = True

    def convert_argument(self, space, w_obj, address):
        x = rffi.cast(rffi.VOIDPP, address)
        x[0] = rffi.cast(rffi.VOIDP, get_rawobject(space, w_obj))
        typecode = rffi.cast(rffi.CCHARP,
           _direct_ptradd(address, capi.c_function_arg_typeoffset()))
        typecode[0] = 'a'

    def convert_argument_libffi(self, space, w_obj, argchain):
        argchain.arg(get_rawobject(space, w_obj))


class VoidPtrPtrConverter(TypeConverter):
    _immutable_ = True

    def convert_argument(self, space, w_obj, address):
        x = rffi.cast(rffi.VOIDPP, address)
        x[0] = rffi.cast(rffi.VOIDP, get_rawobject(space, w_obj))
        typecode = rffi.cast(rffi.CCHARP,
            _direct_ptradd(address, capi.c_function_arg_typeoffset()))
        typecode[0] = 'p'


class VoidPtrRefConverter(TypeConverter):
    _immutable_ = True

    def convert_argument(self, space, w_obj, address):
        x = rffi.cast(rffi.VOIDPP, address)
        x[0] = rffi.cast(rffi.VOIDP, get_rawobject(space, w_obj))
        typecode = rffi.cast(rffi.CCHARP,
            _direct_ptradd(address, capi.c_function_arg_typeoffset()))
        typecode[0] = 'r'


class ShortArrayConverter(ArrayTypeConverterMixin, TypeConverter):
    _immutable_ = True
    typecode = 'h'
    typesize = rffi.sizeof(rffi.SHORT)

class IntArrayConverter(ArrayTypeConverterMixin, TypeConverter):
    _immutable_ = True
    typecode = 'i'
    typesize = rffi.sizeof(rffi.INT)

class UnsignedIntArrayConverter(ArrayTypeConverterMixin, TypeConverter):
    _immutable_ = True
    typecode = 'I'
    typesize = rffi.sizeof(rffi.UINT)

class LongArrayConverter(ArrayTypeConverterMixin, TypeConverter):
    _immutable_ = True
    typecode = 'l'
    typesize = rffi.sizeof(rffi.LONG)

class FloatArrayConverter(ArrayTypeConverterMixin, TypeConverter):
    _immutable_ = True
    typecode = 'f'
    typesize = rffi.sizeof(rffi.FLOAT)

class DoubleArrayConverter(ArrayTypeConverterMixin, TypeConverter):
    _immutable_ = True
    typecode = 'd'
    typesize = rffi.sizeof(rffi.DOUBLE)


class ShortPtrConverter(PtrTypeConverterMixin, TypeConverter):
    _immutable_ = True
    typecode = 'h'
    typesize = rffi.sizeof(rffi.SHORT)

class IntPtrConverter(PtrTypeConverterMixin, TypeConverter):
    _immutable_ = True
    typecode = 'i'
    typesize = rffi.sizeof(rffi.INT)

class UnsignedIntPtrConverter(PtrTypeConverterMixin, TypeConverter):
    _immutable_ = True
    typecode = 'I'
    typesize = rffi.sizeof(rffi.UINT)

class LongPtrConverter(PtrTypeConverterMixin, TypeConverter):
    _immutable_ = True
    typecode = 'l'
    typesize = rffi.sizeof(rffi.LONG)

class FloatPtrConverter(PtrTypeConverterMixin, TypeConverter):
    _immutable_ = True
    typecode = 'f'
    typesize = rffi.sizeof(rffi.FLOAT)

class DoublePtrConverter(PtrTypeConverterMixin, TypeConverter):
    _immutable_ = True
    typecode = 'd'
    typesize = rffi.sizeof(rffi.DOUBLE)


class InstancePtrConverter(TypeConverter):
    _immutable_ = True

    def __init__(self, space, cpptype, name):
        self.cpptype = cpptype
        self.name = name

    def _unwrap_object(self, space, w_obj):
        from pypy.module.cppyy.interp_cppyy import W_CPPInstance
        w_cppinstance = space.findattr(w_obj, space.wrap("_cppinstance"))
        if w_cppinstance:
            w_obj = w_cppinstance
        obj = space.interpclass_w(w_obj)
        if isinstance(obj, W_CPPInstance):
            if capi.c_is_subtype(obj.cppclass.handle, self.cpptype.handle):
                offset = capi.c_base_offset(
                    obj.cppclass.handle, self.cpptype.handle, obj.rawobject)
                obj_address = _direct_ptradd(obj.rawobject, offset)
                return rffi.cast(capi.C_OBJECT, obj_address)
        raise OperationError(space.w_TypeError,
                             space.wrap("cannot pass %s as %s" % (
                                 space.type(w_obj).getname(space, "?"),
                                 self.cpptype.name)))

    def convert_argument(self, space, w_obj, address):
        x = rffi.cast(rffi.VOIDPP, address)
        x[0] = rffi.cast(rffi.VOIDP, self._unwrap_object(space, w_obj))
        address = rffi.cast(capi.C_OBJECT, address)
        typecode = rffi.cast(rffi.CCHARP,
            _direct_ptradd(address, capi.c_function_arg_typeoffset()))
        typecode[0] = 'o'

    def convert_argument_libffi(self, space, w_obj, argchain):
        argchain.arg(self._unwrap_object(space, w_obj))


class InstanceConverter(InstancePtrConverter):
    _immutable_ = True

    def from_memory(self, space, w_obj, w_type, offset):
        address = rffi.cast(capi.C_OBJECT, self._get_raw_address(space, w_obj, offset))
        from pypy.module.cppyy import interp_cppyy
        return interp_cppyy.new_instance(space, w_type, self.cpptype, address, False)


_converters = {}         # builtin and custom types
_a_converters = {}       # array and ptr versions of above
def get_converter(space, name, default):
    from pypy.module.cppyy import interp_cppyy
    # The matching of the name to a converter should follow:
    #   1) full, exact match
    #       1a) const-removed match
    #   2) match of decorated, unqualified type
    #   3) accept const ref as by value
    #   4) accept ref as pointer
    #   5) generalized cases (covers basically all user classes)
    #   6) void converter, which fails on use

    from pypy.module.cppyy import interp_cppyy

    #   1) full, exact match
    try:
        return _converters[name](space, default)
    except KeyError, k:
        pass

    #   1a) const-removed match
    try:
        return _converters[helper.remove_const(name)](space, default)
    except KeyError, k:
        pass

    #   2) match of decorated, unqualified type
    compound = helper.compound(name)
    clean_name = helper.clean_type(name)
    try:
        # array_index may be negative to indicate no size or no size found
        array_size = helper.array_size(name)
        return _a_converters[clean_name+compound](space, array_size)
    except KeyError, k:
        pass

    #   3) accept const ref as by value
    if compound and compound[len(compound)-1] == "&":
        try:
            return _converters[clean_name](space, default)
        except KeyError:
            pass

    #   5) generalized cases (covers basically all user classes)
    cpptype = interp_cppyy.type_byname(space, clean_name)
    if cpptype:
        # type check for the benefit of the annotator
        from pypy.module.cppyy.interp_cppyy import W_CPPType
        cpptype = space.interp_w(W_CPPType, cpptype, can_be_None=False)
        if compound == "*" or compound == "&":
            return InstancePtrConverter(space, cpptype, clean_name)
        elif compound == "":
            return InstanceConverter(space, cpptype, clean_name)
    
    #   6) void converter, which fails on use
    #
    # return a void converter here, so that the class can be build even
    # when some types are unknown; this overload will simply fail on use
    return VoidConverter(space, name)


_converters["bool"]                     = BoolConverter
_converters["char"]                     = CharConverter
_converters["unsigned char"]            = CharConverter
_converters["short int"]                = ShortConverter
_converters["short"]                    = _converters["short int"]
_converters["unsigned short int"]       = ShortConverter
_converters["unsigned short"]           = _converters["unsigned short int"]
_converters["int"]                      = IntConverter
_converters["unsigned int"]             = UnsignedIntConverter
_converters["long int"]                 = LongConverter
_converters["long"]                     = _converters["long int"]
_converters["unsigned long int"]        = UnsignedLongConverter
_converters["unsigned long"]            = _converters["unsigned long int"]
_converters["float"]                    = FloatConverter
_converters["double"]                   = DoubleConverter
_converters["const char*"]              = CStringConverter
_converters["char*"]                    = CStringConverter
_converters["void*"]                    = VoidPtrConverter
_converters["void**"]                   = VoidPtrPtrConverter
_converters["void*&"]                   = VoidPtrRefConverter

# it should be possible to generate these:
_a_converters["short int*"]               = ShortPtrConverter
_a_converters["short*"]                   = _a_converters["short int*"]
_a_converters["short int[]"]              = ShortArrayConverter
_a_converters["short[]"]                  = _a_converters["short int[]"]
_a_converters["unsigned short int*"]      = ShortPtrConverter
_a_converters["unsigned short*"]          = _a_converters["unsigned short int*"]
_a_converters["unsigned short int[]"]     = ShortArrayConverter
_a_converters["unsigned short[]"]         = _a_converters["unsigned short int[]"]
_a_converters["int*"]                     = IntPtrConverter
_a_converters["int[]"]                    = IntArrayConverter
_a_converters["unsigned int*"]            = UnsignedIntPtrConverter
_a_converters["unsigned int[]"]           = UnsignedIntArrayConverter
_a_converters["long int*"]                = LongPtrConverter
_a_converters["long*"]                    = _a_converters["long int*"]
_a_converters["long int[]"]               = LongArrayConverter
_a_converters["long[]"]                   = _a_converters["long int[]"]
_a_converters["unsigned long int*"]       = LongPtrConverter
_a_converters["unsigned long*"]           = _a_converters["unsigned long int*"]
_a_converters["unsigned long int[]"]      = LongArrayConverter
_a_converters["unsigned long[]"]          = _a_converters["unsigned long int[]"]
_a_converters["float*"]                   = FloatPtrConverter
_a_converters["float[]"]                  = FloatArrayConverter
_a_converters["double*"]                  = DoublePtrConverter
_a_converters["double[]"]                 = DoubleArrayConverter

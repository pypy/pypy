import sys
from pypy.interpreter.error import OperationError
from pypy.interpreter.buffer import Buffer
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib.rarithmetic import r_singlefloat
from pypy.rlib import jit

from pypy.module._rawffi.interp_rawffi import unpack_simple_shape
from pypy.module._rawffi.array import W_Array

from pypy.module.cppyy import helper, capi

_converters = {}

def get_rawobject(space, w_obj):
    from pypy.module.cppyy.interp_cppyy import W_CPPInstance
    w_obj = space.findattr(w_obj, space.wrap("_cppinstance"))
    obj = space.interp_w(W_CPPInstance, w_obj, can_be_None=True)
    return obj.rawobject


class TypeConverter(object):
    def __init__(self, space, array_size):
        pass

    @jit.dont_look_inside
    def _get_fieldptr(self, space, w_obj, offset):
        rawobject = get_rawobject(space, w_obj)
        return lltype.direct_ptradd(rawobject, offset)

    def _is_abstract(self):
        raise NotImplementedError(
            "abstract base class" ) # more detailed part is not rpython: (actual: %s)" % type(self).__name__)

    def convert_argument(self, space, w_obj):
        self._is_abstract()

    def from_memory(self, space, w_obj, offset):
        self._is_abstract()

    def to_memory(self, space, w_obj, w_value, offset):
        self._is_abstract()

    def free_argument(self, arg):
        lltype.free(arg, flavor='raw')


class ArrayTypeConverter(TypeConverter):
    _immutable_ = True
    def __init__(self, space, array_size):
        if array_size <= 0:
            self.size = sys.maxint
        else:
            self.size = array_size


class VoidConverter(TypeConverter):
    def __init__(self, space, name):
        self.name = name

    def convert_argument(self, space, w_obj):
        raise OperationError(space.w_TypeError,
                             space.wrap('no converter available for type "%s"' % self.name))


class BoolConverter(TypeConverter):
    def convert_argument(self, space, w_obj):
        arg = space.c_int_w(w_obj)
        if arg != False and arg != True:
            raise OperationError(space.w_TypeError,
                                 space.wrap("boolean value should be bool, or integer 1 or 0"))
        x = lltype.malloc(rffi.LONGP.TO, 1, flavor='raw')
        x[0] = arg
        return rffi.cast(rffi.VOIDP, x)

    def from_memory(self, space, w_obj, offset):
        fieldptr = self._get_fieldptr(space, w_obj, offset)
        if fieldptr[0] == '\x01':
            return space.wrap(True)
        return space.wrap(False)

    def to_memory(self, space, w_obj, w_value, offset):
        fieldptr = self._get_fieldptr(space, w_obj, offset)
        arg = space.c_int_w(w_value)
        if arg != False and arg != True:
            raise OperationError(space.w_TypeError,
                                 space.wrap("boolean value should be bool, or integer 1 or 0"))
        if arg:
           fieldptr[0] = '\x01'
        else:
           fieldptr[0] = '\x00'

class CharConverter(TypeConverter):
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
        fieldptr = self._get_fieldptr(space, w_obj, offset)
        return space.wrap(fieldptr[0])

    def to_memory(self, space, w_obj, w_value, offset):
        fieldptr = self._get_fieldptr(space, w_obj, offset)
        fieldptr[0] = self._from_space(space, w_value)

class LongConverter(TypeConverter):
    def convert_argument(self, space, w_obj):
        arg = space.c_int_w(w_obj)
        x = lltype.malloc(rffi.LONGP.TO, 1, flavor='raw')
        x[0] = arg
        return rffi.cast(rffi.VOIDP, x)

    def from_memory(self, space, w_obj, offset):
        fieldptr = self._get_fieldptr(space, w_obj, offset)
        longptr = rffi.cast(rffi.LONGP, fieldptr)
        return space.wrap(longptr[0])

    def to_memory(self, space, w_obj, w_value, offset):
        fieldptr = self._get_fieldptr(space, w_obj, offset)
        longptr = rffi.cast(rffi.LONGP, fieldptr)
        longptr[0] = space.c_int_w(w_value)

class ShortConverter(LongConverter):
    def from_memory(self, space, w_obj, offset):
        fieldptr = self._get_fieldptr(space, w_obj, offset)
        shortptr = rffi.cast(rffi.SHORTP, fieldptr)
        return space.wrap(shortptr[0])

    def to_memory(self, space, w_obj, w_value, offset):
        fieldptr = self._get_fieldptr(space, w_obj, offset)
        shortptr = rffi.cast(rffi.SHORTP, fieldptr)
        shortptr[0] = rffi.cast(rffi.SHORT, space.c_int_w(w_value))

class FloatConverter(TypeConverter):
    def convert_argument(self, space, w_obj):
        arg = space.float_w(w_obj)
        x = lltype.malloc(rffi.FLOATP.TO, 1, flavor='raw')
        x[0] = r_singlefloat(arg)
        return rffi.cast(rffi.VOIDP, x)        

    def from_memory(self, space, w_obj, offset):
        fieldptr = self._get_fieldptr(space, w_obj, offset)
        floatptr = rffi.cast(rffi.FLOATP, fieldptr)
        return space.wrap(float(floatptr[0]))

    def to_memory(self, space, w_obj, w_value, offset):
        fieldptr = self._get_fieldptr(space, w_obj, offset)
        floatptr = rffi.cast(rffi.FLOATP, fieldptr)
        floatptr[0] = r_singlefloat(space.float_w(w_value))

class DoubleConverter(TypeConverter):
    def convert_argument(self, space, w_obj):
        arg = space.float_w(w_obj)
        x = lltype.malloc(rffi.DOUBLEP.TO, 1, flavor='raw')
        x[0] = arg
        return rffi.cast(rffi.VOIDP, x)        

    def from_memory(self, space, w_obj, offset):
        fieldptr = self._get_fieldptr(space, w_obj, offset)
        doubleptr = rffi.cast(rffi.DOUBLEP, fieldptr)
        return space.wrap(doubleptr[0])

    def to_memory(self, space, w_obj, w_value, offset):
        fieldptr = self._get_fieldptr(space, w_obj, offset)
        doubleptr = rffi.cast(rffi.DOUBLEP, fieldptr)
        doubleptr[0] = space.float_w(w_value)


class CStringConverter(TypeConverter):
    def convert_argument(self, space, w_obj):
        arg = space.str_w(w_obj)
        x = rffi.str2charp(arg)
        return rffi.cast(rffi.VOIDP, x)


class ShortPtrConverter(ArrayTypeConverter):
    _immutable_ = True
    def convert_argument(self, space, w_obj):
        assert 0, "not yet implemented"

    def from_memory(self, space, w_obj, offset):
        # read access, so no copy needed
        fieldptr = self._get_fieldptr(space, w_obj, offset)
        ptrval = rffi.cast(rffi.UINT, fieldptr)
        arr = space.interp_w(W_Array, unpack_simple_shape(space, space.wrap('h')))
        return arr.fromaddress(space, ptrval, self.size)

    def to_memory(self, space, w_obj, w_value, offset):
        # copy only the pointer value
        rawobject = get_rawobject(space, w_obj)
        byteptr = rffi.cast(rffi.LONGP, rawobject[offset])
        # TODO: now what ... ?? AFAICS, w_value is a pure python list, not an array?
#        byteptr[0] = space.unwrap(space.id(w_value.getslotvalue(2)))

class ShortArrayConverter(ShortPtrConverter):
    _immutable_ = True
    def to_memory(self, space, w_obj, w_value, offset):
        # copy the full array (uses byte copy for now)
        fieldptr = self._get_fieldptr(space, w_obj, offset)
        buf = space.interp_w(Buffer, w_value.getslotvalue(2))
        # TODO: get sizeof(short) from system
        for i in range(min(self.size*2, buf.getlength())):
            fieldptr[i] = buf.getitem(i)

class LongPtrConverter(ArrayTypeConverter):
    _immutable_ = True
    def convert_argument(self, space, w_obj):
        assert 0, "not yet implemented"

    def from_memory(self, space, w_obj, offset):
        # read access, so no copy needed
        fieldptr = self._get_fieldptr(space, w_obj, offset)
        ptrval = rffi.cast(rffi.UINT, fieldptr)
        arr = space.interp_w(W_Array, unpack_simple_shape(space, space.wrap('l')))
        return arr.fromaddress(space, ptrval, self.size)

    def to_memory(self, space, w_obj, w_value, offset):
        # copy only the pointer value
        rawobject = get_rawobject(space, w_obj)
        byteptr = rffi.cast(rffi.LONGP, rawobject[offset])
        # TODO: now what ... ?? AFAICS, w_value is a pure python list, not an array?
#        byteptr[0] = space.unwrap(space.id(w_value.getslotvalue(2)))

class LongArrayConverter(LongPtrConverter):
    _immutable_ = True
    def to_memory(self, space, w_obj, w_value, offset):
        # copy the full array (uses byte copy for now)
        fieldptr = self._get_fieldptr(space, w_obj, offset)
        buf = space.interp_w(Buffer, w_value.getslotvalue(2))
        # TODO: get sizeof(long) from system
        for i in range(min(self.size*4, buf.getlength())):
            fieldptr[i] = buf.getitem(i)


class InstancePtrConverter(TypeConverter):
    _immutable_ = True
    def __init__(self, space, cpptype):
        self.cpptype = cpptype

    def convert_argument(self, space, w_obj):
        from pypy.module.cppyy import interp_cppyy
        w_cppinstance = space.findattr(w_obj, space.wrap("_cppinstance"))
        if w_cppinstance is not None:
            w_obj = w_cppinstance
        obj = space.interpclass_w(w_obj)
        if isinstance(obj, interp_cppyy.W_CPPInstance):
            if capi.c_is_subtype(obj.cppclass.handle, self.cpptype.handle):
                return obj.rawobject
        raise OperationError(space.w_TypeError,
                             space.wrap("cannot pass %s as %s" % (
                                 space.type(w_obj).getname(space, "?"),
                                 self.cpptype.name)))

    def free_argument(self, arg):
        pass
        

def get_converter(space, name):
    from pypy.module.cppyy import interp_cppyy
    # The matching of the name to a converter should follow:
    #   1) full, exact match
    #   2) match of decorated, unqualified type
    #   3) accept const ref as by value
    #   4) accept ref as pointer
    #   5) generalized cases (covers basically all user classes)
    #   6) void converter, which fails on use

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

    #   5) generalized cases (covers basically all user classes)
    cpptype = interp_cppyy.type_byname(space, clean_name)
    if compound == "*":
        return InstancePtrConverter(space, cpptype)

    
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
_converters["unsigned int"]             = LongConverter
_converters["unsigned int*"]            = LongPtrConverter
_converters["unsigned int[]"]           = LongArrayConverter
_converters["long int"]                 = LongConverter
_converters["long int*"]                = LongPtrConverter
_converters["long int[]"]               = LongArrayConverter
_converters["unsigned long int"]        = LongConverter
_converters["unsigned long int*"]       = LongPtrConverter
_converters["unsigned long int[]"]      = LongArrayConverter
_converters["float"]                    = FloatConverter
_converters["double"]                   = DoubleConverter
_converters["const char*"]              = CStringConverter

from pypy.rlib.rctypes.implementation import CTypeController
from pypy.rlib.rctypes import rctypesobject
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rctypes import rcarithmetic as rcarith

from ctypes import c_char, c_byte, c_ubyte, c_short, c_ushort, c_int, c_uint
from ctypes import c_long, c_ulong, c_longlong, c_ulonglong, c_float
from ctypes import c_double, c_wchar, c_char_p


ctypes_annotation_list = {
    c_char:          lltype.Char,
    #c_wchar:         lltype.UniChar,
    c_byte:          rcarith.CByte,
    c_ubyte:         rcarith.CUByte,
    c_short:         rcarith.CShort,
    c_ushort:        rcarith.CUShort,
    c_int:           rcarith.CInt,
    c_uint:          rcarith.CUInt,
    c_long:          rcarith.CLong,
    c_ulong:         rcarith.CULong,
    c_longlong:      rcarith.CLonglong,
    c_ulonglong:     rcarith.CULonglong,
    #c_float:         lltype.Float,
    c_double:        lltype.Float,
}   # nb. platform-dependent duplicate ctypes are removed

def return_lltype(ll_type):
    if isinstance(ll_type, lltype.Number):
        return ll_type.normalized()
    return ll_type


class PrimitiveCTypeController(CTypeController):

    def __init__(self, ctype):
        CTypeController.__init__(self, ctype)
        self.VALUETYPE = ctypes_annotation_list[ctype]
        self.RETTYPE   = return_lltype(self.VALUETYPE)
        self.is_char_type = self.VALUETYPE in (lltype.Char, lltype.UniChar)
        self.knowntype = rctypesobject.Primitive(self.VALUETYPE)

        def primitivenew(*initialvalue):
            obj = self.knowntype.allocate()
            if len(initialvalue) > 0:
                if len(initialvalue) > 1:
                    raise TypeError("at most 1 argument expected")
                self.set_value(obj, initialvalue[0])
            return obj
        self.new = primitivenew

    def initialize_prebuilt(self, obj, x):
        value = x.value
        # convert 'value' to anything that cast_primitive will be happy with
        if type(value) is long:
            if value >= 0:
                value = rcarith.rculonglong(value)
            else:
                value = rcarith.rclonglong(value)
        self.set_value(obj, value)

    def get_value(self, obj):
        llvalue = obj.get_value()
        return lltype.cast_primitive(self.RETTYPE, llvalue)
    get_value._annspecialcase_ = 'specialize:arg(0)'

    def set_value(self, obj, value):
        # for integer and float types, any integer is accepted and silently
        # cast.  For char types, do a precise check
        if self.is_char_type:
            if lltype.typeOf(value) != self.RETTYPE:
                raise TypeError("'value' must be set to a %s" % (
                    self.RETTYPE,))
        llvalue = lltype.cast_primitive(self.VALUETYPE, value)
        obj.set_value(llvalue)
    set_value._annspecialcase_ = 'specialize:arg(0)'

    # ctypes automatically unwraps the c_xxx() of primitive types when
    # they are returned by most operations
    return_value = get_value
    store_value = set_value

    def default_ctype_value(self):
        return self.ctype().value

    def is_true(self, obj):
        llvalue = self.get_value(obj)
        if self.is_char_type:
            llvalue = ord(llvalue)
        return bool(llvalue)
    is_true._annspecialcase_ = 'specialize:arg(0)'


for _ctype in ctypes_annotation_list:
    PrimitiveCTypeController.register_for_type(_ctype)

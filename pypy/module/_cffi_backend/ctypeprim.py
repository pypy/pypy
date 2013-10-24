"""
Primitives.
"""

from pypy.interpreter.error import operationerrfmt

from rpython.rlib.rarithmetic import r_uint, r_ulonglong, intmask
from rpython.rlib.objectmodel import keepalive_until_here
from rpython.rlib import jit
from rpython.rtyper.lltypesystem import lltype, rffi

from pypy.module._cffi_backend import cdataobj, misc
from pypy.module._cffi_backend.ctypeobj import W_CType


class W_CTypePrimitive(W_CType):
    _attrs_            = ['align']
    _immutable_fields_ = ['align']
    kind = "primitive"

    def __init__(self, space, size, name, name_position, align):
        W_CType.__init__(self, space, size, name, name_position)
        self.align = align

    def extra_repr(self, cdata):
        w_ob = self.convert_to_object(cdata)
        return self.space.str_w(self.space.repr(w_ob))

    def _alignof(self):
        return self.align

    def cast_str(self, w_ob):
        space = self.space
        s = space.str_w(w_ob)
        if len(s) != 1:
            raise operationerrfmt(space.w_TypeError,
                              "cannot cast string of length %d to ctype '%s'",
                                  len(s), self.name)
        return ord(s[0])

    def cast_unicode(self, w_ob):
        space = self.space
        s = space.unicode_w(w_ob)
        if len(s) != 1:
            raise operationerrfmt(space.w_TypeError,
                      "cannot cast unicode string of length %d to ctype '%s'",
                                  len(s), self.name)
        return ord(s[0])

    def cast(self, w_ob):
        from pypy.module._cffi_backend import ctypeptr
        space = self.space
        if (isinstance(w_ob, cdataobj.W_CData) and
               isinstance(w_ob.ctype, ctypeptr.W_CTypePtrOrArray)):
            value = rffi.cast(lltype.Signed, w_ob._cdata)
            value = self._cast_result(value)
        elif space.isinstance_w(w_ob, space.w_str):
            value = self.cast_str(w_ob)
            value = self._cast_result(value)
        elif space.isinstance_w(w_ob, space.w_unicode):
            value = self.cast_unicode(w_ob)
            value = self._cast_result(value)
        else:
            value = self._cast_generic(w_ob)
        w_cdata = cdataobj.W_CDataMem(space, self.size, self)
        self.write_raw_integer_data(w_cdata, value)
        return w_cdata

    def _cast_result(self, intvalue):
        return r_ulonglong(intvalue)

    def _cast_generic(self, w_ob):
        return misc.as_unsigned_long_long(self.space, w_ob, strict=False)

    def _overflow(self, w_ob):
        space = self.space
        s = space.str_w(space.str(w_ob))
        raise operationerrfmt(space.w_OverflowError,
                              "integer %s does not fit '%s'", s, self.name)

    def string(self, cdataobj, maxlen):
        if self.size == 1:
            s = cdataobj._cdata[0]
            keepalive_until_here(cdataobj)
            return self.space.wrap(s)
        return W_CType.string(self, cdataobj, maxlen)

class W_CTypePrimitiveCharOrUniChar(W_CTypePrimitive):
    _attrs_ = []
    is_primitive_integer = True

    def get_vararg_type(self):
        from pypy.module._cffi_backend import newtype
        return newtype.new_primitive_type(self.space, "int")

    def write_raw_integer_data(self, w_cdata, value):
        w_cdata.write_raw_unsigned_data(value)


class W_CTypePrimitiveChar(W_CTypePrimitiveCharOrUniChar):
    _attrs_ = []
    cast_anything = True

    def cast_to_int(self, cdata):
        return self.space.wrap(ord(cdata[0]))

    def convert_to_object(self, cdata):
        return self.space.wrap(cdata[0])

    def _convert_to_char(self, w_ob):
        space = self.space
        if space.isinstance_w(w_ob, space.w_str):
            s = space.str_w(w_ob)
            if len(s) == 1:
                return s[0]
        if (isinstance(w_ob, cdataobj.W_CData) and
               isinstance(w_ob.ctype, W_CTypePrimitiveChar)):
            return w_ob._cdata[0]
        raise self._convert_error("string of length 1", w_ob)

    def convert_from_object(self, cdata, w_ob):
        value = self._convert_to_char(w_ob)
        cdata[0] = value


class W_CTypePrimitiveUniChar(W_CTypePrimitiveCharOrUniChar):
    _attrs_ = []

    def cast_to_int(self, cdata):
        unichardata = rffi.cast(rffi.CWCHARP, cdata)
        return self.space.wrap(ord(unichardata[0]))

    def convert_to_object(self, cdata):
        unichardata = rffi.cast(rffi.CWCHARP, cdata)
        s = rffi.wcharpsize2unicode(unichardata, 1)
        return self.space.wrap(s)

    def string(self, cdataobj, maxlen):
        w_res = self.convert_to_object(cdataobj._cdata)
        keepalive_until_here(cdataobj)
        return w_res

    def _convert_to_unichar(self, w_ob):
        space = self.space
        if space.isinstance_w(w_ob, space.w_unicode):
            s = space.unicode_w(w_ob)
            if len(s) == 1:
                return s[0]
        if (isinstance(w_ob, cdataobj.W_CData) and
               isinstance(w_ob.ctype, W_CTypePrimitiveUniChar)):
            return rffi.cast(rffi.CWCHARP, w_ob._cdata)[0]
        raise self._convert_error("unicode string of length 1", w_ob)

    def convert_from_object(self, cdata, w_ob):
        value = self._convert_to_unichar(w_ob)
        rffi.cast(rffi.CWCHARP, cdata)[0] = value


class W_CTypePrimitiveSigned(W_CTypePrimitive):
    _attrs_            = ['value_fits_long', 'vmin', 'vrangemax']
    _immutable_fields_ = ['value_fits_long', 'vmin', 'vrangemax']
    is_primitive_integer = True

    def __init__(self, *args):
        W_CTypePrimitive.__init__(self, *args)
        self.value_fits_long = self.size <= rffi.sizeof(lltype.Signed)
        if self.size < rffi.sizeof(lltype.Signed):
            assert self.value_fits_long
            sh = self.size * 8
            self.vmin = r_uint(-1) << (sh - 1)
            self.vrangemax = (r_uint(1) << sh) - 1

    def is_long(self):
        return self.size == rffi.sizeof(lltype.Signed)

    def cast_to_int(self, cdata):
        return self.convert_to_object(cdata)

    def convert_to_object(self, cdata):
        if self.value_fits_long:
            value = misc.read_raw_long_data(cdata, self.size)
            return self.space.wrap(value)
        else:
            value = misc.read_raw_signed_data(cdata, self.size)
            return self.space.wrap(value)    # r_longlong => on 32-bit, 'long'

    def convert_from_object(self, cdata, w_ob):
        if self.value_fits_long:
            value = misc.as_long(self.space, w_ob)
            if self.size < rffi.sizeof(lltype.Signed):
                if r_uint(value) - self.vmin > self.vrangemax:
                    self._overflow(w_ob)
            misc.write_raw_signed_data(cdata, value, self.size)
        else:
            value = misc.as_long_long(self.space, w_ob)
            misc.write_raw_signed_data(cdata, value, self.size)

    def get_vararg_type(self):
        if self.size < rffi.sizeof(rffi.INT):
            from pypy.module._cffi_backend import newtype
            return newtype.new_primitive_type(self.space, "int")
        return self

    def write_raw_integer_data(self, w_cdata, value):
        w_cdata.write_raw_signed_data(value)


class W_CTypePrimitiveUnsigned(W_CTypePrimitive):
    _attrs_            = ['value_fits_long', 'value_fits_ulong', 'vrangemax']
    _immutable_fields_ = ['value_fits_long', 'value_fits_ulong', 'vrangemax']
    is_primitive_integer = True

    def __init__(self, *args):
        W_CTypePrimitive.__init__(self, *args)
        self.value_fits_long = self.size < rffi.sizeof(lltype.Signed)
        self.value_fits_ulong = self.size <= rffi.sizeof(lltype.Unsigned)
        if self.value_fits_long:
            self.vrangemax = self._compute_vrange_max()

    def _compute_vrange_max(self):
        sh = self.size * 8
        return (r_uint(1) << sh) - 1

    def cast_to_int(self, cdata):
        return self.convert_to_object(cdata)

    def convert_from_object(self, cdata, w_ob):
        if self.value_fits_ulong:
            value = misc.as_unsigned_long(self.space, w_ob, strict=True)
            if self.value_fits_long:
                if value > self.vrangemax:
                    self._overflow(w_ob)
            misc.write_raw_unsigned_data(cdata, value, self.size)
        else:
            value = misc.as_unsigned_long_long(self.space, w_ob, strict=True)
            misc.write_raw_unsigned_data(cdata, value, self.size)

    def convert_to_object(self, cdata):
        if self.value_fits_ulong:
            value = misc.read_raw_ulong_data(cdata, self.size)
            if self.value_fits_long:
                return self.space.wrap(intmask(value))
            else:
                return self.space.wrap(value)    # r_uint => 'long' object
        else:
            value = misc.read_raw_unsigned_data(cdata, self.size)
            return self.space.wrap(value)    # r_ulonglong => 'long' object

    def get_vararg_type(self):
        if self.size < rffi.sizeof(rffi.INT):
            from pypy.module._cffi_backend import newtype
            return newtype.new_primitive_type(self.space, "int")
        return self

    def write_raw_integer_data(self, w_cdata, value):
        w_cdata.write_raw_unsigned_data(value)


class W_CTypePrimitiveBool(W_CTypePrimitiveUnsigned):
    _attrs_ = []

    def _compute_vrange_max(self):
        return r_uint(1)

    def _cast_result(self, intvalue):
        return r_ulonglong(intvalue != 0)

    def _cast_generic(self, w_ob):
        return misc.object_as_bool(self.space, w_ob)

    def string(self, cdataobj, maxlen):
        # bypass the method 'string' implemented in W_CTypePrimitive
        return W_CType.string(self, cdataobj, maxlen)


class W_CTypePrimitiveFloat(W_CTypePrimitive):
    _attrs_ = []

    def is_double(self):
        return self.size == rffi.sizeof(lltype.Float)

    def cast(self, w_ob):
        space = self.space
        if isinstance(w_ob, cdataobj.W_CData):
            if not isinstance(w_ob.ctype, W_CTypePrimitive):
                raise operationerrfmt(space.w_TypeError,
                                      "cannot cast ctype '%s' to ctype '%s'",
                                      w_ob.ctype.name, self.name)
            w_ob = w_ob.convert_to_object()
        #
        if space.isinstance_w(w_ob, space.w_str):
            value = self.cast_str(w_ob)
        elif space.isinstance_w(w_ob, space.w_unicode):
            value = self.cast_unicode(w_ob)
        else:
            value = space.float_w(w_ob)
        w_cdata = cdataobj.W_CDataMem(space, self.size, self)
        if not isinstance(self, W_CTypePrimitiveLongDouble):
            w_cdata.write_raw_float_data(value)
        else:
            self._to_longdouble_and_write(value, w_cdata._cdata)
            keepalive_until_here(w_cdata)
        return w_cdata

    def cast_to_int(self, cdata):
        w_value = self.float(cdata)
        return self.space.int(w_value)

    def float(self, cdata):
        return self.convert_to_object(cdata)

    def convert_to_object(self, cdata):
        value = misc.read_raw_float_data(cdata, self.size)
        return self.space.wrap(value)

    def convert_from_object(self, cdata, w_ob):
        space = self.space
        value = space.float_w(space.float(w_ob))
        misc.write_raw_float_data(cdata, value, self.size)


class W_CTypePrimitiveLongDouble(W_CTypePrimitiveFloat):
    _attrs_ = []

    @jit.dont_look_inside
    def extra_repr(self, cdata):
        lvalue = misc.read_raw_longdouble_data(cdata)
        return misc.longdouble2str(lvalue)

    def cast(self, w_ob):
        if (isinstance(w_ob, cdataobj.W_CData) and
                isinstance(w_ob.ctype, W_CTypePrimitiveLongDouble)):
            w_cdata = self.convert_to_object(w_ob._cdata)
            keepalive_until_here(w_ob)
            return w_cdata
        else:
            return W_CTypePrimitiveFloat.cast(self, w_ob)

    @jit.dont_look_inside
    def _to_longdouble_and_write(self, value, cdata):
        lvalue = rffi.cast(rffi.LONGDOUBLE, value)
        misc.write_raw_longdouble_data(cdata, lvalue)

    @jit.dont_look_inside
    def _read_from_longdouble(self, cdata):
        lvalue = misc.read_raw_longdouble_data(cdata)
        value = rffi.cast(lltype.Float, lvalue)
        return value

    @jit.dont_look_inside
    def _copy_longdouble(self, cdatasrc, cdatadst):
        lvalue = misc.read_raw_longdouble_data(cdatasrc)
        misc.write_raw_longdouble_data(cdatadst, lvalue)

    def float(self, cdata):
        value = self._read_from_longdouble(cdata)
        return self.space.wrap(value)

    def convert_to_object(self, cdata):
        w_cdata = cdataobj.W_CDataMem(self.space, self.size, self)
        self._copy_longdouble(cdata, w_cdata._cdata)
        keepalive_until_here(w_cdata)
        return w_cdata

    def convert_from_object(self, cdata, w_ob):
        space = self.space
        if (isinstance(w_ob, cdataobj.W_CData) and
                isinstance(w_ob.ctype, W_CTypePrimitiveLongDouble)):
            self._copy_longdouble(w_ob._cdata, cdata)
            keepalive_until_here(w_ob)
        else:
            value = space.float_w(space.float(w_ob))
            self._to_longdouble_and_write(value, cdata)

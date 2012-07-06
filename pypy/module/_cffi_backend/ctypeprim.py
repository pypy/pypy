"""
Primitives.
"""

from pypy.interpreter.error import operationerrfmt
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rarithmetic import intmask, r_ulonglong
from pypy.rlib.objectmodel import keepalive_until_here

from pypy.module._cffi_backend.ctypeobj import W_CType
from pypy.module._cffi_backend import cdataobj, misc


class W_CTypePrimitive(W_CType):

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

    def cast(self, w_ob):
        from pypy.module._cffi_backend import ctypeptr
        space = self.space
        ob = space.interpclass_w(w_ob)
        if (isinstance(ob, cdataobj.W_CData) and
               isinstance(ob.ctype, ctypeptr.W_CTypePtrOrArray)):
            value = rffi.cast(lltype.Signed, ob._cdata)
            value = r_ulonglong(value)
        elif space.isinstance_w(w_ob, space.w_str):
            value = self.cast_str(w_ob)
            value = r_ulonglong(value)
        else:
            value = misc.as_unsigned_long_long(space, w_ob, strict=False)
        w_cdata = cdataobj.W_CDataCasted(space, self.size, self)
        w_cdata.write_raw_integer_data(value)
        return w_cdata

    def _overflow(self, w_ob):
        space = self.space
        s = space.str_w(space.str(w_ob))
        raise operationerrfmt(space.w_OverflowError,
                              "integer %s does not fit '%s'", s, self.name)


class W_CTypePrimitiveChar(W_CTypePrimitive):
    cast_anything = True

    def int(self, cdata):
        return self.space.wrap(ord(cdata[0]))

    def convert_to_object(self, cdata):
        return self.space.wrap(cdata[0])

    def str(self, cdataobj):
        w_res = self.convert_to_object(cdataobj._cdata)
        keepalive_until_here(cdataobj)
        return w_res

    def _convert_to_char(self, w_ob):
        space = self.space
        if space.isinstance_w(w_ob, space.w_str):
            s = space.str_w(w_ob)
            if len(s) == 1:
                return s[0]
        ob = space.interpclass_w(w_ob)
        if (isinstance(ob, cdataobj.W_CData) and
               isinstance(ob.ctype, W_CTypePrimitiveChar)):
            return ob._cdata[0]
        raise self._convert_error("string of length 1", w_ob)

    def convert_from_object(self, cdata, w_ob):
        value = self._convert_to_char(w_ob)
        cdata[0] = value


class W_CTypePrimitiveSigned(W_CTypePrimitive):

    def __init__(self, *args):
        W_CTypePrimitive.__init__(self, *args)
        self.value_fits_long = self.size <= rffi.sizeof(lltype.Signed)
        if self.size < rffi.sizeof(lltype.SignedLongLong):
            sh = self.size * 8
            self.vmin = r_ulonglong(-1) << (sh - 1)
            self.vrangemax = (r_ulonglong(1) << sh) - 1

    def int(self, cdata):
        if self.value_fits_long:
            # this case is to handle enums, but also serves as a slight
            # performance improvement for some other primitive types
            value = intmask(misc.read_raw_signed_data(cdata, self.size))
            return self.space.wrap(value)
        else:
            return self.convert_to_object(cdata)

    def convert_to_object(self, cdata):
        value = misc.read_raw_signed_data(cdata, self.size)
        if self.value_fits_long:
            return self.space.wrap(intmask(value))
        else:
            return self.space.wrap(value)    # r_longlong => on 32-bit, 'long'

    def convert_from_object(self, cdata, w_ob):
        value = misc.as_long_long(self.space, w_ob)
        if self.size < rffi.sizeof(lltype.SignedLongLong):
            if r_ulonglong(value) - self.vmin > self.vrangemax:
                self._overflow(w_ob)
        value = r_ulonglong(value)
        misc.write_raw_integer_data(cdata, value, self.size)


class W_CTypePrimitiveUnsigned(W_CTypePrimitive):

    def __init__(self, *args):
        W_CTypePrimitive.__init__(self, *args)
        self.value_fits_long = self.size < rffi.sizeof(lltype.Signed)
        if self.size < rffi.sizeof(lltype.SignedLongLong):
            sh = self.size * 8
            self.vrangemax = (r_ulonglong(1) << sh) - 1

    def int(self, cdata):
        return self.convert_to_object(cdata)

    def convert_from_object(self, cdata, w_ob):
        value = misc.as_unsigned_long_long(self.space, w_ob, strict=True)
        if self.size < rffi.sizeof(lltype.SignedLongLong):
            if value > self.vrangemax:
                self._overflow(w_ob)
        misc.write_raw_integer_data(cdata, value, self.size)

    def convert_to_object(self, cdata):
        value = misc.read_raw_unsigned_data(cdata, self.size)
        if self.value_fits_long:
            return self.space.wrap(intmask(value))
        else:
            return self.space.wrap(value)    # r_ulonglong => 'long' object


class W_CTypePrimitiveFloat(W_CTypePrimitive):

    def cast(self, w_ob):
        space = self.space
        ob = space.interpclass_w(w_ob)
        if isinstance(ob, cdataobj.W_CData):
            if not isinstance(ob.ctype, W_CTypePrimitive):
                raise operationerrfmt(space.w_TypeError,
                                      "cannot cast ctype '%s' to ctype '%s'",
                                      ob.ctype.name, self.name)
            w_ob = ob.convert_to_object()
        #
        if space.isinstance_w(w_ob, space.w_str):
            value = self.cast_str(w_ob)
        else:
            value = space.float_w(w_ob)
        w_cdata = cdataobj.W_CDataCasted(space, self.size, self)
        w_cdata.write_raw_float_data(value)
        return w_cdata

    def int(self, cdata):
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

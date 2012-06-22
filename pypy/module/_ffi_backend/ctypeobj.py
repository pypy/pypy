from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.objectmodel import keepalive_until_here

from pypy.module._ffi_backend import cdataobj, misc


class W_CType(Wrappable):
    _immutable_ = True

    def __init__(self, space, size, name, name_position):
        self.space = space
        self.size = size     # size of instances, or -1 if unknown
        self.name = name     # the name of the C type as a string
        self.name_position = name_position
        # 'name_position' is the index in 'name' where it must be extended,
        # e.g. with a '*' or a variable name.

    def repr(self):
        space = self.space
        return space.wrap("<ctype '%s'>" % (self.name,))

    def newp(self, w_init):
        space = self.space
        raise OperationError(space.w_TypeError,
                             space.wrap("expected a pointer or array ctype"))

    def cast(self, w_ob):
        raise NotImplementedError

    def int(self, cdata):
        space = self.space
        raise operationerrfmt(space.w_TypeError,
                              "int() not supported on cdata '%s'", self.name)

    def float(self, cdata):
        space = self.space
        raise operationerrfmt(space.w_TypeError,
                              "float() not supported on cdata '%s'", self.name)

    def convert_to_object(self, cdata):
        raise NotImplementedError

    def convert_from_object(self, cdata, w_ob):
        raise NotImplementedError

    def _check_subscript_index(self, w_cdata, i):
        space = self.space
        raise OperationError(xxx)

    def try_str(self, cdata):
        return None

    def insert_name(self, extra, extra_position):
        name = '%s%s%s' % (self.name[:self.name_position],
                           extra,
                           self.name[self.name_position:])
        name_position = self.name_position + extra_position
        return name, name_position


class W_CTypePtrOrArray(W_CType):
    pass


class W_CTypePointer(W_CTypePtrOrArray):

    def __init__(self, space, ctypeitem):
        name, name_position = ctypeitem.insert_name(' *', 2)
        size = rffi.sizeof(rffi.VOIDP)
        W_CType.__init__(self, space, size, name, name_position)
        self.ctypeitem = ctypeitem

    def cast(self, w_ob):
        space = self.space
        ob = space.interpclass_w(w_ob)
        if (isinstance(ob, cdataobj.W_CData) and
                isinstance(ob.ctype, W_CTypePtrOrArray)):
            value = ob._cdata
        elif space.is_w(w_ob, space.w_None):
            value = lltype.nullptr(rffi.CCHARP.TO)
        else:
            xxx
            value = misc.as_unsigned_long_long(space, w_ob, strict=False)
            value = rffi.cast(rffi.CCHARP, value)
        return cdataobj.W_CData(space, value, self)

    def newp(self, w_init):
        space = self.space
        citem = self.ctypeitem
        if citem.size < 0:
            xxx
        if isinstance(citem, W_CTypePrimitiveChar):
            xxx
        cdata = cdataobj.W_CDataOwn(space, citem.size, self)
        if not space.is_w(w_init, space.w_None):
            citem.convert_from_object(cdata._cdata, w_init)
            keepalive_until_here(cdata)
        return cdata

    def _check_subscript_index(self, w_cdata, i):
        if isinstance(w_cdata, cdataobj.W_CDataOwn) and i != 0:
            space = self.space
            raise operationerrfmt(space.w_IndexError,
                                  "cdata '%s' can only be indexed by 0",
                                  self.name)


class W_CTypePrimitive(W_CType):

    def cast_single_char(self, w_ob):
        space = self.space
        s = space.str_w(w_ob)
        if len(s) != 1:
            raise operationerrfmt(space.w_TypeError,
                              "cannot cast string of length %d to ctype '%s'",
                                  len(s), self.name)
        return ord(s[0])

    def cast(self, w_ob):
        space = self.space
        ob = space.interpclass_w(w_ob)
        if isinstance(ob, cdataobj.W_CData):
            xxx
        elif space.isinstance_w(w_ob, space.w_str):
            value = self.cast_single_char(w_ob)
        elif space.is_w(w_ob, space.w_None):
            value = 0
        else:
            value = misc.as_unsigned_long_long(space, w_ob, strict=False)
        w_cdata = cdataobj.W_CDataOwnFromCasted(space, self.size, self)
        w_cdata.write_raw_integer_data(value)
        return w_cdata


class W_CTypePrimitiveChar(W_CTypePrimitive):

    def int(self, cdata):
        return self.space.wrap(ord(cdata[0]))

    def try_str(self, cdata):
        return self.space.wrap(cdata[0])


class W_CTypePrimitiveSigned(W_CTypePrimitive):

    def __init__(self, *args):
        W_CTypePrimitive.__init__(self, *args)
        self.value_fits_long = self.size <= rffi.sizeof(lltype.Signed)

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
        # xxx enum
        if self.value_fits_long:
            return self.space.wrap(intmask(value))
        else:
            return self.space.wrap(value)    # r_longlong => on 32-bit, 'long'

    def convert_from_object(self, cdata, w_ob):
        value = misc.as_long_long(self.space, w_ob)
        # xxx enums
        misc.write_raw_integer_data(cdata, value, self.size)
        # xxx overflow


class W_CTypePrimitiveUnsigned(W_CTypePrimitive):

    def __init__(self, *args):
        W_CTypePrimitive.__init__(self, *args)
        self.value_fits_long = self.size < rffi.sizeof(lltype.Signed)

    def int(self, cdata):
        return self.convert_to_object(cdata)

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
            xxx
        elif space.isinstance_w(w_ob, space.w_str):
            value = self.cast_single_char(w_ob)
        elif space.is_w(w_ob, space.w_None):
            value = 0.0
        else:
            value = space.float_w(w_ob)
        w_cdata = cdataobj.W_CDataOwnFromCasted(space, self.size, self)
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


W_CType.typedef = TypeDef(
    '_ffi_backend.CTypeDescr',
    __repr__ = interp2app(W_CType.repr),
    )
W_CType.acceptable_as_base_class = False

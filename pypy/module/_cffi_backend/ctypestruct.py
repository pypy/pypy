"""
Struct and unions.
"""

from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, interp_attrproperty

from rpython.rlib import jit
from rpython.rlib.objectmodel import keepalive_until_here
from rpython.rlib.rarithmetic import r_uint, r_ulonglong, r_longlong, intmask
from rpython.rlib.rarithmetic import ovfcheck
from rpython.rtyper.lltypesystem import lltype, rffi

from pypy.module._cffi_backend import cdataobj, ctypeprim, misc
from pypy.module._cffi_backend.ctypeobj import W_CType


class W_CTypeStructOrUnion(W_CType):
    _immutable_fields_ = ['alignment?', 'fields_list?', 'fields_dict?',
                          'custom_field_pos?', 'with_var_array?']
    # fields added by complete_struct_or_union():
    alignment = -1
    fields_list = None
    fields_dict = None
    custom_field_pos = False
    with_var_array = False

    def __init__(self, space, name):
        W_CType.__init__(self, space, -1, name, len(name))

    def check_complete(self, w_errorcls=None):
        if self.fields_dict is None:
            space = self.space
            raise operationerrfmt(w_errorcls or space.w_TypeError,
                                  "'%s' is not completed yet", self.name)

    def _alignof(self):
        self.check_complete(w_errorcls=self.space.w_ValueError)
        return self.alignment

    def _fget(self, attrchar):
        if attrchar == 'f':     # fields
            space = self.space
            if self.size < 0:
                return space.w_None
            result = [None] * len(self.fields_list)
            for fname, field in self.fields_dict.iteritems():
                i = self.fields_list.index(field)
                result[i] = space.newtuple([space.wrap(fname),
                                            space.wrap(field)])
            return space.newlist(result)
        return W_CType._fget(self, attrchar)

    def convert_to_object(self, cdata):
        space = self.space
        self.check_complete()
        return cdataobj.W_CData(space, cdata, self)

    def copy_and_convert_to_object(self, cdata):
        space = self.space
        self.check_complete()
        ob = cdataobj.W_CDataNewOwning(space, self.size, self)
        misc._raw_memcopy(cdata, ob._cdata, self.size)
        keepalive_until_here(ob)
        return ob

    def typeoffsetof(self, fieldname):
        if fieldname is None:
            return (self, 0)
        self.check_complete()
        space = self.space
        try:
            cfield = self.fields_dict[fieldname]
        except KeyError:
            raise OperationError(space.w_KeyError, space.wrap(fieldname))
        if cfield.bitshift >= 0:
            raise OperationError(space.w_TypeError,
                                 space.wrap("not supported for bitfields"))
        return (cfield.ctype, cfield.offset)

    def _copy_from_same(self, cdata, w_ob):
        space = self.space
        if isinstance(w_ob, cdataobj.W_CData):
            if w_ob.ctype is self and self.size >= 0:
                misc._raw_memcopy(w_ob._cdata, cdata, self.size)
                keepalive_until_here(w_ob)
                return True
        return False

    def _check_only_one_argument_for_union(self, w_ob):
        pass

    def convert_from_object(self, cdata, w_ob):
        if not self._copy_from_same(cdata, w_ob):
            self.convert_struct_from_object(cdata, w_ob, optvarsize=-1)

    @jit.look_inside_iff(
        lambda self, cdata, w_ob, optvarsize: jit.isvirtual(w_ob)
    )
    def convert_struct_from_object(self, cdata, w_ob, optvarsize):
        self._check_only_one_argument_for_union(w_ob)

        space = self.space
        if (space.isinstance_w(w_ob, space.w_list) or
            space.isinstance_w(w_ob, space.w_tuple)):
            lst_w = space.listview(w_ob)
            if len(lst_w) > len(self.fields_list):
                raise operationerrfmt(space.w_ValueError,
                        "too many initializers for '%s' (got %d)",
                                      self.name, len(lst_w))
            for i in range(len(lst_w)):
                optvarsize = self.fields_list[i].write_v(cdata, lst_w[i],
                                                         optvarsize)
            return optvarsize

        elif space.isinstance_w(w_ob, space.w_dict):
            lst_w = space.fixedview(w_ob)
            for i in range(len(lst_w)):
                w_key = lst_w[i]
                key = space.str_w(w_key)
                try:
                    cf = self.fields_dict[key]
                except KeyError:
                    space.raise_key_error(w_key)
                    assert 0
                optvarsize = cf.write_v(cdata, space.getitem(w_ob, w_key),
                                        optvarsize)
            return optvarsize

        else:
            if optvarsize == -1:
                msg = "list or tuple or dict or struct-cdata"
            else:
                msg = "list or tuple or dict"
            raise self._convert_error(msg, w_ob)

    @jit.elidable
    def _getcfield_const(self, attr):
        return self.fields_dict[attr]

    def getcfield(self, attr):
        if self.fields_dict is not None:
            self = jit.promote(self)
            attr = jit.promote_string(attr)
            try:
                return self._getcfield_const(attr)
            except KeyError:
                pass
        return W_CType.getcfield(self, attr)


class W_CTypeStruct(W_CTypeStructOrUnion):
    kind = "struct"


class W_CTypeUnion(W_CTypeStructOrUnion):
    kind = "union"

    def _check_only_one_argument_for_union(self, w_ob):
        space = self.space
        n = space.int_w(space.len(w_ob))
        if n > 1:
            raise operationerrfmt(space.w_ValueError,
                                  "initializer for '%s': %d items given, but "
                                  "only one supported (use a dict if needed)",
                                  self.name, n)


class W_CField(W_Root):
    _immutable_ = True

    BS_REGULAR     = -1
    BS_EMPTY_ARRAY = -2

    def __init__(self, ctype, offset, bitshift, bitsize):
        self.ctype = ctype
        self.offset = offset
        self.bitshift = bitshift # >= 0: bitshift; or BS_REGULAR/BS_EMPTY_ARRAY
        self.bitsize = bitsize

    def is_bitfield(self):
        return self.bitshift >= 0

    def make_shifted(self, offset):
        return W_CField(self.ctype, offset + self.offset,
                        self.bitshift, self.bitsize)

    def read(self, cdata):
        cdata = rffi.ptradd(cdata, self.offset)
        if self.bitshift == self.BS_REGULAR:
            return self.ctype.convert_to_object(cdata)
        elif self.bitshift == self.BS_EMPTY_ARRAY:
            from pypy.module._cffi_backend import ctypearray
            ctype = self.ctype
            assert isinstance(ctype, ctypearray.W_CTypeArray)
            return cdataobj.W_CData(ctype.space, cdata, ctype.ctptr)
        else:
            return self.convert_bitfield_to_object(cdata)

    def write(self, cdata, w_ob):
        cdata = rffi.ptradd(cdata, self.offset)
        if self.is_bitfield():
            self.convert_bitfield_from_object(cdata, w_ob)
        else:
            self.ctype.convert_from_object(cdata, w_ob)

    def write_v(self, cdata, w_ob, optvarsize):
        # a special case for var-sized C99 arrays
        from pypy.module._cffi_backend import ctypearray
        ct = self.ctype
        if isinstance(ct, ctypearray.W_CTypeArray) and ct.length < 0:
            space = ct.space
            w_ob, varsizelength = misc.get_new_array_length(space, w_ob)
            if optvarsize != -1:
                # in this mode, the only purpose of this function is to compute
                # the real size of the structure from a var-sized C99 array
                assert cdata == lltype.nullptr(rffi.CCHARP.TO)
                itemsize = ct.ctitem.size
                try:
                    varsize = ovfcheck(itemsize * varsizelength)
                    size = ovfcheck(self.offset + varsize)
                except OverflowError:
                    raise OperationError(space.w_OverflowError,
                        space.wrap("array size would overflow a ssize_t"))
                assert size >= 0
                return max(size, optvarsize)
            # if 'value' was only an integer, get_new_array_length() returns
            # w_ob = space.w_None.  Detect if this was the case,
            # and if so, stop here, leaving the content uninitialized
            # (it should be zero-initialized from somewhere else).
            if space.is_w(w_ob, space.w_None):
                return optvarsize
        #
        if optvarsize == -1:
            self.write(cdata, w_ob)
        return optvarsize

    def convert_bitfield_to_object(self, cdata):
        ctype = self.ctype
        space = ctype.space
        #
        if isinstance(ctype, ctypeprim.W_CTypePrimitiveSigned):
            if ctype.value_fits_long:
                value = r_uint(misc.read_raw_long_data(cdata, ctype.size))
                valuemask = (r_uint(1) << self.bitsize) - 1
                shiftforsign = r_uint(1) << (self.bitsize - 1)
                value = ((value >> self.bitshift) + shiftforsign) & valuemask
                result = intmask(value) - intmask(shiftforsign)
                return space.wrap(result)
            else:
                value = misc.read_raw_unsigned_data(cdata, ctype.size)
                valuemask = (r_ulonglong(1) << self.bitsize) - 1
                shiftforsign = r_ulonglong(1) << (self.bitsize - 1)
                value = ((value >> self.bitshift) + shiftforsign) & valuemask
                result = r_longlong(value) - r_longlong(shiftforsign)
                return space.wrap(result)
        #
        if isinstance(ctype, ctypeprim.W_CTypePrimitiveUnsigned):
            value_fits_long = ctype.value_fits_long
            value_fits_ulong = ctype.value_fits_ulong
        elif isinstance(ctype, ctypeprim.W_CTypePrimitiveCharOrUniChar):
            value_fits_long = True
            value_fits_ulong = True
        else:
            raise NotImplementedError
        #
        if value_fits_ulong:
            value = misc.read_raw_ulong_data(cdata, ctype.size)
            valuemask = (r_uint(1) << self.bitsize) - 1
            value = (value >> self.bitshift) & valuemask
            if value_fits_long:
                return space.wrap(intmask(value))
            else:
                return space.wrap(value)    # uint => wrapped long object
        else:
            value = misc.read_raw_unsigned_data(cdata, ctype.size)
            valuemask = (r_ulonglong(1) << self.bitsize) - 1
            value = (value >> self.bitshift) & valuemask
            return space.wrap(value)      # ulonglong => wrapped long object

    def convert_bitfield_from_object(self, cdata, w_ob):
        ctype = self.ctype
        space = ctype.space
        #
        value = misc.as_long_long(space, w_ob)
        if isinstance(ctype, ctypeprim.W_CTypePrimitiveSigned):
            is_signed = True
            fmin = -(r_longlong(1) << (self.bitsize - 1))
            fmax = (r_longlong(1) << (self.bitsize - 1)) - 1
            if fmax == 0:
                fmax = 1      # special case to let "int x:1" receive "1"
        else:
            is_signed = False
            fmin = r_longlong(0)
            fmax = r_longlong((r_ulonglong(1) << self.bitsize) - 1)
        if value < fmin or value > fmax:
            raise operationerrfmt(space.w_OverflowError,
                                  "value %d outside the range allowed by the "
                                  "bit field width: %d <= x <= %d",
                                  value, fmin, fmax)
        rawmask = ((r_ulonglong(1) << self.bitsize) - 1) << self.bitshift
        rawvalue = r_ulonglong(value) << self.bitshift
        rawfielddata = misc.read_raw_unsigned_data(cdata, ctype.size)
        rawfielddata = (rawfielddata & ~rawmask) | (rawvalue & rawmask)
        if is_signed:
            misc.write_raw_signed_data(cdata, rawfielddata, ctype.size)
        else:
            misc.write_raw_unsigned_data(cdata, rawfielddata, ctype.size)


W_CField.typedef = TypeDef(
    'CField',
    __module__ = '_cffi_backend',
    type = interp_attrproperty('ctype', W_CField),
    offset = interp_attrproperty('offset', W_CField),
    bitshift = interp_attrproperty('bitshift', W_CField),
    bitsize = interp_attrproperty('bitsize', W_CField),
    )
W_CField.typedef.acceptable_as_base_class = False

import sys
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import (TypeDef, GetSetProperty,
    interp_attrproperty, interp_attrproperty_w)
from pypy.module.micronumpy import types, interp_boxes, base
from rpython.rlib.objectmodel import specialize
from rpython.rlib.rarithmetic import LONG_BIT, r_longlong, r_ulonglong
from rpython.rtyper.lltypesystem import rffi
from rpython.rlib import jit
from pypy.module.micronumpy.conversion_utils import byteorder_converter
from pypy.module.micronumpy.constants import *


def decode_w_dtype(space, w_dtype):
    if space.is_none(w_dtype):
        return None
    return space.interp_w(W_Dtype,
          space.call_function(space.gettypefor(W_Dtype), w_dtype))

@jit.unroll_safe
def dtype_agreement(space, w_arr_list, shape, out=None):
    """ agree on dtype from a list of arrays. if out is allocated,
    use it's dtype, otherwise allocate a new one with agreed dtype
    """
    from pypy.module.micronumpy.interp_ufuncs import find_binop_result_dtype

    if not space.is_none(out):
        return out
    dtype = w_arr_list[0].get_dtype()
    for w_arr in w_arr_list[1:]:
        dtype = find_binop_result_dtype(space, dtype, w_arr.get_dtype())
    out = base.W_NDimArray.from_shape(space, shape, dtype)
    return out

class W_Dtype(W_Root):
    _immutable_fields_ = ["itemtype?", "num", "kind", "name?", "char",
                          "w_box_type", "byteorder", "size?", "float_type",
                          "fields?", "fieldnames?", "shape", "subdtype", "base"]

    def __init__(self, itemtype, num, kind, name, char, w_box_type, byteorder=NPY_NATIVE,
                 size=1, alternate_constructors=[], aliases=[], float_type=None,
                 fields=None, fieldnames=None, shape=[], subdtype=None):
        self.itemtype = itemtype
        self.num = num
        self.kind = kind
        self.name = name
        self.char = char
        self.w_box_type = w_box_type
        self.byteorder = byteorder
        self.size = size
        self.alternate_constructors = alternate_constructors
        self.aliases = aliases
        self.float_type = float_type
        self.fields = fields
        self.fieldnames = fieldnames
        self.shape = list(shape)
        self.subdtype = subdtype
        if not subdtype:
            self.base = self
        else:
            self.base = subdtype.base

    def __repr__(self):
        if self.fields is not None:
            return '<DType %r>' % self.fields
        return '<DType %r>' % self.itemtype

    @specialize.argtype(1)
    def box(self, value):
        return self.itemtype.box(value)

    @specialize.argtype(1, 2)
    def box_complex(self, real, imag):
        return self.itemtype.box_complex(real, imag)

    def build_and_convert(self, space, box):
        return self.itemtype.build_and_convert(space, self, box)

    def coerce(self, space, w_item):
        return self.itemtype.coerce(space, self, w_item)

    def is_int_type(self):
        return (self.kind == NPY_SIGNEDLTR or self.kind == NPY_UNSIGNEDLTR or
                self.kind == NPY_GENBOOLLTR)

    def is_signed(self):
        return self.kind == NPY_SIGNEDLTR

    def is_complex_type(self):
        return self.kind == NPY_COMPLEXLTR

    def is_float_type(self):
        return (self.kind == NPY_FLOATINGLTR or self.float_type is not None)

    def is_bool_type(self):
        return self.kind == NPY_GENBOOLLTR

    def is_record_type(self):
        return self.fields is not None

    def is_str_type(self):
        return self.num == NPY_STRING

    def is_str_or_unicode(self):
        return (self.num == NPY_STRING or self.num == NPY_UNICODE)

    def is_flexible_type(self):
        return (self.is_str_or_unicode() or self.is_record_type())

    def is_native(self):
        return self.byteorder in (NPY_NATIVE, NPY_NATBYTE)

    def get_size(self):
        return self.size * self.itemtype.get_element_size()

    def get_name(self):
        if self.char == 'S':
            return '|S' + str(self.get_size())
        return self.name

    def descr_str(self, space):
        return space.wrap(self.get_name())

    def descr_repr(self, space):
        return space.wrap("dtype('%s')" % self.get_name())

    def descr_get_itemsize(self, space):
        return space.wrap(self.get_size())

    def descr_get_alignment(self, space):
        return space.wrap(self.itemtype.alignment)

    def descr_get_subdtype(self, space):
        return space.newtuple([space.wrap(self.subdtype), self.descr_get_shape(space)])

    def descr_get_str(self, space):
        size = self.get_size()
        basic = self.kind
        if basic == NPY_UNICODELTR:
            size >>= 2
            endian = NPY_NATBYTE
        elif size <= 1:
            endian = NPY_IGNORE
        else:
            endian = self.byteorder
            if endian == NPY_NATIVE:
                endian = NPY_NATBYTE
        return space.wrap("%s%s%s" % (endian, basic, size))

    def descr_get_base(self, space):
        return space.wrap(self.base)

    def descr_get_isnative(self, space):
        return space.wrap(self.is_native())

    def descr_get_shape(self, space):
        w_shape = [space.wrap(dim) for dim in self.shape]
        return space.newtuple(w_shape)

    def eq(self, space, w_other):
        w_other = space.call_function(space.gettypefor(W_Dtype), w_other)
        if space.is_w(self, w_other):
            return True
        if isinstance(w_other, W_Dtype):
            return space.eq_w(self.descr_reduce(space), w_other.descr_reduce(space))
        return False

    def descr_eq(self, space, w_other):
        return space.wrap(self.eq(space, w_other))

    def descr_ne(self, space, w_other):
        return space.wrap(not self.eq(space, w_other))

    def descr_get_fields(self, space):
        if self.fields is None:
            return space.w_None
        w_d = space.newdict()
        for name, (offset, subdtype) in self.fields.iteritems():
            space.setitem(w_d, space.wrap(name), space.newtuple([subdtype,
                                                                 space.wrap(offset)]))
        return w_d

    def set_fields(self, space, w_fields):
        if w_fields == space.w_None:
            self.fields = None
        else:
            self.fields = {}
            size = 0
            for key in space.listview(w_fields):
                value = space.getitem(w_fields, key)

                dtype = space.getitem(value, space.wrap(0))
                assert isinstance(dtype, W_Dtype)

                offset = space.int_w(space.getitem(value, space.wrap(1)))
                self.fields[space.str_w(key)] = offset, dtype

                size += dtype.get_size()

            self.itemtype = types.RecordType()
            self.size = size
            self.name = "void" + str(8 * self.get_size())

    def descr_get_names(self, space):
        if self.fieldnames is None:
            return space.w_None
        return space.newtuple([space.wrap(name) for name in self.fieldnames])

    def set_names(self, space, w_names):
        if w_names == space.w_None:
            self.fieldnames = None
        else:
            self.fieldnames = []
            iter = space.iter(w_names)
            while True:
                try:
                    self.fieldnames.append(space.str_w(space.next(iter)))
                except OperationError, e:
                    if not e.match(space, space.w_StopIteration):
                        raise
                    break

    def descr_getitem(self, space, w_item):
        if self.fields is None:
            raise OperationError(space.w_KeyError, space.wrap(
                "There are no fields in dtype %s." % self.name))
        if space.isinstance_w(w_item, space.w_basestring):
            item = space.str_w(w_item)
        elif space.isinstance_w(w_item, space.w_int):
            indx = space.int_w(w_item)
            try:
                item = self.fieldnames[indx]
            except IndexError:
                raise OperationError(space.w_IndexError, space.wrap(
                    "Field index %d out of range." % indx))
        else:
            raise OperationError(space.w_ValueError, space.wrap(
                "Field key must be an integer, string, or unicode."))
        try:
            return self.fields[item][1]
        except KeyError:
            raise OperationError(space.w_KeyError, space.wrap(
                "Field named '%s' not found." % item))

    def descr_len(self, space):
        if self.fields is None:
            return space.wrap(0)
        return space.wrap(len(self.fields))

    def descr_reduce(self, space):
        w_class = space.type(self)

        kind = self.kind
        elemsize = self.get_size()
        builder_args = space.newtuple([space.wrap("%s%d" % (kind, elemsize)), space.wrap(0), space.wrap(1)])

        version = space.wrap(3)
        names = self.descr_get_names(space)
        values = self.descr_get_fields(space)
        if self.fields:
            endian = NPY_IGNORE
            #TODO: Implement this when subarrays are implemented
            subdescr = space.w_None
            size = 0
            for key in self.fields:
                dtype = self.fields[key][1]
                assert isinstance(dtype, W_Dtype)
                size += dtype.get_size()
            w_size = space.wrap(size)
            #TODO: Change this when alignment is implemented
            alignment = space.wrap(1)
        else:
            endian = self.byteorder
            if endian == NPY_NATIVE:
                endian = NPY_NATBYTE
            subdescr = space.w_None
            w_size = space.wrap(-1)
            alignment = space.wrap(-1)
        flags = space.wrap(0)

        data = space.newtuple([version, space.wrap(endian), subdescr, names, values, w_size, alignment, flags])
        return space.newtuple([w_class, builder_args, data])

    def descr_setstate(self, space, w_data):
        if space.int_w(space.getitem(w_data, space.wrap(0))) != 3:
            raise OperationError(space.w_NotImplementedError, space.wrap("Pickling protocol version not supported"))

        endian = space.str_w(space.getitem(w_data, space.wrap(1)))
        if endian == NPY_NATBYTE:
            endian = NPY_NATIVE
        self.byteorder = endian

        fieldnames = space.getitem(w_data, space.wrap(3))
        self.set_names(space, fieldnames)

        fields = space.getitem(w_data, space.wrap(4))
        self.set_fields(space, fields)

    @unwrap_spec(new_order=str)
    def descr_newbyteorder(self, space, new_order=NPY_SWAP):
        newendian = byteorder_converter(space, new_order)
        endian = self.byteorder
        if endian != NPY_IGNORE:
            if newendian == NPY_SWAP:
                endian = NPY_OPPBYTE if self.is_native() else NPY_NATBYTE
            elif newendian != NPY_IGNORE:
                endian = newendian
        itemtype = self.itemtype.__class__(endian in (NPY_NATIVE, NPY_NATBYTE))
        return W_Dtype(itemtype, self.num, self.kind, self.name, self.char,
                       self.w_box_type, endian, size=self.size)

def dtype_from_list(space, w_lst):
    lst_w = space.listview(w_lst)
    fields = {}
    offset = 0
    fieldnames = []
    for w_elem in lst_w:
        size = 1
        w_shape = space.newtuple([])
        if space.len_w(w_elem) == 3:
            w_fldname, w_flddesc, w_shape = space.fixedview(w_elem)
            if not base.issequence_w(space, w_shape):
                w_shape = space.newtuple([w_shape,])
        else:
            w_fldname, w_flddesc = space.fixedview(w_elem, 2)
        subdtype = descr__new__(space, space.gettypefor(W_Dtype), w_flddesc, w_shape=w_shape)
        fldname = space.str_w(w_fldname)
        if fldname in fields:
            raise OperationError(space.w_ValueError, space.wrap("two fields with the same name"))
        assert isinstance(subdtype, W_Dtype)
        fields[fldname] = (offset, subdtype)
        offset += subdtype.get_size() * size
        fieldnames.append(fldname)
    itemtype = types.RecordType()
    return W_Dtype(itemtype, NPY_VOID, NPY_VOIDLTR,
                   "void" + str(8 * offset * itemtype.get_element_size()),
                   NPY_VOIDLTR, space.gettypefor(interp_boxes.W_VoidBox),
                   fields=fields, fieldnames=fieldnames, size=offset)

def dtype_from_dict(space, w_dict):
    raise OperationError(space.w_NotImplementedError, space.wrap(
        "dtype from dict"))

def dtype_from_spec(space, name):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "dtype from spec"))

def descr__new__(space, w_subtype, w_dtype, w_align=None, w_copy=None, w_shape=None):
    # w_align and w_copy are necessary for pickling
    cache = get_dtype_cache(space)

    if w_shape is not None and (space.isinstance_w(w_shape, space.w_int) or
                                space.len_w(w_shape) > 0):
        subdtype = descr__new__(space, w_subtype, w_dtype, w_align, w_copy)
        assert isinstance(subdtype, W_Dtype)
        size = 1
        if space.isinstance_w(w_shape, space.w_int):
            w_shape = space.newtuple([w_shape])
        shape = []
        for w_dim in space.fixedview(w_shape):
            dim = space.int_w(w_dim)
            shape.append(dim)
            size *= dim
        return W_Dtype(types.VoidType(), NPY_VOID, NPY_VOIDLTR,
                       "void" + str(8 * subdtype.get_size() * size),
                       NPY_VOIDLTR, space.gettypefor(interp_boxes.W_VoidBox),
                       shape=shape, subdtype=subdtype,
                       size=subdtype.get_size() * size)

    if space.is_none(w_dtype):
        return cache.w_float64dtype
    elif space.isinstance_w(w_dtype, w_subtype):
        return w_dtype
    elif space.isinstance_w(w_dtype, space.w_str):
        name = space.str_w(w_dtype)
        if ',' in name:
            return dtype_from_spec(space, name)
        try:
            return cache.dtypes_by_name[name]
        except KeyError:
            pass
        if name[0] in 'VSUc' or name[0] in '<>=' and name[1] in 'VSUc':
            return variable_dtype(space, name)
        raise OperationError(space.w_TypeError, space.wrap(
                       "data type %s not understood" % name))
    elif space.isinstance_w(w_dtype, space.w_list):
        return dtype_from_list(space, w_dtype)
    elif space.isinstance_w(w_dtype, space.w_tuple):
        w_dtype0 = space.getitem(w_dtype, space.wrap(0))
        w_dtype1 = space.getitem(w_dtype, space.wrap(1))
        subdtype = descr__new__(space, w_subtype, w_dtype0, w_align, w_copy)
        assert isinstance(subdtype, W_Dtype)
        if subdtype.get_size() == 0:
            name = "%s%d" % (subdtype.kind, space.int_w(w_dtype1))
            return descr__new__(space, w_subtype, space.wrap(name), w_align, w_copy)
        return descr__new__(space, w_subtype, w_dtype0, w_align, w_copy, w_shape=w_dtype1)
    elif space.isinstance_w(w_dtype, space.w_dict):
        return dtype_from_dict(space, w_dtype)
    for dtype in cache.builtin_dtypes:
        if w_dtype in dtype.alternate_constructors:
            return dtype
        if w_dtype is dtype.w_box_type:
            return dtype
    msg = "data type not understood (value of type %T not expected here)"
    raise operationerrfmt(space.w_TypeError, msg, w_dtype)

W_Dtype.typedef = TypeDef("dtype",
    __module__ = "numpy",
    __new__ = interp2app(descr__new__),

    __str__= interp2app(W_Dtype.descr_str),
    __repr__ = interp2app(W_Dtype.descr_repr),
    __eq__ = interp2app(W_Dtype.descr_eq),
    __ne__ = interp2app(W_Dtype.descr_ne),
    __getitem__ = interp2app(W_Dtype.descr_getitem),
    __len__ = interp2app(W_Dtype.descr_len),

    __reduce__ = interp2app(W_Dtype.descr_reduce),
    __setstate__ = interp2app(W_Dtype.descr_setstate),
    newbyteorder = interp2app(W_Dtype.descr_newbyteorder),

    type = interp_attrproperty_w("w_box_type", cls=W_Dtype),
    kind = interp_attrproperty("kind", cls=W_Dtype),
    char = interp_attrproperty("char", cls=W_Dtype),
    num = interp_attrproperty("num", cls=W_Dtype),
    byteorder = interp_attrproperty("byteorder", cls=W_Dtype),
    itemsize = GetSetProperty(W_Dtype.descr_get_itemsize),
    alignment = GetSetProperty(W_Dtype.descr_get_alignment),

    subdtype = GetSetProperty(W_Dtype.descr_get_subdtype),
    str = GetSetProperty(W_Dtype.descr_get_str),
    name = interp_attrproperty("name", cls=W_Dtype),
    base = GetSetProperty(W_Dtype.descr_get_base),
    shape = GetSetProperty(W_Dtype.descr_get_shape),
    isnative = GetSetProperty(W_Dtype.descr_get_isnative),
    fields = GetSetProperty(W_Dtype.descr_get_fields),
    names = GetSetProperty(W_Dtype.descr_get_names),
)
W_Dtype.typedef.acceptable_as_base_class = False


def variable_dtype(space, name):
    if name[0] in '<>=':
        name = name[1:]
    char = name[0]
    if len(name) == 1:
        size = 0
    else:
        try:
            size = int(name[1:])
        except ValueError:
            raise OperationError(space.w_TypeError, space.wrap("data type not understood"))
    if char == NPY_CHARLTR:
        char = NPY_STRINGLTR
        size = 1

    if char == NPY_STRINGLTR:
        itemtype = types.StringType()
        basename = 'string'
        num = NPY_STRING
        w_box_type = space.gettypefor(interp_boxes.W_StringBox)
    elif char == NPY_VOIDLTR:
        itemtype = types.VoidType()
        basename = 'void'
        num = NPY_VOID
        w_box_type = space.gettypefor(interp_boxes.W_VoidBox)
    elif char == NPY_UNICODELTR:
        itemtype = types.UnicodeType()
        basename = 'unicode'
        num = NPY_UNICODE
        w_box_type = space.gettypefor(interp_boxes.W_UnicodeBox)
    else:
        assert False

    return W_Dtype(itemtype, num, char,
                   basename + str(8 * size * itemtype.get_element_size()),
                   char, w_box_type, size=size)

def new_string_dtype(space, size):
    itemtype = types.StringType()
    return W_Dtype(
        itemtype,
        size=size,
        num=NPY_STRING,
        kind=NPY_STRINGLTR,
        name='string' + str(8 * size * itemtype.get_element_size()),
        char=NPY_STRINGLTR,
        w_box_type = space.gettypefor(interp_boxes.W_StringBox),
    )

def new_unicode_dtype(space, size):
    itemtype = types.UnicodeType()
    return W_Dtype(
        itemtype,
        size=size,
        num=NPY_UNICODE,
        kind=NPY_UNICODELTR,
        name='unicode' + str(8 * size * itemtype.get_element_size()),
        char=NPY_UNICODELTR,
        w_box_type = space.gettypefor(interp_boxes.W_UnicodeBox),
    )


class DtypeCache(object):
    def __init__(self, space):
        self.w_booldtype = W_Dtype(
            types.Bool(),
            num=NPY_BOOL,
            kind=NPY_GENBOOLLTR,
            name="bool",
            char=NPY_BOOLLTR,
            w_box_type=space.gettypefor(interp_boxes.W_BoolBox),
            alternate_constructors=[space.w_bool],
            aliases=['bool8'],
        )
        self.w_int8dtype = W_Dtype(
            types.Int8(),
            num=NPY_BYTE,
            kind=NPY_SIGNEDLTR,
            name="int8",
            char=NPY_BYTELTR,
            w_box_type=space.gettypefor(interp_boxes.W_Int8Box),
            aliases=['byte'],
        )
        self.w_uint8dtype = W_Dtype(
            types.UInt8(),
            num=NPY_UBYTE,
            kind=NPY_UNSIGNEDLTR,
            name="uint8",
            char=NPY_UBYTELTR,
            w_box_type=space.gettypefor(interp_boxes.W_UInt8Box),
            aliases=['ubyte'],
        )
        self.w_int16dtype = W_Dtype(
            types.Int16(),
            num=NPY_SHORT,
            kind=NPY_SIGNEDLTR,
            name="int16",
            char=NPY_SHORTLTR,
            w_box_type=space.gettypefor(interp_boxes.W_Int16Box),
            aliases=['short'],
        )
        self.w_uint16dtype = W_Dtype(
            types.UInt16(),
            num=NPY_USHORT,
            kind=NPY_UNSIGNEDLTR,
            name="uint16",
            char=NPY_USHORTLTR,
            w_box_type=space.gettypefor(interp_boxes.W_UInt16Box),
            aliases=['ushort'],
        )
        self.w_int32dtype = W_Dtype(
            types.Int32(),
            num=NPY_INT,
            kind=NPY_SIGNEDLTR,
            name="int32",
            char=NPY_INTLTR,
            w_box_type=space.gettypefor(interp_boxes.W_Int32Box),
       )
        self.w_uint32dtype = W_Dtype(
            types.UInt32(),
            num=NPY_UINT,
            kind=NPY_UNSIGNEDLTR,
            name="uint32",
            char=NPY_UINTLTR,
            w_box_type=space.gettypefor(interp_boxes.W_UInt32Box),
        )
        self.w_longdtype = W_Dtype(
            types.Long(),
            num=NPY_LONG,
            kind=NPY_SIGNEDLTR,
            name="int%d" % LONG_BIT,
            char=NPY_LONGLTR,
            w_box_type=space.gettypefor(interp_boxes.W_LongBox),
            alternate_constructors=[space.w_int,
                                    space.gettypefor(interp_boxes.W_IntegerBox),
                                    space.gettypefor(interp_boxes.W_SignedIntegerBox),
                                   ],
            aliases=['int'],
        )
        self.w_ulongdtype = W_Dtype(
            types.ULong(),
            num=NPY_ULONG,
            kind=NPY_UNSIGNEDLTR,
            name="uint%d" % LONG_BIT,
            char=NPY_ULONGLTR,
            w_box_type=space.gettypefor(interp_boxes.W_ULongBox),
            alternate_constructors=[ space.gettypefor(interp_boxes.W_UnsignedIntegerBox),
                                   ],
            aliases=['uint'],
        )
        self.w_int64dtype = W_Dtype(
            types.Int64(),
            num=NPY_LONGLONG,
            kind=NPY_SIGNEDLTR,
            name="int64",
            char=NPY_LONGLONGLTR,
            w_box_type=space.gettypefor(interp_boxes.W_Int64Box),
            alternate_constructors=[space.w_long],
            aliases=['longlong'],
        )
        self.w_uint64dtype = W_Dtype(
            types.UInt64(),
            num=NPY_ULONGLONG,
            kind=NPY_UNSIGNEDLTR,
            name="uint64",
            char=NPY_ULONGLONGLTR,
            w_box_type=space.gettypefor(interp_boxes.W_UInt64Box),
            aliases=['ulonglong'],
        )
        self.w_float32dtype = W_Dtype(
            types.Float32(),
            num=NPY_FLOAT,
            kind=NPY_FLOATINGLTR,
            name="float32",
            char=NPY_FLOATLTR,
            w_box_type=space.gettypefor(interp_boxes.W_Float32Box),
            aliases=['single']
        )
        self.w_float64dtype = W_Dtype(
            types.Float64(),
            num=NPY_DOUBLE,
            kind=NPY_FLOATINGLTR,
            name="float64",
            char=NPY_DOUBLELTR,
            w_box_type = space.gettypefor(interp_boxes.W_Float64Box),
            alternate_constructors=[space.w_float,
                                    space.gettypefor(interp_boxes.W_NumberBox),
                                   ],
            aliases=["float", "double"],
        )
        self.w_floatlongdtype = W_Dtype(
            types.FloatLong(),
            num=NPY_LONGDOUBLE,
            kind=NPY_FLOATINGLTR,
            name="float%d" % (interp_boxes.long_double_size * 8),
            char=NPY_LONGDOUBLELTR,
            w_box_type=space.gettypefor(interp_boxes.W_FloatLongBox),
            aliases=["longdouble", "longfloat"],
        )
        self.w_complex64dtype = W_Dtype(
            types.Complex64(),
            num=NPY_CFLOAT,
            kind=NPY_COMPLEXLTR,
            name="complex64",
            char=NPY_CFLOATLTR,
            w_box_type = space.gettypefor(interp_boxes.W_Complex64Box),
            aliases=['csingle'],
            float_type = self.w_float32dtype,
        )
        self.w_complex128dtype = W_Dtype(
            types.Complex128(),
            num=NPY_CDOUBLE,
            kind=NPY_COMPLEXLTR,
            name="complex128",
            char=NPY_CDOUBLELTR,
            w_box_type = space.gettypefor(interp_boxes.W_Complex128Box),
            alternate_constructors=[space.w_complex],
            aliases=["complex", 'cfloat', 'cdouble'],
            float_type = self.w_float64dtype,
        )
        self.w_complexlongdtype = W_Dtype(
            types.ComplexLong(),
            num=NPY_CLONGDOUBLE,
            kind=NPY_COMPLEXLTR,
            name="complex%d" % (interp_boxes.long_double_size * 16),
            char=NPY_CLONGDOUBLELTR,
            w_box_type = space.gettypefor(interp_boxes.W_ComplexLongBox),
            aliases=["clongdouble", "clongfloat"],
            float_type = self.w_floatlongdtype,
        )
        self.w_stringdtype = W_Dtype(
            types.StringType(),
            size=0,
            num=NPY_STRING,
            kind=NPY_STRINGLTR,
            name='string',
            char=NPY_STRINGLTR,
            w_box_type = space.gettypefor(interp_boxes.W_StringBox),
            alternate_constructors=[space.w_str, space.gettypefor(interp_boxes.W_CharacterBox)],
            aliases=["str"],
        )
        self.w_unicodedtype = W_Dtype(
            types.UnicodeType(),
            size=0,
            num=NPY_UNICODE,
            kind=NPY_UNICODELTR,
            name='unicode',
            char=NPY_UNICODELTR,
            w_box_type = space.gettypefor(interp_boxes.W_UnicodeBox),
            alternate_constructors=[space.w_unicode],
        )
        self.w_voiddtype = W_Dtype(
            types.VoidType(),
            size=0,
            num=NPY_VOID,
            kind=NPY_VOIDLTR,
            name='void',
            char=NPY_VOIDLTR,
            w_box_type = space.gettypefor(interp_boxes.W_VoidBox),
            #alternate_constructors=[space.w_buffer],
            # XXX no buffer in space
            #alternate_constructors=[space.gettypefor(interp_boxes.W_GenericBox)],
            # XXX fix, leads to _coerce error
        )
        self.w_float16dtype = W_Dtype(
            types.Float16(),
            num=NPY_HALF,
            kind=NPY_FLOATINGLTR,
            name="float16",
            char=NPY_HALFLTR,
            w_box_type=space.gettypefor(interp_boxes.W_Float16Box),
        )
        ptr_size = rffi.sizeof(rffi.CCHARP)
        if ptr_size == 4:
            intp_box = interp_boxes.W_Int32Box
            intp_type = types.Int32()
            intp_num = NPY_INT
            uintp_box = interp_boxes.W_UInt32Box
            uintp_type = types.UInt32()
            uintp_num = NPY_UINT
        elif ptr_size == 8:
            intp_box = interp_boxes.W_Int64Box
            intp_type = types.Int64()
            intp_num = NPY_LONG
            uintp_box = interp_boxes.W_UInt64Box
            uintp_type = types.UInt64()
            uintp_num = NPY_ULONG
        else:
            raise ValueError('unknown point size %d' % ptr_size)
        self.w_intpdtype = W_Dtype(
            intp_type,
            num=intp_num,
            kind=NPY_INTPLTR,
            name='intp',
            char=NPY_INTPLTR,
            w_box_type = space.gettypefor(intp_box),
        )
        self.w_uintpdtype = W_Dtype(
            uintp_type,
            num=uintp_num,
            kind=NPY_UINTPLTR,
            name='uintp',
            char=NPY_UINTPLTR,
            w_box_type = space.gettypefor(uintp_box),
        )
        float_dtypes = [self.w_float16dtype, self.w_float32dtype,
                        self.w_float64dtype, self.w_floatlongdtype]
        complex_dtypes = [self.w_complex64dtype, self.w_complex128dtype,
                          self.w_complexlongdtype]
        self.builtin_dtypes = [
            self.w_booldtype,
            self.w_int8dtype, self.w_uint8dtype,
            self.w_int16dtype, self.w_uint16dtype,
            self.w_longdtype, self.w_ulongdtype,
            self.w_int32dtype, self.w_uint32dtype,
            self.w_int64dtype, self.w_uint64dtype,
            ] + float_dtypes + complex_dtypes + [
            self.w_stringdtype, self.w_unicodedtype, self.w_voiddtype,
            self.w_intpdtype, self.w_uintpdtype,
        ]
        self.float_dtypes_by_num_bytes = sorted(
            (dtype.get_size(), dtype)
            for dtype in float_dtypes
        )
        self.dtypes_by_num = {}
        self.dtypes_by_name = {}
        # we reverse, so the stuff with lower numbers override stuff with
        # higher numbers
        for dtype in reversed(self.builtin_dtypes):
            self.dtypes_by_num[dtype.num] = dtype
            self.dtypes_by_name[dtype.name] = dtype
            can_name = dtype.kind + str(dtype.get_size())
            self.dtypes_by_name[can_name] = dtype
            self.dtypes_by_name[NPY_NATBYTE + can_name] = dtype
            self.dtypes_by_name[NPY_NATIVE + can_name] = dtype
            new_name = NPY_OPPBYTE + can_name
            itemtype = type(dtype.itemtype)(False)
            self.dtypes_by_name[new_name] = W_Dtype(
                itemtype,
                dtype.num, dtype.kind, new_name, dtype.char, dtype.w_box_type,
                byteorder=NPY_OPPBYTE, float_type=dtype.float_type)
            if dtype.kind != dtype.char:
                can_name = dtype.char
                self.dtypes_by_name[NPY_NATBYTE + can_name] = dtype
                self.dtypes_by_name[NPY_NATIVE + can_name] = dtype
                new_name = NPY_OPPBYTE + can_name
                self.dtypes_by_name[new_name] = W_Dtype(
                    itemtype,
                    dtype.num, dtype.kind, new_name, dtype.char, dtype.w_box_type,
                    byteorder=NPY_OPPBYTE, float_type=dtype.float_type)

            for alias in dtype.aliases:
                self.dtypes_by_name[alias] = dtype
            self.dtypes_by_name[dtype.char] = dtype

        typeinfo_full = {
            'LONGLONG': self.w_int64dtype,
            'SHORT': self.w_int16dtype,
            'VOID': self.w_voiddtype,
            'UBYTE': self.w_uint8dtype,
            'UINTP': self.w_ulongdtype,
            'ULONG': self.w_ulongdtype,
            'LONG': self.w_longdtype,
            'UNICODE': self.w_unicodedtype,
            #'OBJECT',
            'ULONGLONG': self.w_uint64dtype,
            'STRING': self.w_stringdtype,
            'CFLOAT': self.w_complex64dtype,
            'CDOUBLE': self.w_complex128dtype,
            'CLONGDOUBLE': self.w_complexlongdtype,
            #'DATETIME',
            'UINT': self.w_uint32dtype,
            'INTP': self.w_intpdtype,
            'UINTP': self.w_uintpdtype,
            'HALF': self.w_float16dtype,
            'BYTE': self.w_int8dtype,
            #'TIMEDELTA',
            'INT': self.w_int32dtype,
            'DOUBLE': self.w_float64dtype,
            'LONGDOUBLE': self.w_floatlongdtype,
            'USHORT': self.w_uint16dtype,
            'FLOAT': self.w_float32dtype,
            'BOOL': self.w_booldtype,
        }

        typeinfo_partial = {
            'Generic': interp_boxes.W_GenericBox,
            'Character': interp_boxes.W_CharacterBox,
            'Flexible': interp_boxes.W_FlexibleBox,
            'Inexact': interp_boxes.W_InexactBox,
            'Integer': interp_boxes.W_IntegerBox,
            'SignedInteger': interp_boxes.W_SignedIntegerBox,
            'UnsignedInteger': interp_boxes.W_UnsignedIntegerBox,
            'ComplexFloating': interp_boxes.W_ComplexFloatingBox,
            'Number': interp_boxes.W_NumberBox,
            'Floating': interp_boxes.W_FloatingBox
        }
        w_typeinfo = space.newdict()
        for k, v in typeinfo_partial.iteritems():
            space.setitem(w_typeinfo, space.wrap(k), space.gettypefor(v))
        for k, dtype in typeinfo_full.iteritems():
            itemsize = dtype.get_size()
            items_w = [space.wrap(dtype.char),
                       space.wrap(dtype.num),
                       space.wrap(itemsize * 8), # in case of changing
                       # number of bits per byte in the future
                       space.wrap(itemsize / (2 if dtype.kind == NPY_COMPLEXLTR else 1) or 1)]
            if dtype.is_int_type():
                if dtype.kind == NPY_GENBOOLLTR:
                    w_maxobj = space.wrap(1)
                    w_minobj = space.wrap(0)
                elif dtype.is_signed():
                    w_maxobj = space.wrap(r_longlong((1 << (itemsize*8 - 1))
                                          - 1))
                    w_minobj = space.wrap(r_longlong(-1) << (itemsize*8 - 1))
                else:
                    w_maxobj = space.wrap(r_ulonglong(1 << (itemsize*8)) - 1)
                    w_minobj = space.wrap(0)
                items_w = items_w + [w_maxobj, w_minobj]
            items_w = items_w + [dtype.w_box_type]
            space.setitem(w_typeinfo, space.wrap(k), space.newtuple(items_w))
        self.w_typeinfo = w_typeinfo

def get_dtype_cache(space):
    return space.fromcache(DtypeCache)

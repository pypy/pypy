import string
from pypy.interpreter.argument import Arguments
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import (TypeDef, GetSetProperty,
                                      interp_attrproperty, interp_attrproperty_w)
from rpython.annotator.model import SomeChar
from rpython.rlib import jit
from rpython.rlib.objectmodel import (
        specialize, compute_hash, we_are_translated, enforceargs)
from rpython.rlib.rarithmetic import r_longlong, r_ulonglong
from pypy.module.micronumpy import types, boxes, support, constants as NPY
from .base import W_NDimArray
from pypy.module.micronumpy.appbridge import get_appbridge_cache
from pypy.module.micronumpy.converters import byteorder_converter


def decode_w_dtype(space, w_dtype):
    if space.is_none(w_dtype):
        return None
    if isinstance(w_dtype, W_Dtype):
        return w_dtype
    return space.interp_w(
        W_Dtype, space.call_function(space.gettypefor(W_Dtype), w_dtype))


@jit.unroll_safe
def dtype_agreement(space, w_arr_list, shape, out=None):
    """ agree on dtype from a list of arrays. if out is allocated,
    use it's dtype, otherwise allocate a new one with agreed dtype
    """
    from .casting import find_result_type

    if not space.is_none(out):
        return out
    arr_w = [w_arr for w_arr in w_arr_list if not space.is_none(w_arr)]
    dtype = find_result_type(space, arr_w, [])
    assert dtype is not None
    out = W_NDimArray.from_shape(space, shape, dtype)
    return out

def byteorder_w(space, w_str):
    order = space.str_w(w_str)
    if len(order) != 1:
        raise oefmt(space.w_ValueError,
                "endian is not 1-char string in Numpy dtype unpickling")
    endian = order[0]
    if endian not in (NPY.LITTLE, NPY.BIG, NPY.NATIVE, NPY.IGNORE):
        raise oefmt(space.w_ValueError, "Invalid byteorder %s", endian)
    return endian


class W_Dtype(W_Root):
    _immutable_fields_ = [
        "itemtype?", "w_box_type", "byteorder?", "names?", "fields?",
        "elsize?", "alignment?", "shape?", "subdtype?", "base?", "flags?"]

    @enforceargs(byteorder=SomeChar())
    def __init__(self, itemtype, w_box_type, byteorder=NPY.NATIVE, names=[],
                 fields={}, elsize=-1, shape=[], subdtype=None):
        self.itemtype = itemtype
        self.w_box_type = w_box_type
        if itemtype.get_element_size() == 1 or isinstance(itemtype, types.ObjectType):
            byteorder = NPY.IGNORE
        self.byteorder = byteorder
        self.names = names
        self.fields = fields
        if elsize < 0:
            elsize = itemtype.get_element_size()
        self.elsize = elsize
        self.shape = shape
        self.subdtype = subdtype
        self.flags = 0
        self.metadata = None
        if isinstance(itemtype, types.ObjectType):
            self.flags = NPY.OBJECT_DTYPE_FLAGS
        if not subdtype:
            self.base = self
            self.alignment = itemtype.get_element_size()
        else:
            self.base = subdtype.base
            self.alignment = subdtype.itemtype.get_element_size()

    @property
    def num(self):
        return self.itemtype.num

    @property
    def kind(self):
        return self.itemtype.kind

    @property
    def char(self):
        return self.itemtype.char

    def __repr__(self):
        if self.fields:
            return '<DType %r>' % self.fields
        return '<DType %r>' % self.itemtype

    @specialize.argtype(1)
    def box(self, value):
        return self.itemtype.box(value)

    @specialize.argtype(1, 2)
    def box_complex(self, real, imag):
        return self.itemtype.box_complex(real, imag)

    def coerce(self, space, w_item):
        return self.itemtype.coerce(space, self, w_item)

    def is_bool(self):
        return self.kind == NPY.GENBOOLLTR

    def is_signed(self):
        return self.kind == NPY.SIGNEDLTR

    def is_unsigned(self):
        return self.kind == NPY.UNSIGNEDLTR

    def is_int(self):
        return (self.kind == NPY.SIGNEDLTR or self.kind == NPY.UNSIGNEDLTR or
                self.kind == NPY.GENBOOLLTR)

    def is_float(self):
        return self.kind == NPY.FLOATINGLTR

    def is_complex(self):
        return self.kind == NPY.COMPLEXLTR

    def is_number(self):
        return self.is_int() or self.is_float() or self.is_complex()

    def is_str(self):
        return self.num == NPY.STRING

    def is_unicode(self):
        return self.num == NPY.UNICODE

    def is_object(self):
        return self.num == NPY.OBJECT

    def is_str_or_unicode(self):
        return self.num == NPY.STRING or self.num == NPY.UNICODE

    def is_flexible(self):
        return self.is_str_or_unicode() or self.num == NPY.VOID

    def is_record(self):
        return bool(self.fields)

    def is_native(self):
        # Use ord() to ensure that self.byteorder is a char and JITs properly
        return ord(self.byteorder) in (ord(NPY.NATIVE), ord(NPY.NATBYTE))

    def as_signed(self, space):
        """Convert from an unsigned integer dtype to its signed partner"""
        if self.is_unsigned():
            return num2dtype(space, self.num - 1)
        else:
            return self

    def as_unsigned(self, space):
        """Convert from a signed integer dtype to its unsigned partner"""
        if self.is_signed():
            return num2dtype(space, self.num + 1)
        else:
            return self

    def get_float_dtype(self, space):
        assert self.is_complex()
        dtype = get_dtype_cache(space).component_dtypes[self.num]
        if self.byteorder == NPY.OPPBYTE:
            dtype = dtype.descr_newbyteorder(space)
        assert dtype.is_float()
        return dtype

    def get_name(self):
        name = self.w_box_type.getname(self.itemtype.space)
        if name.endswith('_'):
            name = name[:-1]
        return name

    def descr_get_name(self, space):
        name = self.get_name()
        if self.is_flexible() and self.elsize != 0:
            return space.wrap(name + str(self.elsize * 8))
        return space.wrap(name)

    def descr_get_str(self, space):
        basic = self.kind
        endian = self.byteorder
        size = self.elsize
        if endian == NPY.NATIVE:
            endian = NPY.NATBYTE
        if self.num == NPY.UNICODE:
            size >>= 2
        return space.wrap("%s%s%s" % (endian, basic, size))

    def descr_get_descr(self, space):
        if not self.is_record():
            return space.newlist([space.newtuple([space.wrap(""),
                                                  self.descr_get_str(space)])])
        else:
            descr = []
            for name in self.names:
                subdtype = self.fields[name][1]
                subdescr = [space.wrap(name)]
                if subdtype.is_record():
                    subdescr.append(subdtype.descr_get_descr(space))
                elif subdtype.subdtype is not None:
                    subdescr.append(subdtype.subdtype.descr_get_str(space))
                else:
                    subdescr.append(subdtype.descr_get_str(space))
                if subdtype.shape != []:
                    subdescr.append(subdtype.descr_get_shape(space))
                descr.append(space.newtuple(subdescr[:]))
            return space.newlist(descr)

    def descr_get_hasobject(self, space):
        return space.wrap(self.is_object())

    def descr_get_isbuiltin(self, space):
        if self.fields is None:
            return space.wrap(1)
        return space.wrap(0)

    def descr_get_isnative(self, space):
        return space.wrap(self.is_native())

    def descr_get_base(self, space):
        return space.wrap(self.base)

    def descr_get_subdtype(self, space):
        if self.subdtype is None:
            return space.w_None
        return space.newtuple([space.wrap(self.subdtype),
                               self.descr_get_shape(space)])

    def descr_get_shape(self, space):
        return space.newtuple([space.wrap(dim) for dim in self.shape])

    def descr_get_flags(self, space):
        return space.wrap(self.flags)

    def descr_get_fields(self, space):
        if not self.fields:
            return space.w_None
        w_fields = space.newdict()
        for name, (offset, subdtype) in self.fields.iteritems():
            space.setitem(w_fields, space.wrap(name),
                          space.newtuple([subdtype, space.wrap(offset)]))
        return w_fields

    def descr_get_names(self, space):
        if not self.fields:
            return space.w_None
        return space.newtuple([space.wrap(name) for name in self.names])

    def descr_set_names(self, space, w_names):
        if not self.fields:
            raise oefmt(space.w_ValueError, "there are no fields defined")
        if not space.issequence_w(w_names) or \
                space.len_w(w_names) != len(self.names):
            raise oefmt(space.w_ValueError,
                        "must replace all names at once "
                        "with a sequence of length %d",
                        len(self.names))
        names = []
        for w_name in space.fixedview(w_names):
            if not space.isinstance_w(w_name, space.w_str):
                raise oefmt(space.w_ValueError,
                            "item #%d of names is of type %T and not string",
                            len(names), w_name)
            names.append(space.str_w(w_name))
        fields = {}
        for i in range(len(self.names)):
            if names[i] in fields:
                raise oefmt(space.w_ValueError, "Duplicate field names given.")
            fields[names[i]] = self.fields[self.names[i]]
        self.fields = fields
        self.names = names

    def descr_del_names(self, space):
        raise oefmt(space.w_AttributeError, 
            "Cannot delete dtype names attribute")

    def descr_get_metadata(self, space):
        if self.metadata is None:
            return space.w_None
        return self.metadata

    def descr_set_metadata(self, space, w_metadata):
        if w_metadata is None:
            return
        if not space.isinstance_w(w_metadata, space.w_dict):
            raise oefmt(space.w_TypeError, "argument 4 must be dict, not str")
        self.metadata = w_metadata

    def descr_del_metadata(self, space):
        self.metadata = None

    def eq(self, space, w_other):
        w_other = space.call_function(space.gettypefor(W_Dtype), w_other)
        if space.is_w(self, w_other):
            return True
        if isinstance(w_other, W_Dtype):
            return space.eq_w(self.descr_reduce(space),
                              w_other.descr_reduce(space))
        return False

    def descr_eq(self, space, w_other):
        return space.wrap(self.eq(space, w_other))

    def descr_ne(self, space, w_other):
        return space.wrap(not self.eq(space, w_other))

    def descr_le(self, space, w_other):
        from .casting import can_cast_to
        w_other = as_dtype(space, w_other)
        return space.wrap(can_cast_to(self, w_other))

    def descr_ge(self, space, w_other):
        from .casting import can_cast_to
        w_other = as_dtype(space, w_other)
        return space.wrap(can_cast_to(w_other, self))

    def descr_lt(self, space, w_other):
        from .casting import can_cast_to
        w_other = as_dtype(space, w_other)
        return space.wrap(can_cast_to(self, w_other) and not self.eq(space, w_other))

    def descr_gt(self, space, w_other):
        from .casting import can_cast_to
        w_other = as_dtype(space, w_other)
        return space.wrap(can_cast_to(w_other, self) and not self.eq(space, w_other))

    def _compute_hash(self, space, x):
        from rpython.rlib.rarithmetic import intmask
        if not self.fields and self.subdtype is None:
            endian = self.byteorder
            if endian == NPY.NATIVE:
                endian = NPY.NATBYTE
            flags = 0
            y = 0x345678
            y = intmask((1000003 * y) ^ ord(self.kind[0]))
            y = intmask((1000003 * y) ^ ord(endian[0]))
            y = intmask((1000003 * y) ^ flags)
            y = intmask((1000003 * y) ^ self.elsize)
            if self.is_flexible():
                y = intmask((1000003 * y) ^ self.alignment)
            return intmask((1000003 * x) ^ y)
        if self.fields:
            for name, (offset, subdtype) in self.fields.iteritems():
                assert isinstance(subdtype, W_Dtype)
                y = intmask(1000003 * (0x345678 ^ compute_hash(name)))
                y = intmask(1000003 * (y ^ compute_hash(offset)))
                y = intmask(1000003 * (y ^ subdtype._compute_hash(space,
                                                                 0x345678)))
                x = intmask(x ^ y)
        if self.subdtype is not None:
            for s in self.shape:
                x = intmask((1000003 * x) ^ compute_hash(s))
            x = self.base._compute_hash(space, x)
        return x

    def descr_hash(self, space):
        return space.wrap(self._compute_hash(space, 0x345678))

    def descr_str(self, space):
        if self.fields:
            return space.str(self.descr_get_descr(space))
        elif self.subdtype is not None:
            return space.str(space.newtuple([
                self.subdtype.descr_get_str(space),
                self.descr_get_shape(space)]))
        else:
            if self.is_flexible():
                return self.descr_get_str(space)
            else:
                return self.descr_get_name(space)

    def descr_repr(self, space):
        if self.fields:
            r = self.descr_get_descr(space)
        elif self.subdtype is not None:
            r = space.newtuple([self.subdtype.descr_get_str(space),
                                self.descr_get_shape(space)])
        else:
            if self.is_flexible():
                if self.byteorder != NPY.IGNORE:
                    byteorder = NPY.NATBYTE if self.is_native() else NPY.OPPBYTE
                else:
                    byteorder = ''
                size = self.elsize
                if self.num == NPY.UNICODE:
                    size >>= 2
                r = space.wrap(byteorder + self.char + str(size))
            else:
                r = self.descr_get_name(space)
        return space.wrap("dtype(%s)" % space.str_w(space.repr(r)))

    def descr_getitem(self, space, w_item):
        if not self.fields:
            raise oefmt(space.w_KeyError, "There are no fields in dtype %s.",
                        self.get_name())
        if space.isinstance_w(w_item, space.w_basestring):
            item = space.str_w(w_item)
        elif space.isinstance_w(w_item, space.w_int):
            indx = space.int_w(w_item)
            try:
                item = self.names[indx]
            except IndexError:
                raise oefmt(space.w_IndexError,
                    "Field index %d out of range.", indx)
        else:
            raise oefmt(space.w_ValueError,
                "Field key must be an integer, string, or unicode.")
        try:
            return self.fields[item][1]
        except KeyError:
            raise oefmt(space.w_KeyError,
                "Field named '%s' not found.", item)

    def descr_len(self, space):
        if not self.fields:
            return space.wrap(0)
        return space.wrap(len(self.fields))

    def runpack_str(self, space, s):
        if self.is_str_or_unicode():
            return self.coerce(space, space.wrap(s))
        return self.itemtype.runpack_str(space, s, self.is_native())

    def store(self, arr, i, offset, value):
        return self.itemtype.store(arr, i, offset, value, self.is_native())

    def read(self, arr, i, offset):
        return self.itemtype.read(arr, i, offset, self)

    def read_bool(self, arr, i, offset):
        return self.itemtype.read_bool(arr, i, offset, self)

    def descr_reduce(self, space):
        w_class = space.type(self)
        builder_args = space.newtuple([
            space.wrap("%s%d" % (self.kind, self.elsize)),
            space.wrap(0), space.wrap(1)])

        version = space.wrap(3)
        endian = self.byteorder
        if endian == NPY.NATIVE:
            endian = NPY.NATBYTE
        subdescr = self.descr_get_subdtype(space)
        names = self.descr_get_names(space)
        values = self.descr_get_fields(space)
        if self.is_flexible():
            w_size = space.wrap(self.elsize)
            w_alignment = space.wrap(self.alignment)
        else:
            w_size = space.wrap(-1)
            w_alignment = space.wrap(-1)
        w_flags = space.wrap(self.flags)

        data = space.newtuple([version, space.wrap(endian), subdescr,
                               names, values, w_size, w_alignment, w_flags])
        return space.newtuple([w_class, builder_args, data])

    def descr_setstate(self, space, w_data):
        if self.fields is None:  # if builtin dtype
            return space.w_None

        version = space.int_w(space.getitem(w_data, space.wrap(0)))
        if version != 3:
            raise oefmt(space.w_ValueError,
                        "can't handle version %d of numpy.dtype pickle",
                        version)

        endian = byteorder_w(space, space.getitem(w_data, space.wrap(1)))
        if endian == NPY.NATBYTE:
            endian = NPY.NATIVE

        w_subarray = space.getitem(w_data, space.wrap(2))
        w_names = space.getitem(w_data, space.wrap(3))
        w_fields = space.getitem(w_data, space.wrap(4))
        size = space.int_w(space.getitem(w_data, space.wrap(5)))
        alignment = space.int_w(space.getitem(w_data, space.wrap(6)))
        flags = space.int_w(space.getitem(w_data, space.wrap(7)))

        if (w_names == space.w_None) != (w_fields == space.w_None):
            raise oefmt(space.w_ValueError, "inconsistent fields and names in Numpy dtype unpickling")

        self.byteorder = endian
        self.shape = []
        self.subdtype = None
        self.base = self

        if w_subarray != space.w_None:
            if not space.isinstance_w(w_subarray, space.w_tuple) or \
                    space.len_w(w_subarray) != 2:
                raise oefmt(space.w_ValueError,
                            "incorrect subarray in __setstate__")
            subdtype, w_shape = space.fixedview(w_subarray)
            assert isinstance(subdtype, W_Dtype)
            if not support.issequence_w(space, w_shape):
                self.shape = [space.int_w(w_shape)]
            else:
                self.shape = [space.int_w(w_s) for w_s in space.fixedview(w_shape)]
            self.subdtype = subdtype
            self.base = subdtype.base

        if w_names != space.w_None:
            self.names = []
            self.fields = {}
            for w_name in space.fixedview(w_names):
                name = space.str_w(w_name)
                value = space.getitem(w_fields, w_name)

                dtype = space.getitem(value, space.wrap(0))
                assert isinstance(dtype, W_Dtype)
                offset = space.int_w(space.getitem(value, space.wrap(1)))

                self.names.append(name)
                self.fields[name] = offset, dtype
            self.itemtype = types.RecordType(space)

        if self.is_flexible():
            self.elsize = size
            self.alignment = alignment
        self.flags = flags

    @unwrap_spec(new_order=str)
    def descr_newbyteorder(self, space, new_order=NPY.SWAP):
        newendian = byteorder_converter(space, new_order)
        endian = self.byteorder
        if endian != NPY.IGNORE:
            if newendian == NPY.SWAP:
                endian = NPY.OPPBYTE if self.is_native() else NPY.NATBYTE
            elif newendian != NPY.IGNORE:
                endian = newendian
        fields = self.fields
        if fields is None:
            fields = {}
        return W_Dtype(self.itemtype,
                       self.w_box_type, byteorder=endian, elsize=self.elsize,
                       names=self.names, fields=fields,
                       shape=self.shape, subdtype=self.subdtype)


@specialize.arg(2)
def dtype_from_list(space, w_lst, simple, align=False):
    lst_w = space.listview(w_lst)
    fields = {}
    offset = 0
    names = []
    maxalign = 0
    for i in range(len(lst_w)):
        w_elem = lst_w[i]
        if simple:
            subdtype = descr__new__(space, space.gettypefor(W_Dtype), w_elem)
            fldname = 'f%d' % i
        else:
            w_shape = space.newtuple([])
            if space.len_w(w_elem) == 3:
                w_fldname, w_flddesc, w_shape = space.fixedview(w_elem)
                if not support.issequence_w(space, w_shape):
                    w_shape = space.newtuple([w_shape])
            else:
                w_fldname, w_flddesc = space.fixedview(w_elem, 2)
            subdtype = descr__new__(space, space.gettypefor(W_Dtype), w_flddesc, w_shape=w_shape)
            fldname = space.str_w(w_fldname)
            if fldname == '':
                fldname = 'f%d' % i
            if fldname in fields:
                raise oefmt(space.w_ValueError, "two fields with the same name")
        assert isinstance(subdtype, W_Dtype)
        fields[fldname] = (offset, subdtype)
        offset += subdtype.elsize
        maxalign = max(subdtype.elsize, maxalign)
        names.append(fldname)
    if align:
        # Set offset to the next power-of-two above offset
        offset = (offset + maxalign -1) & (-maxalign)
    retval = W_Dtype(types.RecordType(space), space.gettypefor(boxes.W_VoidBox),
                   names=names, fields=fields, elsize=offset)
    retval.flags |= NPY.NEEDS_PYAPI
    return retval

def dtype_from_dict(space, w_dict, align):
    def get_list_or_none(key):
        w_key = space.wrap(key)
        if space.is_true(w_dict.descr_has_key(space, w_key)):
            return space.listview(w_dict.descr_getitem(space, w_key))
        return None

    def get_val_or_none(key):
        w_key = space.wrap(key)
        if space.is_true(w_dict.descr_has_key(space, w_key)):
            return w_dict.descr_getitem(space, w_key)
        return None

    names_w = get_list_or_none('names')
    formats_w = get_list_or_none('formats') 
    offsets_w = get_list_or_none('offsets')
    titles_w = get_list_or_none('titles')
    metadata_w = get_list_or_none('metadata')
    aligned_w = get_val_or_none('align')
    if names_w is None or formats_w is None:
        return get_appbridge_cache(space).call_method(space,
            'numpy.core._internal', '_usefields', Arguments(space, [w_dict, space.wrap(align)]))
    n = len(names_w)
    if (n != len(formats_w) or 
        (offsets_w is not None and n != len(ofsets_w)) or
        (titles_w is not None and n != len(titles_w))):
        raise oefmt(space.w_ValueError, "'names', 'formats', 'offsets', and "
            "'titles' dicct entries must have the same length") 
    if aligned_w is not None:
        if space.isinstance(aligned_w, space.bool_w) and space.is_true(aligned_w):
            align = True
        else:
            raise oefmt(space.w_ValueError,
                    "NumPy dtype descriptor includes 'aligned' entry, "
                    "but its value is neither True nor False");
    if offsets_w is not None or titles_w is not None:
        raise oefmt(space.w_NotImplementedError, "'offsets' or "
            "'titles' dicct entries not implemented yet") 
        
    aslist_w = space.newlist([space.newtuple([w_n, w_f]) for w_n, w_f in zip(
        names_w, formats_w)])
    retval = dtype_from_list(space, aslist_w, False, align)
    if metadata_w is not None:
        retval.descr_setmetadata(space, metadata_w)
    retval.flags |= NPY.NEEDS_PYAPI
    return retval 

def dtype_from_spec(space, w_spec):

    if we_are_translated():
        w_lst = get_appbridge_cache(space).call_method(space,
            'numpy.core._internal', '_commastring', Arguments(space, [w_spec]))
    else:
        # testing, handle manually
        if space.eq_w(w_spec, space.wrap('u4,u4,u4')):
            w_lst = space.newlist([space.wrap('u4')]*3)
        if space.eq_w(w_spec, space.wrap('u4,u4,u4')):
            w_lst = space.newlist([space.wrap('u4')]*3)
        else:
            raise oefmt(space.w_RuntimeError,
                    "cannot parse w_spec")
    if not space.isinstance_w(w_lst, space.w_list) or space.len_w(w_lst) < 1:
        raise oefmt(space.w_RuntimeError,
                    "_commastring is not returning a list with len >= 1")
    if space.len_w(w_lst) == 1:
        return descr__new__(space, space.gettypefor(W_Dtype),
                            space.getitem(w_lst, space.wrap(0)))
    else:
        return dtype_from_list(space, w_lst, True)


def _check_for_commastring(s):
    if s[0] in string.digits or s[0] in '<>=|' and s[1] in string.digits:
        return True
    if s[0] == '(' and s[1] == ')' or s[0] in '<>=|' and s[1] == '(' and s[2] == ')':
        return True
    sqbracket = 0
    for c in s:
        if c == ',':
            if sqbracket == 0:
                return True
        elif c == '[':
            sqbracket += 1
        elif c == ']':
            sqbracket -= 1
    return False

@unwrap_spec(align=bool, copy=bool)
def descr__new__(space, w_subtype, w_dtype, align=False, copy=False,
                 w_shape=None, w_metadata=None):

    cache = get_dtype_cache(space)
    def set_metadata_and_copy(dtype, space, w_metadata, copy=False):
        if copy or (dtype in cache.builtin_dtypes and w_metadata is not None):
            dtype = W_Dtype(dtype.itemtype, dtype.w_box_type, dtype.byteorder)
        if w_metadata is not None:
            dtype.descr_set_metadata(space, w_metadata)
        return dtype

    if w_shape is not None and (space.isinstance_w(w_shape, space.w_int) or
                                space.len_w(w_shape) > 0):
        subdtype = descr__new__(space, w_subtype, w_dtype, align, copy, w_metadata=w_metadata)
        assert isinstance(subdtype, W_Dtype)
        size = 1
        if space.isinstance_w(w_shape, space.w_int):
            dim = space.int_w(w_shape)
            if dim == 1:
                return subdtype
            w_shape = space.newtuple([w_shape])
        shape = []
        for w_dim in space.fixedview(w_shape):
            try:
                dim = space.int_w(w_dim)
            except OperationError as e:
                if e.match(space, space.w_OverflowError):
                    raise oefmt(space.w_ValueError, "invalid shape in fixed-type tuple.")
                else:
                    raise
            if dim > 2 ** 32 -1:
                raise oefmt(space.w_ValueError, "invalid shape in fixed-type tuple: "
                      "dimension does not fit into a C int.")
            elif dim < 0:
                raise oefmt(space.w_ValueError, "invalid shape in fixed-type tuple: "
                      "dimension smaller than zero.")
            shape.append(dim)
            size *= dim
        size *= subdtype.elsize
        if size >= 2 ** 31:
            raise oefmt(space.w_ValueError, "invalid shape in fixed-type tuple: "
                  "dtype size in bytes must fit into a C int.")
        return set_metadata_and_copy(W_Dtype(types.VoidType(space),
                       space.gettypefor(boxes.W_VoidBox),
                       shape=shape, subdtype=subdtype, elsize=size),
                    space, w_metadata)

    if space.is_none(w_dtype):
        return cache.w_float64dtype
    if space.isinstance_w(w_dtype, w_subtype):
        return w_dtype
    if space.isinstance_w(w_dtype, space.w_unicode):
        w_dtype = space.wrap(space.str_w(w_dtype))  # may raise if invalid
    if space.isinstance_w(w_dtype, space.w_str):
        name = space.str_w(w_dtype)
        if _check_for_commastring(name):
            return set_metadata(dtype_from_spec(space, w_dtype), space, w_metadata)
        cname = name[1:] if name[0] == NPY.OPPBYTE else name
        try:
            dtype = cache.dtypes_by_name[cname]
        except KeyError:
            pass
        else:
            if name[0] == NPY.OPPBYTE:
                dtype = dtype.descr_newbyteorder(space)
            return dtype
        if name[0] in 'VSUca' or name[0] in '<>=|' and name[1] in 'VSUca':
            return variable_dtype(space, name)
        raise oefmt(space.w_TypeError, 'data type "%s" not understood', name)
    elif space.isinstance_w(w_dtype, space.w_list):
        return set_metadata_and_copy(dtype_from_list(space, w_dtype, False, align=align),
                    space, w_metadata, copy)
    elif space.isinstance_w(w_dtype, space.w_tuple):
        w_dtype0 = space.getitem(w_dtype, space.wrap(0))
        w_dtype1 = space.getitem(w_dtype, space.wrap(1))
        subdtype = descr__new__(space, w_subtype, w_dtype0, align, copy)
        assert isinstance(subdtype, W_Dtype)
        if subdtype.elsize == 0:
            name = "%s%d" % (subdtype.kind, space.int_w(w_dtype1))
            retval = descr__new__(space, w_subtype, space.wrap(name), align, copy)
        else:
            retval = descr__new__(space, w_subtype, w_dtype0, align, copy, w_shape=w_dtype1)
        return set_metadata_and_copy(retval, space, w_metadata, copy)
    elif space.isinstance_w(w_dtype, space.w_dict):
        return set_metadata_and_copy(dtype_from_dict(space, w_dtype, align),
                    space, w_metadata, copy)
    for dtype in cache.builtin_dtypes:
        if dtype.num in cache.alternate_constructors and \
                w_dtype in cache.alternate_constructors[dtype.num]:
            return set_metadata_and_copy(dtype, space, w_metadata, copy)
        if w_dtype is dtype.w_box_type:
            return set_metadata_and_copy(dtype, space, w_metadata, copy)
        if space.isinstance_w(w_dtype, space.w_type) and \
           space.is_true(space.issubtype(w_dtype, dtype.w_box_type)):
            return set_metadata_and_copy(W_Dtype(dtype.itemtype, w_dtype, elsize=0),
                    space, w_metadata, copy)
    if space.isinstance_w(w_dtype, space.w_type):
        return set_metadata_and_copy(cache.w_objectdtype, space, w_metadata, copy)
    raise oefmt(space.w_TypeError, "data type not understood")


W_Dtype.typedef = TypeDef("numpy.dtype",
    __new__ = interp2app(descr__new__),

    type = interp_attrproperty_w("w_box_type", cls=W_Dtype),
    kind = interp_attrproperty("kind", cls=W_Dtype),
    char = interp_attrproperty("char", cls=W_Dtype),
    num = interp_attrproperty("num", cls=W_Dtype),
    byteorder = interp_attrproperty("byteorder", cls=W_Dtype),
    itemsize = interp_attrproperty("elsize", cls=W_Dtype),
    alignment = interp_attrproperty("alignment", cls=W_Dtype),

    name = GetSetProperty(W_Dtype.descr_get_name),
    str = GetSetProperty(W_Dtype.descr_get_str),
    descr = GetSetProperty(W_Dtype.descr_get_descr),
    hasobject = GetSetProperty(W_Dtype.descr_get_hasobject),
    isbuiltin = GetSetProperty(W_Dtype.descr_get_isbuiltin),
    isnative = GetSetProperty(W_Dtype.descr_get_isnative),
    base = GetSetProperty(W_Dtype.descr_get_base),
    subdtype = GetSetProperty(W_Dtype.descr_get_subdtype),
    shape = GetSetProperty(W_Dtype.descr_get_shape),
    fields = GetSetProperty(W_Dtype.descr_get_fields),
    names = GetSetProperty(W_Dtype.descr_get_names,
                           W_Dtype.descr_set_names,
                           W_Dtype.descr_del_names),
    metadata = GetSetProperty(W_Dtype.descr_get_metadata,
                           W_Dtype.descr_set_metadata,
                           W_Dtype.descr_del_metadata),
    flags = GetSetProperty(W_Dtype.descr_get_flags),

    __eq__ = interp2app(W_Dtype.descr_eq),
    __ne__ = interp2app(W_Dtype.descr_ne),
    __lt__ = interp2app(W_Dtype.descr_lt),
    __le__ = interp2app(W_Dtype.descr_le),
    __gt__ = interp2app(W_Dtype.descr_gt),
    __ge__ = interp2app(W_Dtype.descr_ge),
    __hash__ = interp2app(W_Dtype.descr_hash),
    __str__= interp2app(W_Dtype.descr_str),
    __repr__ = interp2app(W_Dtype.descr_repr),
    __getitem__ = interp2app(W_Dtype.descr_getitem),
    __len__ = interp2app(W_Dtype.descr_len),
    __reduce__ = interp2app(W_Dtype.descr_reduce),
    __setstate__ = interp2app(W_Dtype.descr_setstate),
    newbyteorder = interp2app(W_Dtype.descr_newbyteorder),
)
W_Dtype.typedef.acceptable_as_base_class = False


def variable_dtype(space, name):
    if name[0] in '<>=|':
        name = name[1:]
    char = name[0]
    if len(name) == 1:
        size = 0
    else:
        try:
            size = int(name[1:])
        except ValueError:
            raise oefmt(space.w_TypeError, "data type not understood")
    if char == NPY.CHARLTR:
        return W_Dtype(
            types.CharType(space),
            elsize=1,
            w_box_type=space.gettypefor(boxes.W_StringBox))
    elif char == NPY.STRINGLTR or char == NPY.STRINGLTR2:
        return new_string_dtype(space, size)
    elif char == NPY.UNICODELTR:
        return new_unicode_dtype(space, size)
    elif char == NPY.VOIDLTR:
        return new_void_dtype(space, size)
    assert False


def new_string_dtype(space, size):
    return W_Dtype(
        types.StringType(space),
        elsize=size,
        w_box_type=space.gettypefor(boxes.W_StringBox),
    )


def new_unicode_dtype(space, size):
    itemtype = types.UnicodeType(space)
    return W_Dtype(
        itemtype,
        elsize=size * itemtype.get_element_size(),
        w_box_type=space.gettypefor(boxes.W_UnicodeBox),
    )


def new_void_dtype(space, size):
    return W_Dtype(
        types.VoidType(space),
        elsize=size,
        w_box_type=space.gettypefor(boxes.W_VoidBox),
    )


class DtypeCache(object):
    def __init__(self, space):
        self.w_booldtype = W_Dtype(
            types.Bool(space),
            w_box_type=space.gettypefor(boxes.W_BoolBox),
        )
        self.w_int8dtype = W_Dtype(
            types.Int8(space),
            w_box_type=space.gettypefor(boxes.W_Int8Box),
        )
        self.w_uint8dtype = W_Dtype(
            types.UInt8(space),
            w_box_type=space.gettypefor(boxes.W_UInt8Box),
        )
        self.w_int16dtype = W_Dtype(
            types.Int16(space),
            w_box_type=space.gettypefor(boxes.W_Int16Box),
        )
        self.w_uint16dtype = W_Dtype(
            types.UInt16(space),
            w_box_type=space.gettypefor(boxes.W_UInt16Box),
        )
        self.w_int32dtype = W_Dtype(
            types.Int32(space),
            w_box_type=space.gettypefor(boxes.W_Int32Box),
        )
        self.w_uint32dtype = W_Dtype(
            types.UInt32(space),
            w_box_type=space.gettypefor(boxes.W_UInt32Box),
        )
        self.w_longdtype = W_Dtype(
            types.Long(space),
            w_box_type=space.gettypefor(boxes.W_LongBox),
        )
        self.w_ulongdtype = W_Dtype(
            types.ULong(space),
            w_box_type=space.gettypefor(boxes.W_ULongBox),
        )
        self.w_int64dtype = W_Dtype(
            types.Int64(space),
            w_box_type=space.gettypefor(boxes.W_Int64Box),
        )
        self.w_uint64dtype = W_Dtype(
            types.UInt64(space),
            w_box_type=space.gettypefor(boxes.W_UInt64Box),
        )
        self.w_float32dtype = W_Dtype(
            types.Float32(space),
            w_box_type=space.gettypefor(boxes.W_Float32Box),
        )
        self.w_float64dtype = W_Dtype(
            types.Float64(space),
            w_box_type=space.gettypefor(boxes.W_Float64Box),
        )
        self.w_floatlongdtype = W_Dtype(
            types.FloatLong(space),
            w_box_type=space.gettypefor(boxes.W_FloatLongBox),
        )
        self.w_complex64dtype = W_Dtype(
            types.Complex64(space),
            w_box_type=space.gettypefor(boxes.W_Complex64Box),
        )
        self.w_complex128dtype = W_Dtype(
            types.Complex128(space),
            w_box_type=space.gettypefor(boxes.W_Complex128Box),
        )
        self.w_complexlongdtype = W_Dtype(
            types.ComplexLong(space),
            w_box_type=space.gettypefor(boxes.W_ComplexLongBox),
        )
        self.w_stringdtype = W_Dtype(
            types.StringType(space),
            elsize=0,
            w_box_type=space.gettypefor(boxes.W_StringBox),
        )
        self.w_unicodedtype = W_Dtype(
            types.UnicodeType(space),
            elsize=0,
            w_box_type=space.gettypefor(boxes.W_UnicodeBox),
        )
        self.w_voiddtype = W_Dtype(
            types.VoidType(space),
            elsize=0,
            w_box_type=space.gettypefor(boxes.W_VoidBox),
        )
        self.w_float16dtype = W_Dtype(
            types.Float16(space),
            w_box_type=space.gettypefor(boxes.W_Float16Box),
        )
        self.w_objectdtype = W_Dtype(
            types.ObjectType(space),
            w_box_type=space.gettypefor(boxes.W_ObjectBox),
        )
        aliases = {
            NPY.BOOL:        ['bool_', 'bool8'],
            NPY.BYTE:        ['byte'],
            NPY.UBYTE:       ['ubyte'],
            NPY.SHORT:       ['short'],
            NPY.USHORT:      ['ushort'],
            NPY.LONG:        ['int'],
            NPY.ULONG:       ['uint'],
            NPY.LONGLONG:    ['longlong'],
            NPY.ULONGLONG:   ['ulonglong'],
            NPY.FLOAT:       ['single'],
            NPY.DOUBLE:      ['float', 'double'],
            NPY.LONGDOUBLE:  ['longdouble', 'longfloat'],
            NPY.CFLOAT:      ['csingle'],
            NPY.CDOUBLE:     ['complex', 'cfloat', 'cdouble'],
            NPY.CLONGDOUBLE: ['clongdouble', 'clongfloat'],
            NPY.STRING:      ['string_', 'str'],
            NPY.UNICODE:     ['unicode_'],
            NPY.OBJECT:      ['object_'],
        }
        self.alternate_constructors = {
            NPY.BOOL:     [space.w_bool],
            NPY.LONG:     [space.w_int,
                           space.gettypefor(boxes.W_IntegerBox),
                           space.gettypefor(boxes.W_SignedIntegerBox)],
            NPY.ULONG:    [space.gettypefor(boxes.W_UnsignedIntegerBox)],
            NPY.LONGLONG: [space.w_long],
            NPY.DOUBLE:   [space.w_float,
                           space.gettypefor(boxes.W_NumberBox),
                           space.gettypefor(boxes.W_FloatingBox)],
            NPY.CDOUBLE:  [space.w_complex,
                           space.gettypefor(boxes.W_ComplexFloatingBox)],
            NPY.STRING:   [space.w_str,
                           space.gettypefor(boxes.W_CharacterBox)],
            NPY.UNICODE:  [space.w_unicode],
            NPY.VOID:     [space.gettypefor(boxes.W_GenericBox)],
                           #space.w_buffer,  # XXX no buffer in space
            NPY.OBJECT:   [space.gettypefor(boxes.W_ObjectBox),
                           space.w_object],
        }
        float_dtypes = [self.w_float16dtype, self.w_float32dtype,
                        self.w_float64dtype, self.w_floatlongdtype]
        complex_dtypes = [self.w_complex64dtype, self.w_complex128dtype,
                          self.w_complexlongdtype]
        self.component_dtypes = {
            NPY.CFLOAT:      self.w_float32dtype,
            NPY.CDOUBLE:     self.w_float64dtype,
            NPY.CLONGDOUBLE: self.w_floatlongdtype,
        }
        integer_dtypes = [
            self.w_int8dtype, self.w_uint8dtype,
            self.w_int16dtype, self.w_uint16dtype,
            self.w_int32dtype, self.w_uint32dtype,
            self.w_longdtype, self.w_ulongdtype,
            self.w_int64dtype, self.w_uint64dtype]
        self.builtin_dtypes = ([self.w_booldtype] + integer_dtypes +
            float_dtypes + complex_dtypes + [
                self.w_stringdtype, self.w_unicodedtype, self.w_voiddtype,
                self.w_objectdtype,
            ])
        self.integer_dtypes = integer_dtypes
        self.float_dtypes = float_dtypes
        self.complex_dtypes = complex_dtypes
        self.float_dtypes_by_num_bytes = sorted(
            (dtype.elsize, dtype)
            for dtype in float_dtypes
        )
        self.dtypes_by_num = {}
        self.dtypes_by_name = {}
        # we reverse, so the stuff with lower numbers override stuff with
        # higher numbers
        # However, Long/ULong always take precedence over Intxx
        for dtype in reversed(
                [self.w_longdtype, self.w_ulongdtype] + self.builtin_dtypes):
            dtype.fields = None  # mark these as builtin
            self.dtypes_by_num[dtype.num] = dtype
            self.dtypes_by_name[dtype.get_name()] = dtype
            for can_name in [dtype.kind + str(dtype.elsize),
                             dtype.char]:
                self.dtypes_by_name[can_name] = dtype
                self.dtypes_by_name[NPY.NATBYTE + can_name] = dtype
                self.dtypes_by_name[NPY.NATIVE + can_name] = dtype
                self.dtypes_by_name[NPY.IGNORE + can_name] = dtype
            if dtype.num in aliases:
                for alias in aliases[dtype.num]:
                    self.dtypes_by_name[alias] = dtype
        if self.w_longdtype.elsize == self.w_int32dtype.elsize:
            intp_dtype = self.w_int32dtype
            uintp_dtype = self.w_uint32dtype
        else:
            intp_dtype = self.w_longdtype
            uintp_dtype = self.w_ulongdtype
        self.dtypes_by_name['p'] = self.dtypes_by_name['intp'] = intp_dtype
        self.dtypes_by_name['P'] = self.dtypes_by_name['uintp'] = uintp_dtype

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
            'INTP': self.w_longdtype,
            'HALF': self.w_float16dtype,
            'BYTE': self.w_int8dtype,
            #'TIMEDELTA',
            'INT': self.w_int32dtype,
            'DOUBLE': self.w_float64dtype,
            'LONGDOUBLE': self.w_floatlongdtype,
            'USHORT': self.w_uint16dtype,
            'FLOAT': self.w_float32dtype,
            'BOOL': self.w_booldtype,
            'OBJECT': self.w_objectdtype,
        }

        typeinfo_partial = {
            'Generic': boxes.W_GenericBox,
            'Character': boxes.W_CharacterBox,
            'Flexible': boxes.W_FlexibleBox,
            'Inexact': boxes.W_InexactBox,
            'Integer': boxes.W_IntegerBox,
            'SignedInteger': boxes.W_SignedIntegerBox,
            'UnsignedInteger': boxes.W_UnsignedIntegerBox,
            'ComplexFloating': boxes.W_ComplexFloatingBox,
            'Number': boxes.W_NumberBox,
            'Floating': boxes.W_FloatingBox
        }
        w_typeinfo = space.newdict()
        for k, v in typeinfo_partial.iteritems():
            space.setitem(w_typeinfo, space.wrap(k), space.gettypefor(v))
        for k, dtype in typeinfo_full.iteritems():
            itembits = dtype.elsize * 8
            if k in ('INTP', 'UINTP'):
                char = getattr(NPY, k + 'LTR')
            else:
                char = dtype.char
            items_w = [space.wrap(char),
                       space.wrap(dtype.num),
                       space.wrap(itembits),
                       space.wrap(dtype.itemtype.get_element_size())]
            if dtype.is_int():
                if dtype.is_bool():
                    w_maxobj = space.wrap(1)
                    w_minobj = space.wrap(0)
                elif dtype.is_signed():
                    w_maxobj = space.wrap(r_longlong((1 << (itembits - 1))
                                          - 1))
                    w_minobj = space.wrap(r_longlong(-1) << (itembits - 1))
                else:
                    w_maxobj = space.wrap(r_ulonglong(1 << itembits) - 1)
                    w_minobj = space.wrap(0)
                items_w = items_w + [w_maxobj, w_minobj]
            items_w = items_w + [dtype.w_box_type]
            space.setitem(w_typeinfo, space.wrap(k), space.newtuple(items_w))
        self.w_typeinfo = w_typeinfo


def get_dtype_cache(space):
    return space.fromcache(DtypeCache)

@jit.elidable
def num2dtype(space, num):
    return get_dtype_cache(space).dtypes_by_num[num]

def as_dtype(space, w_arg, allow_None=True):
    from pypy.module.micronumpy.casting import scalar2dtype
    # roughly equivalent to CNumPy's PyArray_DescrConverter2
    if not allow_None and space.is_none(w_arg):
        raise TypeError("Cannot create dtype from None here")
    if isinstance(w_arg, W_NDimArray):
        return w_arg.get_dtype()
    elif is_scalar_w(space, w_arg):
        result = scalar2dtype(space, w_arg)
        return result
    else:
        return space.interp_w(W_Dtype,
            space.call_function(space.gettypefor(W_Dtype), w_arg))

def is_scalar_w(space, w_arg):
    return (isinstance(w_arg, boxes.W_GenericBox) or
            space.isinstance_w(w_arg, space.w_int) or
            space.isinstance_w(w_arg, space.w_float) or
            space.isinstance_w(w_arg, space.w_complex) or
            space.isinstance_w(w_arg, space.w_long) or
            space.isinstance_w(w_arg, space.w_bool))

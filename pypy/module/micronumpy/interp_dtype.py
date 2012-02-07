
import sys
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import (TypeDef, GetSetProperty,
    interp_attrproperty, interp_attrproperty_w)
from pypy.module.micronumpy import types, interp_boxes
from pypy.rlib.objectmodel import specialize
from pypy.rlib.rarithmetic import LONG_BIT
from pypy.rpython.lltypesystem import lltype


UNSIGNEDLTR = "u"
SIGNEDLTR = "i"
BOOLLTR = "b"
FLOATINGLTR = "f"
VOID = 'V'


VOID_STORAGE = lltype.Array(lltype.Char, hints={'nolength': True, 'render_as_void': True})

class W_Dtype(Wrappable):
    _immutable_fields_ = ["itemtype", "num", "kind"]

    def __init__(self, itemtype, num, kind, name, char, w_box_type, alternate_constructors=[], aliases=[]):
        self.itemtype = itemtype
        self.num = num
        self.kind = kind
        self.name = name
        self.char = char
        self.w_box_type = w_box_type
        self.alternate_constructors = alternate_constructors
        self.aliases = aliases

    def malloc(self, length):
        # XXX find out why test_zjit explodes with tracking of allocations
        return lltype.malloc(VOID_STORAGE, self.itemtype.get_element_size() * length,
            zero=True, flavor="raw",
            track_allocation=False, add_memory_pressure=True
        )

    @specialize.argtype(1)
    def box(self, value):
        return self.itemtype.box(value)

    def coerce(self, space, w_item):
        return self.itemtype.coerce(space, w_item)

    def getitem(self, storage, i):
        return self.itemtype.read(storage, self.itemtype.get_element_size(), i, 0)

    def getitem_bool(self, storage, i):
        isize = self.itemtype.get_element_size()
        return self.itemtype.read_bool(storage, isize, i, 0)

    def setitem(self, storage, i, box):
        self.itemtype.store(storage, self.itemtype.get_element_size(), i, 0, box)

    def fill(self, storage, box, start, stop):
        self.itemtype.fill(storage, self.itemtype.get_element_size(), box, start, stop, 0)

    def descr__new__(space, w_subtype, w_dtype):
        cache = get_dtype_cache(space)

        if space.is_w(w_dtype, space.w_None):
            return cache.w_float64dtype
        elif space.isinstance_w(w_dtype, w_subtype):
            return w_dtype
        elif space.isinstance_w(w_dtype, space.w_str):
            name = space.str_w(w_dtype)
            try:
                return cache.dtypes_by_name[name]
            except KeyError:
                pass
        elif space.isinstance_w(w_dtype, space.w_list):
            xxx
        else:
            for dtype in cache.builtin_dtypes:
                if w_dtype in dtype.alternate_constructors:
                    return dtype
                if w_dtype is dtype.w_box_type:
                    return dtype
        raise OperationError(space.w_TypeError, space.wrap("data type not understood"))

    def descr_str(self, space):
        return space.wrap(self.name)

    def descr_repr(self, space):
        return space.wrap("dtype('%s')" % self.name)

    def descr_get_itemsize(self, space):
        return space.wrap(self.itemtype.get_element_size())

    def descr_get_shape(self, space):
        return space.newtuple([])

    def eq(self, space, w_other):
        w_other = space.call_function(space.gettypefor(W_Dtype), w_other)
        return space.is_w(self, w_other)

    def descr_eq(self, space, w_other):
        return space.wrap(self.eq(space, w_other))

    def descr_ne(self, space, w_other):
        return space.wrap(not self.eq(space, w_other))

    def is_int_type(self):
        return (self.kind == SIGNEDLTR or self.kind == UNSIGNEDLTR or
                self.kind == BOOLLTR)

    def is_bool_type(self):
        return self.kind == BOOLLTR

W_Dtype.typedef = TypeDef("dtype",
    __module__ = "numpypy",
    __new__ = interp2app(W_Dtype.descr__new__.im_func),

    __str__= interp2app(W_Dtype.descr_str),
    __repr__ = interp2app(W_Dtype.descr_repr),
    __eq__ = interp2app(W_Dtype.descr_eq),
    __ne__ = interp2app(W_Dtype.descr_ne),

    num = interp_attrproperty("num", cls=W_Dtype),
    kind = interp_attrproperty("kind", cls=W_Dtype),
    type = interp_attrproperty_w("w_box_type", cls=W_Dtype),
    itemsize = GetSetProperty(W_Dtype.descr_get_itemsize),
    shape = GetSetProperty(W_Dtype.descr_get_shape),
    name = interp_attrproperty('name', cls=W_Dtype),
)
W_Dtype.typedef.acceptable_as_base_class = False

if sys.byteorder == 'little':
    byteorder_prefix = '<'
    nonnative_byteorder_prefix = '>'
else:
    byteorder_prefix = '>'
    nonnative_byteorder_prefix = '<'

class DtypeCache(object):
    def __init__(self, space):
        self.w_booldtype = W_Dtype(
            types.Bool(),
            num=0,
            kind=BOOLLTR,
            name="bool",
            char="?",
            w_box_type=space.gettypefor(interp_boxes.W_BoolBox),
            alternate_constructors=[space.w_bool],
        )
        self.w_int8dtype = W_Dtype(
            types.Int8(),
            num=1,
            kind=SIGNEDLTR,
            name="int8",
            char="b",
            w_box_type=space.gettypefor(interp_boxes.W_Int8Box)
        )
        self.w_uint8dtype = W_Dtype(
            types.UInt8(),
            num=2,
            kind=UNSIGNEDLTR,
            name="uint8",
            char="B",
            w_box_type=space.gettypefor(interp_boxes.W_UInt8Box),
        )
        self.w_int16dtype = W_Dtype(
            types.Int16(),
            num=3,
            kind=SIGNEDLTR,
            name="int16",
            char="h",
            w_box_type=space.gettypefor(interp_boxes.W_Int16Box),
        )
        self.w_uint16dtype = W_Dtype(
            types.UInt16(),
            num=4,
            kind=UNSIGNEDLTR,
            name="uint16",
            char="H",
            w_box_type=space.gettypefor(interp_boxes.W_UInt16Box),
        )
        self.w_int32dtype = W_Dtype(
            types.Int32(),
            num=5,
            kind=SIGNEDLTR,
            name="int32",
            char="i",
            w_box_type=space.gettypefor(interp_boxes.W_Int32Box),
       )
        self.w_uint32dtype = W_Dtype(
            types.UInt32(),
            num=6,
            kind=UNSIGNEDLTR,
            name="uint32",
            char="I",
            w_box_type=space.gettypefor(interp_boxes.W_UInt32Box),
        )
        if LONG_BIT == 32:
            name = "int32"
        elif LONG_BIT == 64:
            name = "int64"
        self.w_longdtype = W_Dtype(
            types.Long(),
            num=7,
            kind=SIGNEDLTR,
            name=name,
            char="l",
            w_box_type=space.gettypefor(interp_boxes.W_LongBox),
            alternate_constructors=[space.w_int],
        )
        self.w_ulongdtype = W_Dtype(
            types.ULong(),
            num=8,
            kind=UNSIGNEDLTR,
            name="u" + name,
            char="L",
            w_box_type=space.gettypefor(interp_boxes.W_ULongBox),
        )
        self.w_int64dtype = W_Dtype(
            types.Int64(),
            num=9,
            kind=SIGNEDLTR,
            name="int64",
            char="q",
            w_box_type=space.gettypefor(interp_boxes.W_Int64Box),
        )
        self.w_uint64dtype = W_Dtype(
            types.UInt64(),
            num=10,
            kind=UNSIGNEDLTR,
            name="uint64",
            char="Q",
            w_box_type=space.gettypefor(interp_boxes.W_UInt64Box),
        )
        self.w_float32dtype = W_Dtype(
            types.Float32(),
            num=11,
            kind=FLOATINGLTR,
            name="float32",
            char="f",
            w_box_type=space.gettypefor(interp_boxes.W_Float32Box),
        )
        self.w_float64dtype = W_Dtype(
            types.Float64(),
            num=12,
            kind=FLOATINGLTR,
            name="float64",
            char="d",
            w_box_type = space.gettypefor(interp_boxes.W_Float64Box),
            alternate_constructors=[space.w_float],
            aliases=["float"],
        )
        self.w_longlongdtype = W_Dtype(
            types.Int64(),
            num=9,
            kind=SIGNEDLTR,
            name='int64',
            char='q',
            w_box_type = space.gettypefor(interp_boxes.W_LongLongBox),
            alternate_constructors=[space.w_long],
        )
        self.w_ulonglongdtype = W_Dtype(
            types.UInt64(),
            num=10,
            kind=UNSIGNEDLTR,
            name='uint64',
            char='Q',
            w_box_type = space.gettypefor(interp_boxes.W_ULongLongBox),
        )
        self.builtin_dtypes = [
            self.w_booldtype, self.w_int8dtype, self.w_uint8dtype,
            self.w_int16dtype, self.w_uint16dtype, self.w_int32dtype,
            self.w_uint32dtype, self.w_longdtype, self.w_ulongdtype,
            self.w_longlongdtype, self.w_ulonglongdtype,
            self.w_float32dtype,
            self.w_float64dtype
        ]
        self.dtypes_by_num_bytes = sorted(
            (dtype.itemtype.get_element_size(), dtype)
            for dtype in self.builtin_dtypes
        )
        self.dtypes_by_name = {}
        for dtype in self.builtin_dtypes:
            self.dtypes_by_name[dtype.name] = dtype
            can_name = dtype.kind + str(dtype.itemtype.get_element_size())
            self.dtypes_by_name[can_name] = dtype
            self.dtypes_by_name[byteorder_prefix + can_name] = dtype
            new_name = nonnative_byteorder_prefix + can_name
            itemtypename = dtype.itemtype.__class__.__name__
            self.dtypes_by_name[new_name] = W_Dtype(
                getattr(types, 'NonNative' + itemtypename)(),
                dtype.num, dtype.kind, new_name, dtype.char, dtype.w_box_type)
            for alias in dtype.aliases:
                self.dtypes_by_name[alias] = dtype
            self.dtypes_by_name[dtype.char] = dtype

def get_dtype_cache(space):
    return space.fromcache(DtypeCache)

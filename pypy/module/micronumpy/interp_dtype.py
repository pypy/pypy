from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty, interp_attrproperty
from pypy.module.micronumpy import types, signature
from pypy.rlib.objectmodel import specialize
from pypy.rlib.rarithmetic import LONG_BIT
from pypy.rpython.lltypesystem import lltype, rffi


STORAGE_TYPE = lltype.Array(lltype.Char, hints={"nolength": True})

UNSIGNEDLTR = "u"
SIGNEDLTR = "i"
BOOLLTR = "b"
FLOATINGLTR = "f"

class W_Dtype(Wrappable):
    def __init__(self, itemtype, num, kind, name, char, alternate_constructors=[]):
        self.signature = signature.BaseSignature()
        self.itemtype = itemtype
        self.num = num
        self.kind = kind
        self.name = name
        self.char = char
        self.alternate_constructors = alternate_constructors

    def malloc(self, length):
        # XXX find out why test_zjit explodes with tracking of allocations
        return lltype.malloc(STORAGE_TYPE, self.itemtype.get_element_size() * length,
            zero=True, flavor="raw",
            track_allocation=False, add_memory_pressure=True
        )

    @specialize.argtype(1)
    def box(self, value):
        return self.itemtype.box(value)

    def coerce(self, space, w_item):
        return self.itemtype.coerce(space, w_item)

    def getitem(self, storage, i):
        struct_ptr = rffi.ptradd(storage, i * self.itemtype.get_element_size())
        return self.itemtype.read(struct_ptr, 0)

    def setitem(self, storage, i, box):
        struct_ptr = rffi.ptradd(storage, i * self.itemtype.get_element_size())
        self.itemtype.store(struct_ptr, 0, box)

    def fill(self, storage, box, start, stop):
        start_ptr = rffi.ptradd(storage, start * self.itemtype.get_element_size())
        self.itemtype.fill(start_ptr, box, stop - start)

    def descr__new__(space, w_subtype, w_dtype):
        cache = get_dtype_cache(space)

        if space.is_w(w_dtype, space.w_None):
            return cache.w_float64dtype
        elif space.isinstance_w(w_dtype, w_subtype):
            return w_dtype
        elif space.isinstance_w(w_dtype, space.w_str):
            name = space.str_w(w_dtype)
            for dtype in cache.builtin_dtypes:
                if dtype.name == name or dtype.char == name:
                    return dtype
        else:
            for dtype in cache.builtin_dtypes:
                if w_dtype in dtype.alternate_constructors:
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

W_Dtype.typedef = TypeDef("dtype",
    __module__ = "numpy",
    __new__ = interp2app(W_Dtype.descr__new__.im_func),

    __str__= interp2app(W_Dtype.descr_str),
    __repr__ = interp2app(W_Dtype.descr_repr),

    num = interp_attrproperty("num", cls=W_Dtype),
    kind = interp_attrproperty("kind", cls=W_Dtype),
    itemsize = GetSetProperty(W_Dtype.descr_get_itemsize),
    shape = GetSetProperty(W_Dtype.descr_get_shape),
)
W_Dtype.typedef.acceptable_as_base_class = False

class DtypeCache(object):
    def __init__(self, space):
        self.w_booldtype = W_Dtype(
            types.Bool(),
            num=0,
            kind=BOOLLTR,
            name="bool",
            char="?",
            alternate_constructors=[space.w_bool],
        )
        self.w_int8dtype = W_Dtype(
            types.Int8(),
            num=1,
            kind=SIGNEDLTR,
            name="int8",
            char="b",
        )
        self.w_uint8dtype = W_Dtype(
            types.UInt8(),
            num=2,
            kind=UNSIGNEDLTR,
            name="uint8",
            char="B",
        )
        self.w_int16dtype = W_Dtype(
            types.Int16(),
            num=3,
            kind=SIGNEDLTR,
            name="int16",
            char="h",
        )
        self.w_uint16dtype = W_Dtype(
            types.UInt16(),
            num=4,
            kind=UNSIGNEDLTR,
            name="uint16",
            char="H",
        )
        self.w_int32dtype = W_Dtype(
            types.Int32(),
            num=5,
            kind=SIGNEDLTR,
            name="int32",
            char="i",
        )
        self.w_uint32dtype = W_Dtype(
            types.UInt32(),
            num=6,
            kind=UNSIGNEDLTR,
            name="uint32",
            char="I",
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
            alternate_constructors=[space.w_int],
        )
        self.w_ulongdtype = W_Dtype(
            types.ULong(),
            num=8,
            kind=UNSIGNEDLTR,
            name="u" + name,
            char="L",
        )
        self.w_int64dtype = W_Dtype(
            types.Int64(),
            num=9,
            kind=SIGNEDLTR,
            name="int64",
            char="q",
            alternate_constructors=[space.w_long],
        )
        self.w_uint64dtype = W_Dtype(
            types.UInt64(),
            num=10,
            kind=UNSIGNEDLTR,
            name="uint64",
            char="Q",
        )
        self.w_float32dtype = W_Dtype(
            types.Float32(),
            num=11,
            kind=FLOATINGLTR,
            name="float32",
            char="f",
        )
        self.w_float64dtype = W_Dtype(
            types.Float64(),
            num=12,
            kind=FLOATINGLTR,
            name="float32",
            char="d",
            alternate_constructors=[space.w_float],
        )

        self.builtin_dtypes = [
            self.w_booldtype, self.w_int8dtype, self.w_uint8dtype,
            self.w_int16dtype, self.w_uint16dtype, self.w_int32dtype,
            self.w_uint32dtype, self.w_longdtype, self.w_ulongdtype,
            self.w_int64dtype, self.w_uint64dtype, self.w_float32dtype,
            self.w_float64dtype
        ]
        self.dtypes_by_num_bytes = sorted(
            (dtype.itemtype.get_element_size(), dtype)
            for dtype in self.builtin_dtypes
        )

def get_dtype_cache(space):
    return space.fromcache(DtypeCache)
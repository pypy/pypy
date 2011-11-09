from pypy.interpreter.baseobjspace import Wrappable
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
    def __init__(self, itemtype, num, kind):
        self.signature = signature.BaseSignature()
        self.itemtype = itemtype
        self.num = num
        self.kind = kind

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


class DtypeCache(object):
    def __init__(self, space):
        self.w_booldtype = W_Dtype(
            types.Bool(),
            num=0,
            kind=BOOLLTR,
        )
        self.w_int8dtype = W_Dtype(
            types.Int8(),
            num=1,
            kind=SIGNEDLTR,
        )
        self.w_uint8dtype = W_Dtype(
            types.UInt8(),
            num=2,
            kind=UNSIGNEDLTR,
        )
        self.w_int16dtype = W_Dtype(
            types.Int16(),
            num=3,
            kind=SIGNEDLTR,
        )
        self.w_uint16dtype = W_Dtype(
            types.UInt16(),
            num=4,
            kind=UNSIGNEDLTR,
        )
        self.w_int32dtype = W_Dtype(
            types.Int32(),
            num=5,
            kind=SIGNEDLTR,
        )
        self.w_uint32dtype = W_Dtype(
            types.UInt32(),
            num=6,
            kind=UNSIGNEDLTR,
        )
        if LONG_BIT == 32:
            longtype = types.Int32()
            unsigned_longtype = types.UInt32()
        elif LONG_BIT == 64:
            longtype = types.Int64()
            unsigned_longtype = types.UInt64()
        self.w_longdtype = W_Dtype(
            longtype,
            num=7,
            kind=SIGNEDLTR,
        )
        self.w_ulongdtype = W_Dtype(
            unsigned_longtype,
            num=8,
            kind=UNSIGNEDLTR,
        )
        self.w_int64dtype = W_Dtype(
            types.Int64(),
            num=9,
            kind=SIGNEDLTR,
        )
        self.w_uint64dtype = W_Dtype(
            types.UInt64(),
            num=10,
            kind=UNSIGNEDLTR,
        )
        self.w_float32dtype = W_Dtype(
            types.Float32(),
            num=11,
            kind=FLOATINGLTR,
        )
        self.w_float64dtype = W_Dtype(
            types.Float64(),
            num=12,
            kind=FLOATINGLTR,
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
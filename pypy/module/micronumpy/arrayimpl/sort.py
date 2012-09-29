
""" This is the implementation of various sorting routines in numpy. It's here
because it only makes sense on a concrete array
"""

from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib.listsort import make_timsort_class
from pypy.rlib.objectmodel import specialize
from pypy.rlib.rawstorage import raw_storage_getitem, raw_storage_setitem

from pypy.interpreter.error import OperationError
from pypy.module.micronumpy.base import W_NDimArray
from pypy.module.micronumpy import interp_dtype, types

INT_SIZE = rffi.sizeof(lltype.Signed)

@specialize.memo()
def make_sort_classes(space, itemtype):
    TP = itemtype.T
    
    class ArgArrayRepresentation(object):
        def __init__(self, itemsize, size, values, indexes):
            self.itemsize = itemsize
            self.size = size
            self.values = values
            self.indexes = indexes

        def getitem(self, item):
            v = raw_storage_getitem(TP, self.values, item * self.itemsize)
            v = itemtype.for_computation(v)
            return (v, raw_storage_getitem(lltype.Signed, self.indexes,
                                           item * INT_SIZE))

        def setitem(self, idx, item):
            raw_storage_setitem(self.values, idx * self.itemsize,
                                rffi.cast(TP, item[0]))
            raw_storage_setitem(self.indexes, idx * INT_SIZE, item[1])

    def arg_getitem(lst, item):
        return lst.getitem(item)

    def arg_setitem(lst, item, value):
        lst.setitem(item, value)

    def arg_length(lst):
        return lst.size

    def arg_getitem_slice(lst, start, stop):
        xxx

    def arg_lt(a, b):
        return a[0] < b[0]

    ArgSort = make_timsort_class(arg_getitem, arg_setitem, arg_length,
                                 arg_getitem_slice, arg_lt)

    return ArgArrayRepresentation, ArgSort

def sort_array(arr, space):
    itemtype = arr.dtype.itemtype
    if (not isinstance(itemtype, types.Float) and
        not isinstance(itemtype, types.Integer)):
        raise OperationError(space.w_NotImplementedError,
           space.wrap("sorting of non-numeric types is not implemented"))
    itemsize = itemtype.get_element_size()
    # create array of indexes
    dtype = interp_dtype.get_dtype_cache(space).w_longdtype
    indexes = W_NDimArray.from_shape([arr.get_size()], dtype)
    storage = indexes.implementation.get_storage()
    for i in range(arr.get_size()):
        raw_storage_setitem(storage, i * INT_SIZE, i)
    Repr, Sort = make_sort_classes(space, itemtype)
    r = Repr(itemsize, arr.get_size(), arr.get_storage(),
             indexes.implementation.get_storage())
    Sort(r).sort()
    return indexes

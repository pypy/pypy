
""" This is the implementation of various sorting routines in numpy. It's here
because it only makes sense on a concrete array
"""

from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib.listsort import make_timsort_class
from rpython.rlib.rawstorage import raw_storage_getitem, raw_storage_setitem, \
        free_raw_storage, alloc_raw_storage
from pypy.interpreter.error import OperationError
from pypy.module.micronumpy.base import W_NDimArray
from pypy.module.micronumpy import interp_dtype, types
from pypy.module.micronumpy.iter import AxisIterator

INT_SIZE = rffi.sizeof(lltype.Signed)

def make_sort_classes(space, itemtype):
    TP = itemtype.T
    
    class ArgArrayRepresentation(object):
        def __init__(self, index_stride_size, stride_size, size, values,
                     indexes, index_start, start):
            self.index_stride_size = index_stride_size
            self.stride_size = stride_size
            self.index_start = index_start
            self.start = start
            self.size = size
            self.values = values
            self.indexes = indexes

        def getitem(self, item):
            v = raw_storage_getitem(TP, self.values, item * self.stride_size
                                    + self.start)
            v = itemtype.for_computation(v)
            return (v, raw_storage_getitem(lltype.Signed, self.indexes,
                                           item * self.index_stride_size +
                                           self.index_start))

        def setitem(self, idx, item):
            raw_storage_setitem(self.values, idx * self.stride_size +
                                self.start, rffi.cast(TP, item[0]))
            raw_storage_setitem(self.indexes, idx * self.index_stride_size +
                                self.index_start, item[1])
    class ArgArrayRepWithStorage(ArgArrayRepresentation):
        def __init__(self, index_stride_size, stride_size, size):
            start = 0
            dtype = interp_dtype.get_dtype_cache(space).w_longdtype
            self.indexes = dtype.itemtype.malloc(size*dtype.get_size())
            self.values = alloc_raw_storage(size*rffi.sizeof(TP), track_allocation=False)
            ArgArrayRepresentation.__init__(self, index_stride_size, stride_size, 
                    size, self.values, self.indexes, start, start)

        def __del__(self):
            free_raw_storage(self.indexes, track_allocation=False)
            free_raw_storage(self.values, track_allocation=False)

    def arg_getitem(lst, item):
        return lst.getitem(item)

    def arg_setitem(lst, item, value):
        lst.setitem(item, value)

    def arg_length(lst):
        return lst.size

    def arg_getitem_slice(lst, start, stop):
        retval = ArgArrayRepWithStorage(lst.index_stride_size, lst.stride_size,
                stop-start)
        for i in range(stop-start):
            retval.setitem(i, lst.getitem(i+start))
        return retval

    def arg_lt(a, b):
        return a[0] < b[0]

    ArgSort = make_timsort_class(arg_getitem, arg_setitem, arg_length,
                                 arg_getitem_slice, arg_lt)

    return ArgArrayRepresentation, ArgSort

def argsort_array(arr, space, w_axis):
    space.fromcache(SortCache) # that populates SortClasses
    itemtype = arr.dtype.itemtype
    if itemtype.Sort is None:
        # XXX this should probably be changed
        raise OperationError(space.w_NotImplementedError,
               space.wrap("sorting of non-numeric types " + \
                      "'%s' is not implemented" % arr.dtype.get_name(), ))
    if w_axis is space.w_None:
        # note that it's fine ot pass None here as we're not going
        # to pass the result around (None is the link to base in slices)
        arr = arr.reshape(space, None, [arr.get_size()])
        axis = 0
    elif w_axis is None:
        axis = -1
    else:
        axis = space.int_w(w_axis)
    Repr = itemtype.SortRepr
    Sort = itemtype.Sort
    itemsize = itemtype.get_element_size()
    # create array of indexes
    dtype = interp_dtype.get_dtype_cache(space).w_longdtype
    index_arr = W_NDimArray.from_shape(arr.get_shape(), dtype)
    storage = index_arr.implementation.get_storage()
    if len(arr.get_shape()) == 1:
        for i in range(arr.get_size()):
            raw_storage_setitem(storage, i * INT_SIZE, i)
        r = Repr(INT_SIZE, itemsize, arr.get_size(), arr.get_storage(),
                 storage, 0, arr.start)
        Sort(r).sort()
    else:
        shape = arr.get_shape()
        if axis < 0:
            axis = len(shape) + axis - 1
        if axis < 0 or axis > len(shape):
            raise OperationError(space.w_IndexError, space.wrap(
                                                "Wrong axis %d" % axis))
        iterable_shape = shape[:axis] + [0] + shape[axis + 1:]
        iter = AxisIterator(arr, iterable_shape, axis, False)
        index_impl = index_arr.implementation
        index_iter = AxisIterator(index_impl, iterable_shape, axis, False)
        stride_size = arr.strides[axis]
        index_stride_size = index_impl.strides[axis]
        axis_size = arr.shape[axis]
        while not iter.done():
            for i in range(axis_size):
                raw_storage_setitem(storage, i * index_stride_size +
                                    index_iter.offset, i)
            r = Repr(index_stride_size, stride_size, axis_size,
                     arr.get_storage(), storage, index_iter.offset, iter.offset)
            Sort(r).sort()
            iter.next()
            index_iter.next()
    return index_arr

class SortCache(object):
    built = False
    
    def __init__(self, space):
        if self.built:
            return
        for cls in types.all_float_types:
            cls.SortRepr, cls.Sort = make_sort_classes(space, cls)
        for cls in types.all_int_types:
            cls.SortRepr, cls.Sort = make_sort_classes(space, cls)
        for cls in types.all_complex_types:
            cls.SortRepr, cls.Sort = make_sort_classes(space, cls)

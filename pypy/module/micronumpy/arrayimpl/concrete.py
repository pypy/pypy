
from pypy.module.micronumpy.arrayimpl import base
from pypy.module.micronumpy import support
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.rlib import jit

class ConcreteArrayIterator(base.BaseArrayIterator):
    def __init__(self, array):
        self.array = array
        self.offset = 0
        self.dtype = array.dtype
        self.element_size = array.dtype.get_size()
        self.size = array.size

    def setitem(self, elem):
        self.dtype.setitem(self.array, self.offset, elem)

    def getitem(self):
        return self.array.getitem(self.offset)

    def next(self):
        self.offset += self.element_size

    def done(self):
        return self.offset >= self.size

def calc_strides(shape, dtype, order):
    strides = []
    backstrides = []
    s = 1
    shape_rev = shape[:]
    if order == 'C':
        shape_rev.reverse()
    for sh in shape_rev:
        strides.append(s * dtype.get_size())
        backstrides.append(s * (sh - 1) * dtype.get_size())
        s *= sh
    if order == 'C':
        strides.reverse()
        backstrides.reverse()
    return strides, backstrides

def int_w(space, w_obj):
    # a special version that respects both __index__ and __int__
    # XXX add __index__ support
    return space.int_w(space.int(w_obj))

class ConcreteArray(base.BaseArrayImplementation):
    start = 0
    
    def __init__(self, shape, dtype, order):
        self.shape = shape
        self.size = support.product(shape) * dtype.get_size()
        self.storage = dtype.itemtype.malloc(self.size)
        self.strides, self.backstrides = calc_strides(shape, dtype, order)
        self.order = order
        self.dtype = dtype

    def get_shape(self):
        return self.shape

    def create_iter(self):
        return ConcreteArrayIterator(self)

    def getitem(self, index):
        return self.dtype.getitem(self, index)

    # -------------------- applevel get/setitem -----------------------

    @jit.unroll_safe
    def _lookup_by_index(self, space, view_w):
        item = self.start
        for i, w_index in enumerate(view_w):
            if space.isinstance_w(w_index, space.w_slice):
                raise IndexError
            idx = int_w(space, w_index)
            if idx < 0:
                idx = self.shape[i] + id
            if idx < 0 or idx >= self.shape[0]:
                raise operationerrfmt(space.w_IndexError,
                      "index (%d) out of range (0<=index<%d", i, self.shape[i],
                )
            item += idx * self.strides[i]
        return item

    def _single_item_index(self, space, w_idx):
        """ Return an index of single item if possible, otherwise raises
        IndexError
        """
        if (space.isinstance_w(w_idx, space.w_str) or
            space.isinstance_w(w_idx, space.w_slice) or
            space.is_w(w_idx, space.w_None)):
            raise IndexError
        shape_len = len(self.shape)
        if shape_len == 0:
            raise OperationError(space.w_IndexError, space.wrap(
                "0-d arrays can't be indexed"))
        if space.isinstance_w(w_idx, space.w_tuple):
            view_w = space.fixedview(w_idx)
            if len(view_w) < shape_len:
                raise IndexError
            if len(view_w) > shape_len:
                raise OperationError(space.w_IndexError,
                                     space.wrap("invalid index"))
            return self._lookup_by_index(space, view_w)
        idx = int_w(space, w_idx)
        return self._lookup_by_index(space, [space.wrap(idx)])

    def descr_getitem(self, space, w_index):
        try:
            item = self._single_item_index(space, w_index)
            return self.getitem(item)
        except IndexError:
            # not a single result
            chunks = self._prepare_slice_args(space, w_index)
            return chunks.apply(self)


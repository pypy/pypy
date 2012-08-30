
from pypy.module.micronumpy.arrayimpl import base
from pypy.module.micronumpy import support, loop
from pypy.module.micronumpy.strides import calc_new_strides
from pypy.module.micronumpy.iter import Chunk, Chunks, NewAxisChunk, RecordChunk
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.rlib import jit

class ConcreteArrayIterator(base.BaseArrayIterator):
    def __init__(self, array):
        self.array = array
        self.offset = 0
        self.dtype = array.dtype
        self.skip = self.dtype.itemtype.get_element_size()
        self.size = array.size

    def setitem(self, elem):
        self.array.setitem(self.offset, elem)

    def getitem(self):
        return self.array.getitem(self.offset)

    def next(self):
        self.offset += self.skip

    def done(self):
        return self.offset >= self.size

class OneDimViewIterator(ConcreteArrayIterator):
    def __init__(self, array):
        self.array = array
        self.offset = array.start
        self.skip = array.strides[0]
        self.dtype = array.dtype
        self.index = 0
        self.size = array.shape[0]

    def next(self):
        self.offset += self.skip
        self.index += 1

    def done(self):
        return self.index >= self.size

class MultiDimViewIterator(ConcreteArrayIterator):
    def __init__(self, array):
        self.indexes = [0] * len(array.shape)
        self.array = array
        self.shape = array.shape
        self.offset = array.start
        self.shapelen = len(self.shape)
        self._done = False
        self.strides = array.strides
        self.backstrides = array.backstrides

    @jit.unroll_safe
    def next(self):
        offset = self.offset
        for i in range(self.shapelen - 1, -1, -1):
            if self.indexes[i] < self.shape[i] - 1:
                self.indexes[i] += 1
                offset += self.strides[i]
                break
            else:
                self.indexes[i] = 0
                offset -= self.backstrides[i]
        else:
            self._done = True
        self.offset = offset

    def done(self):
        return self._done


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
    try:
        return space.int_w(space.index(w_obj))
    except OperationError:
        return space.int_w(space.int(w_obj))

class ConcreteArray(base.BaseArrayImplementation):
    start = 0
    parent = None
    
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

    def setitem(self, index, value):
        self.dtype.setitem(self, index, value)

    def fill(self, box):
        self.dtype.fill(self.storage, box, 0, self.size)

    def copy(self):
        impl = ConcreteArray(self.shape, self.dtype, self.order)
        return loop.setslice(impl, self)

    def setslice(self, arr):
        if arr.is_scalar():
            self.fill(arr.get_scalar_value())
            return
        assert isinstance(arr, ConcreteArray)
        if arr.storage == self.storage:
            arr = arr.copy()
        loop.setslice(self, arr)

    def get_size(self):
        return self.size // self.dtype.itemtype.get_element_size()


    def reshape(self, space, new_shape):
        # Since we got to here, prod(new_shape) == self.size
        new_strides = None
        if self.size > 0:
            new_strides = calc_new_strides(new_shape, self.shape,
                                           self.strides, self.order)
        if new_strides:
            # We can create a view, strides somehow match up.
            ndims = len(new_shape)
            new_backstrides = [0] * ndims
            for nd in range(ndims):
                new_backstrides[nd] = (new_shape[nd] - 1) * new_strides[nd]
            return SliceArray(self.start, new_strides, new_backstrides,
                              new_shape, self)
        else:
            return None

    # -------------------- applevel get/setitem -----------------------

    @jit.unroll_safe
    def _lookup_by_index(self, space, view_w):
        item = self.start
        for i, w_index in enumerate(view_w):
            if space.isinstance_w(w_index, space.w_slice):
                raise IndexError
            idx = int_w(space, w_index)
            if idx < 0:
                idx = self.shape[i] + idx
            if idx < 0 or idx >= self.shape[i]:
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

    @jit.unroll_safe
    def _prepare_slice_args(self, space, w_idx):
        if space.isinstance_w(w_idx, space.w_str):
            idx = space.str_w(w_idx)
            dtype = self.find_dtype()
            if not dtype.is_record_type() or idx not in dtype.fields:
                raise OperationError(space.w_ValueError, space.wrap(
                    "field named %s not defined" % idx))
            return RecordChunk(idx)
        if (space.isinstance_w(w_idx, space.w_int) or
            space.isinstance_w(w_idx, space.w_slice)):
            return Chunks([Chunk(*space.decode_index4(w_idx, self.shape[0]))])
        elif space.is_w(w_idx, space.w_None):
            return Chunks([NewAxisChunk()])
        result = []
        i = 0
        for w_item in space.fixedview(w_idx):
            if space.is_w(w_item, space.w_None):
                result.append(NewAxisChunk())
            else:
                result.append(Chunk(*space.decode_index4(w_item,
                                                         self.shape[i])))
                i += 1
        return Chunks(result)

    def descr_getitem(self, space, w_index):
        try:
            item = self._single_item_index(space, w_index)
            return self.getitem(item)
        except IndexError:
            # not a single result
            chunks = self._prepare_slice_args(space, w_index)
            return chunks.apply(self)

    def descr_setitem(self, space, w_index, w_value):
        try:
            item = self._single_item_index(space, w_index)
            self.setitem(item, self.dtype.coerce(space, w_value))
        except IndexError:
            w_value = support.convert_to_array(space, w_value)
            chunks = self._prepare_slice_args(space, w_index)
            view = chunks.apply(self)
            view.implementation.setslice(w_value.implementation)

    def transpose(self):
        if len(self.shape) < 2:
            return self
        strides = []
        backstrides = []
        shape = []
        for i in range(len(self.shape) - 1, -1, -1):
            strides.append(self.strides[i])
            backstrides.append(self.backstrides[i])
            shape.append(self.shape[i])
        return SliceArray(self.start, strides,
                          backstrides, shape, self)

class SliceArray(ConcreteArray):
    def __init__(self, start, strides, backstrides, shape, parent):
        self.strides = strides
        self.backstrides = backstrides
        self.shape = shape
        self.parent = parent
        self.storage = parent.storage
        self.order = parent.order
        self.dtype = parent.dtype
        self.size = support.product(shape) * self.dtype.itemtype.get_element_size()
        self.start = start

    def fill(self, box):
        loop.fill(self, box)

    def create_iter(self):
        if len(self.shape) == 1:
            return OneDimViewIterator(self)
        return MultiDimViewIterator(self)

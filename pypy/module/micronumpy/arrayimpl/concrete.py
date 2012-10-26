
from pypy.module.micronumpy.arrayimpl import base
from pypy.module.micronumpy import support, loop
from pypy.module.micronumpy.base import convert_to_array, W_NDimArray,\
     ArrayArgumentException
from pypy.module.micronumpy.strides import calc_new_strides, shape_agreement,\
     calculate_broadcast_strides, calculate_dot_strides
from pypy.module.micronumpy.iter import Chunk, Chunks, NewAxisChunk, RecordChunk
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib import jit
from pypy.rlib.rawstorage import free_raw_storage
from pypy.module.micronumpy.arrayimpl.sort import argsort_array

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

    def getitem_bool(self):
        return self.dtype.getitem_bool(self.array, self.offset)

    def next(self):
        self.offset += self.skip

    def next_skip_x(self, x):
        self.offset += self.skip * x

    def done(self):
        return self.offset >= self.size

    def reset(self):
        self.offset %= self.size

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

    def next_skip_x(self, x):
        self.offset += self.skip * x
        self.index += x

    def done(self):
        return self.index >= self.size

    def reset(self):
        self.offset %= self.size

class MultiDimViewIterator(ConcreteArrayIterator):
    def __init__(self, array, start, strides, backstrides, shape):
        self.indexes = [0] * len(shape)
        self.array = array
        self.shape = shape
        self.offset = start
        self.shapelen = len(shape)
        self._done = False
        self.strides = strides
        self.backstrides = backstrides
        self.size = array.size

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

    @jit.unroll_safe
    def next_skip_x(self, step):
        for i in range(len(self.shape) - 1, -1, -1):
            if self.indexes[i] < self.shape[i] - step:
                self.indexes[i] += step
                self.offset += self.strides[i] * step
                break
            else:
                remaining_step = (self.indexes[i] + step) // self.shape[i]
                this_i_step = step - remaining_step * self.shape[i]
                self.offset += self.strides[i] * this_i_step
                self.indexes[i] = self.indexes[i] +  this_i_step
                step = remaining_step
        else:
            self._done = True

    def done(self):
        return self._done

    def reset(self):
        self.offset %= self.size

class AxisIterator(base.BaseArrayIterator):
    def __init__(self, array, shape, dim):
        self.shape = shape
        strides = array.strides
        backstrides = array.backstrides
        if len(shape) == len(strides):
            # keepdims = True
            self.strides = strides[:dim] + [0] + strides[dim + 1:]
            self.backstrides = backstrides[:dim] + [0] + backstrides[dim + 1:]
        else:
            self.strides = strides[:dim] + [0] + strides[dim:]
            self.backstrides = backstrides[:dim] + [0] + backstrides[dim:]
        self.first_line = True
        self.indices = [0] * len(shape)
        self._done = False
        self.offset = array.start
        self.dim = dim
        self.array = array
        
    def setitem(self, elem):
        self.array.setitem(self.offset, elem)

    def getitem(self):
        return self.array.getitem(self.offset)

    @jit.unroll_safe
    def next(self):
        for i in range(len(self.shape) - 1, -1, -1):
            if self.indices[i] < self.shape[i] - 1:
                if i == self.dim:
                    self.first_line = False
                self.indices[i] += 1
                self.offset += self.strides[i]
                break
            else:
                if i == self.dim:
                    self.first_line = True
                self.indices[i] = 0
                self.offset -= self.backstrides[i]
        else:
            self._done = True

    def done(self):
        return self._done

def int_w(space, w_obj):
    try:
        return space.int_w(space.index(w_obj))
    except OperationError:
        return space.int_w(space.int(w_obj))

class BaseConcreteArray(base.BaseArrayImplementation):
    start = 0
    parent = None
    
    def get_shape(self):
        return self.shape

    def getitem(self, index):
        return self.dtype.getitem(self, index)

    def setitem(self, index, value):
        self.dtype.setitem(self, index, value)

    def setslice(self, space, arr):
        impl = arr.implementation
        if impl.is_scalar():
            self.fill(impl.get_scalar_value())
            return
        shape = shape_agreement(space, self.shape, arr)
        if impl.storage == self.storage:
            impl = impl.copy()
        loop.setslice(shape, self, impl)

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

    @jit.unroll_safe
    def _lookup_by_unwrapped_index(self, space, lst):
        item = self.start
        assert len(lst) == len(self.shape)
        for i, idx in enumerate(lst):
            if idx < 0:
                idx = self.shape[i] + idx
            if idx < 0 or idx >= self.shape[i]:
                raise operationerrfmt(space.w_IndexError,
                      "index (%d) out of range (0<=index<%d", i, self.shape[i],
                )
            item += idx * self.strides[i]
        return item

    def getitem_index(self, space, index):
        return self.getitem(self._lookup_by_unwrapped_index(space, index))

    def setitem_index(self, space, index, value):
        self.setitem(self._lookup_by_unwrapped_index(space, index), value)

    @jit.unroll_safe
    def _single_item_index(self, space, w_idx):
        """ Return an index of single item if possible, otherwise raises
        IndexError
        """
        if (space.isinstance_w(w_idx, space.w_str) or
            space.isinstance_w(w_idx, space.w_slice) or
            space.is_w(w_idx, space.w_None)):
            raise IndexError
        if isinstance(w_idx, W_NDimArray):
            raise ArrayArgumentException
        shape_len = len(self.shape)
        if shape_len == 0:
            raise OperationError(space.w_IndexError, space.wrap(
                "0-d arrays can't be indexed"))
        view_w = None
        if (space.isinstance_w(w_idx, space.w_list) or
            isinstance(w_idx, W_NDimArray)):
            raise ArrayArgumentException
        if space.isinstance_w(w_idx, space.w_tuple):
            view_w = space.fixedview(w_idx)
            if len(view_w) < shape_len:
                raise IndexError
            if len(view_w) > shape_len:
                # we can allow for one extra None
                count = len(view_w)
                for w_item in view_w:
                    if space.is_w(w_item, space.w_None):
                        count -= 1
                if count == shape_len:
                    raise IndexError # but it's still not a single item
                raise OperationError(space.w_IndexError,
                                     space.wrap("invalid index"))
            # check for arrays
            for w_item in view_w:
                if (isinstance(w_item, W_NDimArray) or
                    space.isinstance_w(w_item, space.w_list)):
                    raise ArrayArgumentException
            return self._lookup_by_index(space, view_w)
        if shape_len > 1:
            raise IndexError
        idx = int_w(space, w_idx)
        return self._lookup_by_index(space, [space.wrap(idx)])

    @jit.unroll_safe
    def _prepare_slice_args(self, space, w_idx):
        if space.isinstance_w(w_idx, space.w_str):
            idx = space.str_w(w_idx)
            dtype = self.dtype
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
            w_value = convert_to_array(space, w_value)
            chunks = self._prepare_slice_args(space, w_index)
            view = chunks.apply(self)
            view.implementation.setslice(space, w_value)

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

    def copy(self):
        strides, backstrides = support.calc_strides(self.shape, self.dtype,
                                                    self.order)
        impl = ConcreteArray(self.shape, self.dtype, self.order, strides,
                             backstrides)
        return loop.setslice(self.shape, impl, self)

    def create_axis_iter(self, shape, dim):
        return AxisIterator(self, shape, dim)

    def create_dot_iter(self, shape, skip):
        r = calculate_dot_strides(self.strides, self.backstrides,
                                  shape, skip)
        return MultiDimViewIterator(self, self.start, r[0], r[1], shape)

    def swapaxes(self, axis1, axis2):
        shape = self.shape[:]
        strides = self.strides[:]
        backstrides = self.backstrides[:]
        shape[axis1], shape[axis2] = shape[axis2], shape[axis1]   
        strides[axis1], strides[axis2] = strides[axis2], strides[axis1]
        backstrides[axis1], backstrides[axis2] = backstrides[axis2], backstrides[axis1] 
        return W_NDimArray.new_slice(self.start, strides, 
                                     backstrides, shape, self)

    def get_storage_as_int(self, space):
        return rffi.cast(lltype.Signed, self.storage)

    def get_storage(self):
        return self.storage

class ConcreteArray(BaseConcreteArray):
    def __init__(self, shape, dtype, order, strides, backstrides):
        self.shape = shape
        self.size = support.product(shape) * dtype.get_size()
        self.storage = dtype.itemtype.malloc(self.size)
        self.order = order
        self.dtype = dtype
        self.strides = strides
        self.backstrides = backstrides

    def create_iter(self, shape):
        if shape == self.shape:
            return ConcreteArrayIterator(self)
        r = calculate_broadcast_strides(self.strides, self.backstrides,
                                        self.shape, shape)
        return MultiDimViewIterator(self, 0, r[0], r[1], shape)

    def fill(self, box):
        self.dtype.fill(self.storage, box, 0, self.size)

    def __del__(self):
        free_raw_storage(self.storage, track_allocation=False)

    def set_shape(self, space, new_shape):
        strides, backstrides = support.calc_strides(new_shape, self.dtype,
                                                    self.order)
        return SliceArray(0, strides, backstrides, new_shape, self)

    def argsort(self, space, w_axis):
        return argsort_array(self, space, w_axis)

class SliceArray(BaseConcreteArray):
    def __init__(self, start, strides, backstrides, shape, parent, dtype=None):
        self.strides = strides
        self.backstrides = backstrides
        self.shape = shape
        if isinstance(parent, SliceArray):
            parent = parent.parent # one level only
        self.parent = parent
        self.storage = parent.storage
        self.order = parent.order
        if dtype is None:
            dtype = parent.dtype
        self.dtype = dtype
        self.size = support.product(shape) * self.dtype.itemtype.get_element_size()
        self.start = start

    def fill(self, box):
        loop.fill(self, box.convert_to(self.dtype))

    def create_iter(self, shape):
        if shape != self.shape:
            r = calculate_broadcast_strides(self.strides, self.backstrides,
                                            self.shape, shape)
            return MultiDimViewIterator(self.parent,
                                        self.start, r[0], r[1], shape)
        if len(self.shape) == 1:
            return OneDimViewIterator(self)
        return MultiDimViewIterator(self.parent, self.start, self.strides,
                                    self.backstrides, self.shape)

    def set_shape(self, space, new_shape):
        if len(self.shape) < 2 or self.size == 0:
            # TODO: this code could be refactored into calc_strides
            # but then calc_strides would have to accept a stepping factor
            strides = []
            backstrides = []
            dtype = self.dtype
            s = self.strides[0] // dtype.get_size()
            if self.order == 'C':
                new_shape.reverse()
            for sh in new_shape:
                strides.append(s * dtype.get_size())
                backstrides.append(s * (sh - 1) * dtype.get_size())
                s *= max(1, sh)
            if self.order == 'C':
                strides.reverse()
                backstrides.reverse()
                new_shape.reverse()
            return SliceArray(self.start, strides, backstrides, new_shape,
                              self)
        new_strides = calc_new_strides(new_shape, self.shape, self.strides,
                                       self.order)
        if new_strides is None:
            raise OperationError(space.w_AttributeError, space.wrap(
                          "incompatible shape for a non-contiguous array"))
        new_backstrides = [0] * len(new_shape)
        for nd in range(len(new_shape)):
            new_backstrides[nd] = (new_shape[nd] - 1) * new_strides[nd]
        return SliceArray(self.start, new_strides, new_backstrides, new_shape,
                          self)

from pypy.module.micronumpy.arrayimpl import base, scalar
from pypy.module.micronumpy import support, loop, iter
from pypy.module.micronumpy.base import convert_to_array, W_NDimArray,\
     ArrayArgumentException
from pypy.module.micronumpy.strides import calc_new_strides, shape_agreement,\
     calculate_broadcast_strides, calculate_dot_strides
from pypy.module.micronumpy.iter import Chunk, Chunks, NewAxisChunk, RecordChunk
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.buffer import RWBuffer
from rpython.rlib import jit
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib.rawstorage import free_raw_storage, raw_storage_getitem,\
     raw_storage_setitem, RAW_STORAGE
from rpython.rlib.debug import make_sure_not_resized


class BaseConcreteArray(base.BaseArrayImplementation):
    start = 0
    parent = None

    # JIT hints that length of all those arrays is a constant

    def get_shape(self):
        shape = self.shape
        jit.hint(len(shape), promote=True)
        return shape

    def get_strides(self):
        strides = self.strides
        jit.hint(len(strides), promote=True)
        return strides

    def get_backstrides(self):
        backstrides = self.backstrides
        jit.hint(len(backstrides), promote=True)
        return backstrides

    def getitem(self, index):
        return self.dtype.getitem(self, index)

    def setitem(self, index, value):
        self.dtype.setitem(self, index, value)

    def setslice(self, space, arr):
        impl = arr.implementation
        if impl.is_scalar():
            self.fill(impl.get_scalar_value())
            return
        shape = shape_agreement(space, self.get_shape(), arr)
        if impl.storage == self.storage:
            impl = impl.copy(space)
        loop.setslice(space, shape, self, impl)

    def get_size(self):
        return self.size // self.dtype.itemtype.get_element_size()

    def get_storage_size(self):
        return self.size

    def reshape(self, space, orig_array, new_shape):
        # Since we got to here, prod(new_shape) == self.size
        new_strides = None
        if self.size > 0:
            new_strides = calc_new_strides(new_shape, self.get_shape(),
                                           self.get_strides(), self.order)
        if new_strides:
            # We can create a view, strides somehow match up.
            ndims = len(new_shape)
            new_backstrides = [0] * ndims
            for nd in range(ndims):
                new_backstrides[nd] = (new_shape[nd] - 1) * new_strides[nd]
            assert isinstance(orig_array, W_NDimArray) or orig_array is None
            return SliceArray(self.start, new_strides, new_backstrides,
                              new_shape, self, orig_array)
        else:
            return None

    def get_view(self, orig_array, dtype, new_shape):
        strides, backstrides = support.calc_strides(new_shape, dtype,
                                                    self.order)
        return SliceArray(self.start, strides, backstrides, new_shape,
                          self, orig_array, dtype=dtype)

    def get_real(self, orig_array):
        strides = self.get_strides()
        backstrides = self.get_backstrides()
        if self.dtype.is_complex_type():
            dtype =  self.dtype.float_type
            return SliceArray(self.start, strides, backstrides,
                          self.get_shape(), self, orig_array, dtype=dtype)
        return SliceArray(self.start, strides, backstrides,
                          self.get_shape(), self, orig_array)

    def set_real(self, space, orig_array, w_value):
        tmp = self.get_real(orig_array)
        tmp.setslice(space, convert_to_array(space, w_value))

    def get_imag(self, orig_array):
        strides = self.get_strides()
        backstrides = self.get_backstrides()
        if self.dtype.is_complex_type():
            dtype =  self.dtype.float_type
            return SliceArray(self.start + dtype.get_size(), strides,
                    backstrides, self.get_shape(), self, orig_array, dtype=dtype)
        if self.dtype.is_flexible_type():
            # numpy returns self for self.imag
            return SliceArray(self.start, strides, backstrides,
                    self.get_shape(), self, orig_array)
        impl = NonWritableArray(self.get_shape(), self.dtype, self.order, strides,
                             backstrides)
        impl.fill(self.dtype.box(0))
        return impl

    def set_imag(self, space, orig_array, w_value):
        tmp = self.get_imag(orig_array)
        tmp.setslice(space, convert_to_array(space, w_value))

    # -------------------- applevel get/setitem -----------------------

    @jit.unroll_safe
    def _lookup_by_index(self, space, view_w):
        item = self.start
        strides = self.get_strides()
        for i, w_index in enumerate(view_w):
            if space.isinstance_w(w_index, space.w_slice):
                raise IndexError
            idx = support.int_w(space, w_index)
            if idx < 0:
                idx = self.get_shape()[i] + idx
            if idx < 0 or idx >= self.get_shape()[i]:
                raise operationerrfmt(space.w_IndexError,
                      "index (%d) out of range (0<=index<%d", i, self.get_shape()[i],
                )
            item += idx * strides[i]
        return item

    @jit.unroll_safe
    def _lookup_by_unwrapped_index(self, space, lst):
        item = self.start
        shape = self.get_shape()
        strides = self.get_strides()
        assert len(lst) == len(shape)
        for i, idx in enumerate(lst):
            if idx < 0:
                idx = shape[i] + idx
            if idx < 0 or idx >= shape[i]:
                raise operationerrfmt(space.w_IndexError,
                      "index (%d) out of range (0<=index<%d", i, shape[i],
                )
            item += idx * strides[i]
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
        if isinstance(w_idx, W_NDimArray) and not isinstance(w_idx.implementation, scalar.Scalar):
            raise ArrayArgumentException
        shape = self.get_shape()
        shape_len = len(shape)
        view_w = None
        if space.isinstance_w(w_idx, space.w_list):
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
        idx = support.int_w(space, w_idx)
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
            return Chunks([Chunk(*space.decode_index4(w_idx, self.get_shape()[0]))])
        elif space.is_w(w_idx, space.w_None):
            return Chunks([NewAxisChunk()])
        result = []
        i = 0
        for w_item in space.fixedview(w_idx):
            if space.is_w(w_item, space.w_None):
                result.append(NewAxisChunk())
            else:
                result.append(Chunk(*space.decode_index4(w_item,
                                                         self.get_shape()[i])))
                i += 1
        return Chunks(result)

    def descr_getitem(self, space, orig_arr, w_index):
        try:
            item = self._single_item_index(space, w_index)
            return self.getitem(item)
        except IndexError:
            # not a single result
            chunks = self._prepare_slice_args(space, w_index)
            return chunks.apply(space, orig_arr)

    def descr_setitem(self, space, orig_arr, w_index, w_value):
        try:
            item = self._single_item_index(space, w_index)
            self.setitem(item, self.dtype.coerce(space, w_value))
        except IndexError:
            w_value = convert_to_array(space, w_value)
            chunks = self._prepare_slice_args(space, w_index)
            view = chunks.apply(space, orig_arr)
            view.implementation.setslice(space, w_value)

    def transpose(self, orig_array):
        if len(self.get_shape()) < 2:
            return self
        strides = []
        backstrides = []
        shape = []
        for i in range(len(self.get_shape()) - 1, -1, -1):
            strides.append(self.get_strides()[i])
            backstrides.append(self.get_backstrides()[i])
            shape.append(self.get_shape()[i])
        return SliceArray(self.start, strides,
                          backstrides, shape, self, orig_array)

    def copy(self, space):
        strides, backstrides = support.calc_strides(self.get_shape(), self.dtype,
                                                    self.order)
        impl = ConcreteArray(self.get_shape(), self.dtype, self.order, strides,
                             backstrides)
        return loop.setslice(space, self.get_shape(), impl, self)

    def create_axis_iter(self, shape, dim, cum):
        return iter.AxisIterator(self, shape, dim, cum)

    def create_dot_iter(self, shape, skip):
        r = calculate_dot_strides(self.get_strides(), self.get_backstrides(),
                                  shape, skip)
        return iter.MultiDimViewIterator(self, self.dtype, self.start, r[0], r[1], shape)

    def swapaxes(self, space, orig_arr, axis1, axis2):
        shape = self.get_shape()[:]
        strides = self.get_strides()[:]
        backstrides = self.get_backstrides()[:]
        shape[axis1], shape[axis2] = shape[axis2], shape[axis1]
        strides[axis1], strides[axis2] = strides[axis2], strides[axis1]
        backstrides[axis1], backstrides[axis2] = backstrides[axis2], backstrides[axis1]
        return W_NDimArray.new_slice(space, self.start, strides,
                                     backstrides, shape, self, orig_arr)

    def nonzero(self, space, index_type):
        s = loop.count_all_true_concrete(self)
        box = index_type.itemtype.box
        nd = len(self.get_shape())
        w_res = W_NDimArray.from_shape(space, [s, nd], index_type)
        loop.nonzero(w_res, self, box)
        w_res = w_res.implementation.swapaxes(space, w_res, 0, 1)
        l_w = [w_res.descr_getitem(space, space.wrap(d)) for d in range(nd)]
        return space.newtuple(l_w)

    def get_storage_as_int(self, space):
        return rffi.cast(lltype.Signed, self.storage) + self.start

    def get_storage(self):
        return self.storage

    def get_buffer(self, space):
        return ArrayBuffer(self)

    def astype(self, space, dtype):
        strides, backstrides = support.calc_strides(self.get_shape(), dtype,
                                                    self.order)
        impl = ConcreteArray(self.get_shape(), dtype, self.order,
                             strides, backstrides)
        if self.dtype.is_str_or_unicode() and not dtype.is_str_or_unicode():
            raise OperationError(space.w_NotImplementedError, space.wrap(
                "astype(%s) not implemented yet" % self.dtype))
        else:
            loop.setslice(space, impl.get_shape(), impl, self)
        return impl


class ConcreteArrayNotOwning(BaseConcreteArray):
    def __init__(self, shape, dtype, order, strides, backstrides, storage):

        make_sure_not_resized(shape)
        make_sure_not_resized(strides)
        make_sure_not_resized(backstrides)
        self.shape = shape
        self.size = support.product(shape) * dtype.get_size()
        self.order = order
        self.dtype = dtype
        self.strides = strides
        self.backstrides = backstrides
        self.storage = storage

    def create_iter(self, shape=None, backward_broadcast=False, require_index=False):
        if shape is not None and \
                support.product(shape) > support.product(self.get_shape()):
            r = calculate_broadcast_strides(self.get_strides(),
                                            self.get_backstrides(),
                                            self.get_shape(), shape, backward_broadcast)
            return iter.MultiDimViewIterator(self, self.dtype, self.start, r[0], r[1], shape)

        if not require_index:
            return iter.ConcreteArrayIterator(self)
        else:
            if len(self.get_shape()) == 1:
                return iter.OneDimViewIterator(self, self.dtype, self.start,
                        self.get_strides(), self.get_shape())
            else:
                return iter.MultiDimViewIterator(self, self.dtype, self.start,
                        self.get_strides(), self.get_backstrides(), self.get_shape())

    def fill(self, box):
        self.dtype.fill(self.storage, box, 0, self.size)

    def set_shape(self, space, orig_array, new_shape):
        strides, backstrides = support.calc_strides(new_shape, self.dtype,
                                                    self.order)
        return SliceArray(0, strides, backstrides, new_shape, self,
                          orig_array)

    def argsort(self, space, w_axis):
        from pypy.module.micronumpy.arrayimpl.sort import argsort_array
        return argsort_array(self, space, w_axis)

    def sort(self, space, w_axis, w_order):
        from pypy.module.micronumpy.arrayimpl.sort import sort_array
        return sort_array(self, space, w_axis, w_order)

    def base(self):
        return None


class ConcreteArray(ConcreteArrayNotOwning):
    def __init__(self, shape, dtype, order, strides, backstrides, storage=lltype.nullptr(RAW_STORAGE)):
        null_storage = lltype.nullptr(RAW_STORAGE)
        ConcreteArrayNotOwning.__init__(self, shape, dtype, order, strides, backstrides,
                                        null_storage)
        if storage == lltype.nullptr(RAW_STORAGE):
            self.storage = dtype.itemtype.malloc(self.size)
        else:
            self.storage = storage

    def __del__(self):
        free_raw_storage(self.storage, track_allocation=False)


class NonWritableArray(ConcreteArray):
    def descr_setitem(self, space, orig_array, w_index, w_value):
        raise OperationError(space.w_RuntimeError, space.wrap(
            "array is not writable"))


class SliceArray(BaseConcreteArray):
    def __init__(self, start, strides, backstrides, shape, parent, orig_arr,
                 dtype=None):
        self.strides = strides
        self.backstrides = backstrides
        self.shape = shape
        if dtype is None:
            dtype = parent.dtype
        if isinstance(parent, SliceArray):
            parent = parent.parent # one level only
        self.parent = parent
        self.storage = parent.storage
        self.order = parent.order
        self.dtype = dtype
        self.size = support.product(shape) * self.dtype.itemtype.get_element_size()
        self.start = start
        self.orig_arr = orig_arr

    def base(self):
        return self.orig_arr

    def fill(self, box):
        loop.fill(self, box.convert_to(self.dtype))

    def create_iter(self, shape=None, backward_broadcast=False, require_index=False):
        if shape is not None and \
                support.product(shape) > support.product(self.get_shape()):
            r = calculate_broadcast_strides(self.get_strides(),
                                            self.get_backstrides(),
                                            self.get_shape(), shape,
                                            backward_broadcast)
            return iter.MultiDimViewIterator(self.parent, self.dtype,
                                             self.start, r[0], r[1], shape)
        if len(self.get_shape()) == 1:
            return iter.OneDimViewIterator(self.parent, self.dtype, self.start,
                    self.get_strides(), self.get_shape())
        return iter.MultiDimViewIterator(self.parent, self.dtype, self.start,
                                    self.get_strides(),
                                    self.get_backstrides(), self.get_shape())

    def set_shape(self, space, orig_array, new_shape):
        if len(self.get_shape()) < 2 or self.size == 0:
            # TODO: this code could be refactored into calc_strides
            # but then calc_strides would have to accept a stepping factor
            strides = []
            backstrides = []
            dtype = self.dtype
            s = self.get_strides()[0] // dtype.get_size()
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
                              self, orig_array)
        new_strides = calc_new_strides(new_shape, self.get_shape(),
                                       self.get_strides(),
                                       self.order)
        if new_strides is None:
            raise OperationError(space.w_AttributeError, space.wrap(
                          "incompatible shape for a non-contiguous array"))
        new_backstrides = [0] * len(new_shape)
        for nd in range(len(new_shape)):
            new_backstrides[nd] = (new_shape[nd] - 1) * new_strides[nd]
        return SliceArray(self.start, new_strides, new_backstrides, new_shape,
                          self, orig_array)


class ArrayBuffer(RWBuffer):
    def __init__(self, impl):
        self.impl = impl

    def getitem(self, item):
        return raw_storage_getitem(lltype.Char, self.impl.storage, item)

    def setitem(self, item, v):
        raw_storage_setitem(self.impl.storage, item,
                            rffi.cast(lltype.Char, v))

    def getlength(self):
        return self.impl.size

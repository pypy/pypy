
from pypy.interpreter.error import operationerrfmt, OperationError
from pypy.interpreter.typedef import TypeDef, GetSetProperty, make_weakref_descr
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.module.micronumpy.base import W_NDimArray, convert_to_array,\
     ArrayArgumentException, issequence_w, wrap_impl
from pypy.module.micronumpy import interp_dtype, interp_ufuncs, interp_boxes,\
     interp_arrayops, iter
from pypy.module.micronumpy.strides import find_shape_and_elems,\
     get_shape_from_iterable, to_coords, shape_agreement, \
     shape_agreement_multiple
from pypy.module.micronumpy.interp_flatiter import W_FlatIterator
from pypy.module.micronumpy.interp_support import unwrap_axis_arg
from pypy.module.micronumpy.appbridge import get_appbridge_cache
from pypy.module.micronumpy import loop
from pypy.module.micronumpy.dot import match_dot_shapes
from pypy.module.micronumpy.interp_arrayops import repeat, choose
from pypy.module.micronumpy.arrayimpl import scalar
from rpython.tool.sourcetools import func_with_new_name
from rpython.rlib import jit
from rpython.rlib.rstring import StringBuilder
from pypy.module.micronumpy.arrayimpl.base import BaseArrayImplementation

def _find_shape(space, w_size, dtype):
    if space.is_none(w_size):
        return []
    if space.isinstance_w(w_size, space.w_int):
        return [space.int_w(w_size)]
    shape = []
    for w_item in space.fixedview(w_size):
        shape.append(space.int_w(w_item))
    shape += dtype.shape
    return shape[:]

class __extend__(W_NDimArray):
    @jit.unroll_safe
    def descr_get_shape(self, space):
        shape = self.get_shape()
        return space.newtuple([space.wrap(i) for i in shape])

    def get_shape(self):
        return self.implementation.get_shape()

    def descr_set_shape(self, space, w_new_shape):
        self.implementation = self.implementation.set_shape(space, self,
            get_shape_from_iterable(space, self.get_size(), w_new_shape))

    def descr_get_strides(self, space):
        strides = self.implementation.get_strides()
        return space.newtuple([space.wrap(i) for i in strides])

    def get_dtype(self):
        return self.implementation.dtype

    def get_order(self):
        return self.implementation.order

    def descr_get_dtype(self, space):
        return self.implementation.dtype

    def descr_get_ndim(self, space):
        return space.wrap(len(self.get_shape()))

    def descr_get_itemsize(self, space):
        return space.wrap(self.get_dtype().itemtype.get_element_size())

    def descr_get_nbytes(self, space):
        return space.wrap(self.get_size() * self.get_dtype().itemtype.get_element_size())

    def descr_fill(self, space, w_value):
        self.fill(self.get_dtype().coerce(space, w_value))

    def descr_tostring(self, space):
        return space.wrap(loop.tostring(space, self))

    def getitem_filter(self, space, arr):
        if len(arr.get_shape()) > 1 and arr.get_shape() != self.get_shape():
            raise OperationError(space.w_ValueError,
                                 space.wrap("boolean index array should have 1 dimension"))
        if arr.get_size() > self.get_size():
            raise OperationError(space.w_ValueError,
                                 space.wrap("index out of range for array"))
        size = loop.count_all_true(arr)
        if len(arr.get_shape()) == 1:
            res_shape = [size] + self.get_shape()[1:]
        else:
            res_shape = [size]
        w_res = W_NDimArray.from_shape(space, res_shape, self.get_dtype(), w_instance=self)
        return loop.getitem_filter(w_res, self, arr)

    def setitem_filter(self, space, idx, val):
        if len(idx.get_shape()) > 1 and idx.get_shape() != self.get_shape():
            raise OperationError(space.w_ValueError,
                                 space.wrap("boolean index array should have 1 dimension"))
        if idx.get_size() > self.get_size():
            raise OperationError(space.w_ValueError,
                                 space.wrap("index out of range for array"))
        size = loop.count_all_true(idx)
        if size > val.get_size() and val.get_size() > 1:
            raise OperationError(space.w_ValueError, space.wrap("NumPy boolean array indexing assignment "
                                                                "cannot assign %d input values to "
                                                                "the %d output values where the mask is true" % (val.get_size(), size)))
        if val.get_shape() == [0]:
            val.implementation.dtype = self.implementation.dtype
        loop.setitem_filter(self, idx, val, size)

    def _prepare_array_index(self, space, w_index):
        if isinstance(w_index, W_NDimArray):
            return [], w_index.get_shape(), w_index.get_shape(), [w_index]
        w_lst = space.listview(w_index)
        for w_item in w_lst:
            if not space.isinstance_w(w_item, space.w_int):
                break
        else:
            arr = convert_to_array(space, w_index)
            return [], arr.get_shape(), arr.get_shape(), [arr]
        shape = None
        indexes_w = [None] * len(w_lst)
        res_shape = []
        arr_index_in_shape = False
        prefix = []
        for i, w_item in enumerate(w_lst):
            if (isinstance(w_item, W_NDimArray) or
                space.isinstance_w(w_item, space.w_list)):
                w_item = convert_to_array(space, w_item)
                if shape is None:
                    shape = w_item.get_shape()
                else:
                    shape = shape_agreement(space, shape, w_item)
                indexes_w[i] = w_item
                if not arr_index_in_shape:
                    res_shape.append(-1)
                    arr_index_in_shape = True
            else:
                if space.isinstance_w(w_item, space.w_slice):
                    _, _, _, lgt = space.decode_index4(w_item, self.get_shape()[i])
                    if not arr_index_in_shape:
                        prefix.append(w_item)
                    res_shape.append(lgt)
                indexes_w[i] = w_item
        real_shape = []
        for i in res_shape:
            if i == -1:
                real_shape += shape
            else:
                real_shape.append(i)
        return prefix, real_shape[:], shape, indexes_w

    def getitem_array_int(self, space, w_index):
        prefix, res_shape, iter_shape, indexes = \
                self._prepare_array_index(space, w_index)
        if iter_shape is None:
            # w_index is a list of slices, return a view
            chunks = self.implementation._prepare_slice_args(space, w_index)
            return chunks.apply(space, self)
        shape = res_shape + self.get_shape()[len(indexes):]
        w_res = W_NDimArray.from_shape(space, shape, self.get_dtype(),
                                     self.get_order(), w_instance=self)
        if not w_res.get_size():
            return w_res
        return loop.getitem_array_int(space, self, w_res, iter_shape, indexes,
                                      prefix)

    def setitem_array_int(self, space, w_index, w_value):
        val_arr = convert_to_array(space, w_value)
        prefix, _, iter_shape, indexes = \
                self._prepare_array_index(space, w_index)
        if iter_shape is None:
            # w_index is a list of slices
            w_value = convert_to_array(space, w_value)
            chunks = self.implementation._prepare_slice_args(space, w_index)
            view = chunks.apply(space, self)
            view.implementation.setslice(space, w_value)
            return
        loop.setitem_array_int(space, self, iter_shape, indexes, val_arr,
                               prefix)

    def descr_getitem(self, space, w_idx):
        if (isinstance(w_idx, W_NDimArray) and
            w_idx.get_dtype().is_bool_type()):
            return self.getitem_filter(space, w_idx)
        try:
            return self.implementation.descr_getitem(space, self, w_idx)
        except ArrayArgumentException:
            return self.getitem_array_int(space, w_idx)
        except OperationError:
            raise OperationError(space.w_IndexError, space.wrap("wrong index"))

    def getitem(self, space, index_list):
        return self.implementation.getitem_index(space, index_list)

    def setitem(self, space, index_list, w_value):
        self.implementation.setitem_index(space, index_list, w_value)

    def descr_setitem(self, space, w_idx, w_value):
        if (isinstance(w_idx, W_NDimArray) and
                w_idx.get_dtype().is_bool_type()):
            self.setitem_filter(space, w_idx, convert_to_array(space, w_value))
            return
        try:
            self.implementation.descr_setitem(space, self, w_idx, w_value)
        except ArrayArgumentException:
            self.setitem_array_int(space, w_idx, w_value)

    def descr_len(self, space):
        shape = self.get_shape()
        if len(shape):
            return space.wrap(shape[0])
        raise OperationError(space.w_TypeError, space.wrap(
            "len() of unsized object"))

    def descr_repr(self, space):
        cache = get_appbridge_cache(space)
        if cache.w_array_repr is None:
            return space.wrap(self.dump_data())
        return space.call_function(cache.w_array_repr, self)

    def descr_str(self, space):
        cache = get_appbridge_cache(space)
        if cache.w_array_str is None:
            return space.wrap(self.dump_data())
        return space.call_function(cache.w_array_str, self)

    def dump_data(self):
        i = self.create_iter()
        first = True
        dtype = self.get_dtype()
        s = StringBuilder()
        s.append('array([')
        while not i.done():
            if first:
                first = False
            else:
                s.append(', ')
            s.append(dtype.itemtype.str_format(i.getitem()))
            i.next()
        s.append('])')
        return s.build()

    def create_iter(self, shape=None, backward_broadcast=False, require_index=False):
        assert isinstance(self.implementation, BaseArrayImplementation)
        return self.implementation.create_iter(shape=shape,
                                   backward_broadcast=backward_broadcast,
                                   require_index=require_index)

    def create_axis_iter(self, shape, dim, cum):
        return self.implementation.create_axis_iter(shape, dim, cum)

    def create_dot_iter(self, shape, skip):
        return self.implementation.create_dot_iter(shape, skip)

    def is_scalar(self):
        return self.implementation.is_scalar()

    def set_scalar_value(self, w_val):
        self.implementation.set_scalar_value(w_val)

    def fill(self, box):
        self.implementation.fill(box)

    def descr_get_size(self, space):
        return space.wrap(self.get_size())

    def get_size(self):
        return self.implementation.get_size()

    def get_scalar_value(self):
        return self.implementation.get_scalar_value()

    def descr_copy(self, space):
        copy = self.implementation.copy(space)
        w_subtype = space.type(self)
        return wrap_impl(space, w_subtype, self, copy)

    def descr_get_real(self, space):
        return wrap_impl(space, space.type(self), self,
                         self.implementation.get_real(self))

    def descr_get_imag(self, space):
        ret = self.implementation.get_imag(self)
        return wrap_impl(space, space.type(self), self, ret)

    def descr_set_real(self, space, w_value):
        # copy (broadcast) values into self
        self.implementation.set_real(space, self, w_value)

    def descr_set_imag(self, space, w_value):
        # if possible, copy (broadcast) values into self
        if not self.get_dtype().is_complex_type():
            raise OperationError(space.w_TypeError,
                    space.wrap('array does not have imaginary part to set'))
        self.implementation.set_imag(space, self, w_value)

    def descr_reshape(self, space, args_w):
        """reshape(...)
        a.reshape(shape)

        Returns an array containing the same data with a new shape.

        Refer to `numpypy.reshape` for full documentation.

        See Also
        --------
        numpypy.reshape : equivalent function
        """
        if len(args_w) == 1:
            w_shape = args_w[0]
        else:
            w_shape = space.newtuple(args_w)
        new_shape = get_shape_from_iterable(space, self.get_size(), w_shape)
        new_impl = self.implementation.reshape(space, self, new_shape)
        if new_impl is not None:
            return wrap_impl(space, space.type(self), self, new_impl)
        # Create copy with contiguous data
        arr = self.descr_copy(space)
        if arr.get_size() > 0:
            arr.implementation = arr.implementation.reshape(space, self,
                                                            new_shape)
            assert arr.implementation
        else:
            arr.implementation.shape = new_shape
        return arr

    def descr_get_transpose(self, space):
        return W_NDimArray(self.implementation.transpose(self))

    @unwrap_spec(axis1=int, axis2=int)
    def descr_swapaxes(self, space, axis1, axis2):
        """a.swapaxes(axis1, axis2)

        Return a view of the array with `axis1` and `axis2` interchanged.

        Refer to `numpy.swapaxes` for full documentation.

        See Also
        --------
        numpy.swapaxes : equivalent function
        """
        if self.is_scalar():
            return self
        return self.implementation.swapaxes(space, self, axis1, axis2)

    def descr_nonzero(self, space):
        index_type = interp_dtype.get_dtype_cache(space).w_int64dtype
        return self.implementation.nonzero(space, index_type)

    def descr_tolist(self, space):
        if len(self.get_shape()) == 0:
            return self.get_scalar_value().item(space)
        l_w = []
        for i in range(self.get_shape()[0]):
            l_w.append(space.call_method(self.descr_getitem(space,
                                         space.wrap(i)), "tolist"))
        return space.newlist(l_w)

    def descr_ravel(self, space, w_order=None):
        if space.is_none(w_order):
            order = 'C'
        else:
            order = space.str_w(w_order)
        if order != 'C':
            raise OperationError(space.w_NotImplementedError, space.wrap(
                "order not implemented"))
        return self.descr_reshape(space, [space.wrap(-1)])

    def descr_take(self, space, w_obj, w_axis=None, w_out=None):
        # if w_axis is None and w_out is Nont this is an equivalent to
        # fancy indexing
        raise OperationError(space.w_NotImplementedError,
                             space.wrap("unsupported for now"))
        if not space.is_none(w_axis):
            raise OperationError(space.w_NotImplementedError,
                                 space.wrap("axis unsupported for take"))
        if not space.is_none(w_out):
            raise OperationError(space.w_NotImplementedError,
                                 space.wrap("out unsupported for take"))
        return self.getitem_int(space, convert_to_array(space, w_obj))

    def descr_compress(self, space, w_obj, w_axis=None):
        if not space.is_none(w_axis):
            raise OperationError(space.w_NotImplementedError,
                                 space.wrap("axis unsupported for compress"))
            arr = self
        else:
            arr = self.descr_reshape(space, [space.wrap(-1)])
        index = convert_to_array(space, w_obj)
        return arr.getitem_filter(space, index)

    def descr_flatten(self, space, w_order=None):
        if self.is_scalar():
            # scalars have no storage
            return self.descr_reshape(space, [space.wrap(1)])
        w_res = self.descr_ravel(space, w_order)
        if w_res.implementation.storage == self.implementation.storage:
            return w_res.descr_copy(space)
        return w_res

    @unwrap_spec(repeats=int)
    def descr_repeat(self, space, repeats, w_axis=None):
        return repeat(space, self, repeats, w_axis)

    def descr_set_flatiter(self, space, w_obj):
        arr = convert_to_array(space, w_obj)
        loop.flatiter_setitem(space, self, arr, 0, 1, self.get_size())

    def descr_get_flatiter(self, space):
        return space.wrap(W_FlatIterator(self))

    def to_coords(self, space, w_index):
        coords, _, _ = to_coords(space, self.get_shape(),
                                 self.get_size(), self.get_order(),
                                 w_index)
        return coords

    def descr_item(self, space, w_arg=None):
        if space.is_none(w_arg):
            if self.is_scalar():
                return self.get_scalar_value().item(space)
            if self.get_size() == 1:
                w_obj = self.getitem(space,
                                     [0] * len(self.get_shape()))
                assert isinstance(w_obj, interp_boxes.W_GenericBox)
                return w_obj.item(space)
            raise OperationError(space.w_ValueError,
                                 space.wrap("can only convert an array of size 1 to a Python scalar"))
        if space.isinstance_w(w_arg, space.w_int):
            if self.is_scalar():
                raise OperationError(space.w_IndexError,
                                     space.wrap("index out of bounds"))
            i = self.to_coords(space, w_arg)
            item = self.getitem(space, i)
            assert isinstance(item, interp_boxes.W_GenericBox)
            return item.item(space)
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "non-int arg not supported"))

    def descr___array__(self, space, w_dtype=None):
        if not space.is_none(w_dtype):
            raise OperationError(space.w_NotImplementedError, space.wrap(
                "__array__(dtype) not implemented"))
        # stub implementation of __array__()
        return self

    def descr_array_iface(self, space):
        addr = self.implementation.get_storage_as_int(space)
        # will explode if it can't
        w_d = space.newdict()
        space.setitem_str(w_d, 'data',
                          space.newtuple([space.wrap(addr), space.w_False]))
        space.setitem_str(w_d, 'shape', self.descr_get_shape(space))
        space.setitem_str(w_d, 'typestr', self.get_dtype().descr_get_str(space))
        if self.implementation.order == 'C':
            # Array is contiguous, no strides in the interface.
            strides = space.w_None
        else:
            strides = self.descr_get_strides(space)
        space.setitem_str(w_d, 'strides', strides)
        return w_d

    w_pypy_data = None
    def fget___pypy_data__(self, space):
        return self.w_pypy_data

    def fset___pypy_data__(self, space, w_data):
        self.w_pypy_data = w_data

    def fdel___pypy_data__(self, space):
        self.w_pypy_data = None

    def descr_argsort(self, space, w_axis=None, w_kind=None, w_order=None):
        # happily ignore the kind
        # create a contiguous copy of the array
        # we must do that, because we need a working set. otherwise
        # we would modify the array in-place. Use this to our advantage
        # by converting nonnative byte order.
        if self.is_scalar():
            return space.wrap(0)
        s = self.get_dtype().name
        if not self.get_dtype().native:
            s = s[1:]
        dtype = interp_dtype.get_dtype_cache(space).dtypes_by_name[s]
        contig = self.implementation.astype(space, dtype)
        return contig.argsort(space, w_axis)

    def descr_astype(self, space, w_dtype):
        dtype = space.interp_w(interp_dtype.W_Dtype,
          space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype))
        impl = self.implementation
        if isinstance(impl, scalar.Scalar):
            return W_NDimArray.new_scalar(space, dtype, impl.value)
        else:
            new_impl = impl.astype(space, dtype)
            return wrap_impl(space, space.type(self), self, new_impl)

    def descr_get_base(self, space):
        impl = self.implementation
        ret = impl.base()
        if ret is None:
            return space.w_None
        return ret

    @unwrap_spec(inplace=bool)
    def descr_byteswap(self, space, inplace=False):
        if inplace:
            loop.byteswap(self.implementation, self.implementation)
            return self
        else:
            w_res = W_NDimArray.from_shape(space, self.get_shape(), self.get_dtype(), w_instance=self)
            loop.byteswap(self.implementation, w_res.implementation)
            return w_res

    @unwrap_spec(mode=str)
    def descr_choose(self, space, w_choices, w_out=None, mode='raise'):
        return choose(space, self, w_choices, w_out, mode)

    def descr_clip(self, space, w_min, w_max, w_out=None):
        if space.is_none(w_out):
            w_out = None
        elif not isinstance(w_out, W_NDimArray):
            raise OperationError(space.w_TypeError, space.wrap(
                "return arrays must be of ArrayType"))
        min = convert_to_array(space, w_min)
        max = convert_to_array(space, w_max)
        shape = shape_agreement_multiple(space, [self, min, max, w_out])
        out = interp_dtype.dtype_agreement(space, [self, min, max], shape,
                                           w_out)
        loop.clip(space, self, shape, min, max, out)
        return out

    def descr_get_ctypes(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "ctypes not implemented yet"))

    def descr_get_data(self, space):
        return self.implementation.get_buffer(space)

    @unwrap_spec(offset=int, axis1=int, axis2=int)
    def descr_diagonal(self, space, offset=0, axis1=0, axis2=1):
        if len(self.get_shape()) < 2:
            raise OperationError(space.w_ValueError, space.wrap(
                "need at least 2 dimensions for diagonal"))
        if (axis1 < 0 or axis2 < 0 or axis1 >= len(self.get_shape()) or
            axis2 >= len(self.get_shape())):
            raise operationerrfmt(space.w_ValueError,
                 "axis1(=%d) and axis2(=%d) must be withing range (ndim=%d)",
                                  axis1, axis2, len(self.get_shape()))
        if axis1 == axis2:
            raise OperationError(space.w_ValueError, space.wrap(
                "axis1 and axis2 cannot be the same"))
        return interp_arrayops.diagonal(space, self.implementation, offset,
                                        axis1, axis2)

    @unwrap_spec(offset=int, axis1=int, axis2=int)
    def descr_trace(self, space, offset=0, axis1=0, axis2=1,
                    w_dtype=None, w_out=None):
        diag = self.descr_diagonal(space, offset, axis1, axis2)
        return diag.descr_sum(space, w_axis=space.wrap(-1), w_dtype=w_dtype, w_out=w_out)

    def descr_dump(self, space, w_file):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "dump not implemented yet"))

    def descr_dumps(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "dumps not implemented yet"))

    def descr_get_flags(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "getting flags not implemented yet"))

    def descr_set_flags(self, space, w_args):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "setting flags not implemented yet"))

    @unwrap_spec(offset=int)
    def descr_getfield(self, space, w_dtype, offset):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "getfield not implemented yet"))

    def descr_itemset(self, space, w_arg):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "itemset not implemented yet"))

    @unwrap_spec(neworder=str)
    def descr_newbyteorder(self, space, neworder):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "newbyteorder not implemented yet"))

    def descr_ptp(self, space, w_axis=None, w_out=None):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "ptp (peak to peak) not implemented yet"))

    @unwrap_spec(mode=str)
    def descr_put(self, space, w_indices, w_values, mode='raise'):
        from pypy.module.micronumpy.interp_arrayops import put
        put(space, self, w_indices, w_values, mode)

    def descr_resize(self, space, w_new_shape, w_refcheck=True):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "resize not implemented yet"))

    @unwrap_spec(decimals=int)
    def descr_round(self, space, decimals=0, w_out=None):
        if space.is_none(w_out):
            if self.get_dtype().is_bool_type():
                #numpy promotes bool.round() to float16. Go figure.
                w_out = W_NDimArray.from_shape(space, self.get_shape(),
                       interp_dtype.get_dtype_cache(space).w_float16dtype)
            else:
                w_out = None
        elif not isinstance(w_out, W_NDimArray):
            raise OperationError(space.w_TypeError, space.wrap(
                "return arrays must be of ArrayType"))
        out = interp_dtype.dtype_agreement(space, [self], self.get_shape(),
                                           w_out)
        if out.get_dtype().is_bool_type() and self.get_dtype().is_bool_type():
            calc_dtype = interp_dtype.get_dtype_cache(space).w_longdtype
        else:
            calc_dtype = out.get_dtype()

        if decimals == 0:
            out = out.descr_view(space,space.type(self))
        loop.round(space, self, calc_dtype, self.get_shape(), decimals, out)
        return out

    def descr_searchsorted(self, space, w_v, w_side='left'):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "searchsorted not implemented yet"))

    def descr_setasflat(self, space, w_v):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "setasflat not implemented yet"))

    def descr_setfield(self, space, w_val, w_dtype, w_offset=0):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "setfield not implemented yet"))

    def descr_setflags(self, space, w_write=None, w_align=None, w_uic=None):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "setflags not implemented yet"))

    @unwrap_spec(kind=str)
    def descr_sort(self, space, w_axis=None, kind='quicksort', w_order=None):
        # happily ignore the kind
        # modify the array in-place
        if self.is_scalar():
            return
        return self.implementation.sort(space, w_axis, w_order)

    def descr_squeeze(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "squeeze not implemented yet"))

    def descr_strides(self, space):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "strides not implemented yet"))

    def descr_tofile(self, space, w_fid, w_sep="", w_format="%s"):
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "tofile not implemented yet"))

    def descr_view(self, space, w_dtype=None, w_type=None) :
        if not w_type and w_dtype:
            try:
                if space.is_true(space.issubtype(w_dtype, space.gettypefor(W_NDimArray))):
                    w_type = w_dtype
                    w_dtype = None
            except (OperationError, TypeError):
                pass
        if w_dtype:
            dtype = space.interp_w(interp_dtype.W_Dtype,
                space.call_function(space.gettypefor(interp_dtype.W_Dtype),
                                                                   w_dtype))
        else:
            dtype = self.get_dtype()
        old_itemsize = self.get_dtype().get_size()
        new_itemsize = dtype.get_size()
        impl = self.implementation
        new_shape = self.get_shape()[:]
        dims = len(new_shape)
        if dims == 0:
            # Cannot resize scalars
            if old_itemsize != new_itemsize:
                raise OperationError(space.w_ValueError, space.wrap(
                    "new type not compatible with array shape"))
        else:
            if dims == 1 or impl.get_strides()[0] < impl.get_strides()[-1]:
                # Column-major, resize first dimension
                if new_shape[0] * old_itemsize % new_itemsize != 0:
                    raise OperationError(space.w_ValueError, space.wrap(
                        "new type not compatible with array."))
                new_shape[0] = new_shape[0] * old_itemsize / new_itemsize
            else:
                # Row-major, resize last dimension
                if new_shape[-1] * old_itemsize % new_itemsize != 0:
                    raise OperationError(space.w_ValueError, space.wrap(
                        "new type not compatible with array."))
                new_shape[-1] = new_shape[-1] * old_itemsize / new_itemsize
        v = impl.get_view(self, dtype, new_shape)
        w_ret = wrap_impl(space, w_type, self, v)
        return w_ret

    # --------------------- operations ----------------------------

    def _unaryop_impl(ufunc_name):
        def impl(self, space, w_out=None):
            return getattr(interp_ufuncs.get(space), ufunc_name).call(space,
                                                                [self, w_out])
        return func_with_new_name(impl, "unaryop_%s_impl" % ufunc_name)

    descr_pos = _unaryop_impl("positive")
    descr_neg = _unaryop_impl("negative")
    descr_abs = _unaryop_impl("absolute")
    descr_invert = _unaryop_impl("invert")

    descr_conj = _unaryop_impl('conjugate')

    def descr___nonzero__(self, space):
        if self.get_size() > 1:
            raise OperationError(space.w_ValueError, space.wrap(
                "The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()"))
        iter = self.create_iter()
        return space.wrap(space.is_true(iter.getitem()))

    def _binop_impl(ufunc_name):
        def impl(self, space, w_other, w_out=None):
            return getattr(interp_ufuncs.get(space), ufunc_name).call(space,
                                                        [self, w_other, w_out])
        return func_with_new_name(impl, "binop_%s_impl" % ufunc_name)

    descr_add = _binop_impl("add")
    descr_sub = _binop_impl("subtract")
    descr_mul = _binop_impl("multiply")
    descr_div = _binop_impl("divide")
    descr_truediv = _binop_impl("true_divide")
    descr_floordiv = _binop_impl("floor_divide")
    descr_mod = _binop_impl("mod")
    descr_pow = _binop_impl("power")
    descr_lshift = _binop_impl("left_shift")
    descr_rshift = _binop_impl("right_shift")
    descr_and = _binop_impl("bitwise_and")
    descr_or = _binop_impl("bitwise_or")
    descr_xor = _binop_impl("bitwise_xor")

    def descr_divmod(self, space, w_other):
        w_quotient = self.descr_div(space, w_other)
        w_remainder = self.descr_mod(space, w_other)
        return space.newtuple([w_quotient, w_remainder])

    def _binop_comp_impl(ufunc):
        def impl(self, space, w_other, w_out=None):
            try:
                return ufunc(self, space, w_other, w_out)
            except OperationError, e:
                if e.match(space, space.w_ValueError):
                    return space.w_False
                raise e

        return func_with_new_name(impl, ufunc.func_name)

    descr_eq = _binop_comp_impl(_binop_impl("equal"))
    descr_ne = _binop_comp_impl(_binop_impl("not_equal"))
    descr_lt = _binop_comp_impl(_binop_impl("less"))
    descr_le = _binop_comp_impl(_binop_impl("less_equal"))
    descr_gt = _binop_comp_impl(_binop_impl("greater"))
    descr_ge = _binop_comp_impl(_binop_impl("greater_equal"))

    def _binop_inplace_impl(ufunc_name):
        def impl(self, space, w_other):
            w_out = self
            ufunc = getattr(interp_ufuncs.get(space), ufunc_name)
            return ufunc.call(space, [self, w_other, w_out])
        return func_with_new_name(impl, "binop_inplace_%s_impl" % ufunc_name)

    descr_iadd = _binop_inplace_impl("add")
    descr_isub = _binop_inplace_impl("subtract")
    descr_imul = _binop_inplace_impl("multiply")
    descr_idiv = _binop_inplace_impl("divide")
    descr_itruediv = _binop_inplace_impl("true_divide")
    descr_ifloordiv = _binop_inplace_impl("floor_divide")
    descr_imod = _binop_inplace_impl("mod")
    descr_ipow = _binop_inplace_impl("power")
    descr_ilshift = _binop_inplace_impl("left_shift")
    descr_irshift = _binop_inplace_impl("right_shift")
    descr_iand = _binop_inplace_impl("bitwise_and")
    descr_ior = _binop_inplace_impl("bitwise_or")
    descr_ixor = _binop_inplace_impl("bitwise_xor")

    def _binop_right_impl(ufunc_name):
        def impl(self, space, w_other, w_out=None):
            w_other = convert_to_array(space, w_other)
            return getattr(interp_ufuncs.get(space), ufunc_name).call(space, [w_other, self, w_out])
        return func_with_new_name(impl, "binop_right_%s_impl" % ufunc_name)

    descr_radd = _binop_right_impl("add")
    descr_rsub = _binop_right_impl("subtract")
    descr_rmul = _binop_right_impl("multiply")
    descr_rdiv = _binop_right_impl("divide")
    descr_rtruediv = _binop_right_impl("true_divide")
    descr_rfloordiv = _binop_right_impl("floor_divide")
    descr_rmod = _binop_right_impl("mod")
    descr_rpow = _binop_right_impl("power")
    descr_rlshift = _binop_right_impl("left_shift")
    descr_rrshift = _binop_right_impl("right_shift")
    descr_rand = _binop_right_impl("bitwise_and")
    descr_ror = _binop_right_impl("bitwise_or")
    descr_rxor = _binop_right_impl("bitwise_xor")

    def descr_rdivmod(self, space, w_other):
        w_quotient = self.descr_rdiv(space, w_other)
        w_remainder = self.descr_rmod(space, w_other)
        return space.newtuple([w_quotient, w_remainder])

    def descr_dot(self, space, w_other):
        other = convert_to_array(space, w_other)
        if other.is_scalar():
            #Note: w_out is not modified, this is numpy compliant.
            return self.descr_mul(space, other)
        elif len(self.get_shape()) < 2 and len(other.get_shape()) < 2:
            w_res = self.descr_mul(space, other)
            assert isinstance(w_res, W_NDimArray)
            return w_res.descr_sum(space, space.wrap(-1))
        dtype = interp_ufuncs.find_binop_result_dtype(space,
                                     self.get_dtype(), other.get_dtype())
        if self.get_size() < 1 and other.get_size() < 1:
            # numpy compatability
            return W_NDimArray.new_scalar(space, dtype, space.wrap(0))
        # Do the dims match?
        out_shape, other_critical_dim = match_dot_shapes(space, self, other)
        w_res = W_NDimArray.from_shape(space, out_shape, dtype, w_instance=self)
        # This is the place to add fpypy and blas
        return loop.multidim_dot(space, self, other,  w_res, dtype,
                                 other_critical_dim)

    @unwrap_spec(w_axis = WrappedDefault(None))
    def descr_var(self, space, w_axis):
        return get_appbridge_cache(space).call_method(space, '_var', self,
                                                      w_axis)

    @unwrap_spec(w_axis = WrappedDefault(None))
    def descr_std(self, space, w_axis):
        return get_appbridge_cache(space).call_method(space, '_std', self,
                                                      w_axis)

    # ----------------------- reduce -------------------------------

    def _reduce_ufunc_impl(ufunc_name, promote_to_largest=False,
                           cumultative=False):
        def impl(self, space, w_axis=None, w_dtype=None, w_out=None):
            if space.is_none(w_out):
                out = None
            elif not isinstance(w_out, W_NDimArray):
                raise OperationError(space.w_TypeError, space.wrap(
                        'output must be an array'))
            else:
                out = w_out
            return getattr(interp_ufuncs.get(space), ufunc_name).reduce(
                space, self, promote_to_largest, w_axis,
                False, out, w_dtype, cumultative=cumultative)
        return func_with_new_name(impl, "reduce_%s_impl_%d_%d" % (ufunc_name,
                    promote_to_largest, cumultative))

    descr_sum = _reduce_ufunc_impl("add")
    descr_sum_promote = _reduce_ufunc_impl("add", True)
    descr_prod = _reduce_ufunc_impl("multiply", True)
    descr_max = _reduce_ufunc_impl("maximum")
    descr_min = _reduce_ufunc_impl("minimum")
    descr_all = _reduce_ufunc_impl('logical_and')
    descr_any = _reduce_ufunc_impl('logical_or')

    descr_cumsum = _reduce_ufunc_impl('add', cumultative=True)
    descr_cumprod = _reduce_ufunc_impl('multiply', cumultative=True)

    def descr_mean(self, space, w_axis=None, w_out=None):
        if space.is_none(w_axis):
            w_denom = space.wrap(self.get_size())
        else:
            axis = unwrap_axis_arg(space, len(self.get_shape()), w_axis)
            w_denom = space.wrap(self.get_shape()[axis])
        return space.div(self.descr_sum_promote(space, w_axis, w_out), w_denom)

    def _reduce_argmax_argmin_impl(op_name):
        def impl(self, space):
            if self.get_size() == 0:
                raise OperationError(space.w_ValueError,
                    space.wrap("Can't call %s on zero-size arrays" % op_name))
            return space.wrap(getattr(loop, 'arg' + op_name)(self))
        return func_with_new_name(impl, "reduce_arg%s_impl" % op_name)

    descr_argmax = _reduce_argmax_argmin_impl("max")
    descr_argmin = _reduce_argmax_argmin_impl("min")

    def descr_int(self, space):
        shape = self.get_shape()
        if len(shape) == 0:
            assert isinstance(self.implementation, scalar.Scalar)
            return space.int(space.wrap(self.implementation.get_scalar_value()))
        if shape == [1]:
            return space.int(self.descr_getitem(space, space.wrap(0)))
        raise OperationError(space.w_TypeError, space.wrap("only length-1 arrays can be converted to Python scalars"))

    def descr_long(self, space):
        shape = self.get_shape()
        if len(shape) == 0:
            assert isinstance(self.implementation, scalar.Scalar)
            return space.long(space.wrap(self.implementation.get_scalar_value()))
        if shape == [1]:
            return space.int(self.descr_getitem(space, space.wrap(0)))
        raise OperationError(space.w_TypeError, space.wrap("only length-1 arrays can be converted to Python scalars"))

    def descr_float(self, space):
        shape = self.get_shape()
        if len(shape) == 0:
            assert isinstance(self.implementation, scalar.Scalar)
            return space.float(space.wrap(self.implementation.get_scalar_value()))
        if shape == [1]:
            return space.float(self.descr_getitem(space, space.wrap(0)))
        raise OperationError(space.w_TypeError, space.wrap("only length-1 arrays can be converted to Python scalars"))

    def descr_reduce(self, space):
        from rpython.rtyper.lltypesystem import rffi
        from rpython.rlib.rstring import StringBuilder
        from pypy.interpreter.mixedmodule import MixedModule
        from pypy.module.micronumpy.arrayimpl.concrete import SliceArray

        numpypy = space.getbuiltinmodule("_numpypy")
        assert isinstance(numpypy, MixedModule)
        multiarray = numpypy.get("multiarray")
        assert isinstance(multiarray, MixedModule)
        reconstruct = multiarray.get("_reconstruct")

        parameters = space.newtuple([space.gettypefor(W_NDimArray), space.newtuple([space.wrap(0)]), space.wrap("b")])

        builder = StringBuilder()
        if isinstance(self.implementation, SliceArray):
            iter = self.implementation.create_iter()
            while not iter.done():
                box = iter.getitem()
                builder.append(box.raw_str())
                iter.next()
        else:
            builder.append_charpsize(self.implementation.get_storage(), self.implementation.get_storage_size())

        state = space.newtuple([
                space.wrap(1),      # version
                self.descr_get_shape(space),
                self.get_dtype(),
                space.wrap(False),  # is_fortran
                space.wrap(builder.build()),
            ])

        return space.newtuple([reconstruct, parameters, state])

    def descr_setstate(self, space, w_state):
        from rpython.rtyper.lltypesystem import rffi

        shape = space.getitem(w_state, space.wrap(1))
        dtype = space.getitem(w_state, space.wrap(2))
        assert isinstance(dtype, interp_dtype.W_Dtype)
        isfortran = space.getitem(w_state, space.wrap(3))
        storage = space.getitem(w_state, space.wrap(4))

        self.implementation = W_NDimArray.from_shape_and_storage(space,
                [space.int_w(i) for i in space.listview(shape)],
                rffi.str2charp(space.str_w(storage), track_allocation=False),
                dtype, owning=True).implementation

    def descr___array_finalize__(self, space, w_obj):
        pass

    def descr___array_wrap__(self, space, w_obj, w_context=None):
        return w_obj

    def descr___array_prepare__(self, space, w_obj, w_context=None):
        return w_obj
        pass

@unwrap_spec(offset=int, order=str)
def descr_new_array(space, w_subtype, w_shape, w_dtype=None, w_buffer=None,
                    offset=0, w_strides=None, order='C'):
    from pypy.module.micronumpy.arrayimpl.concrete import ConcreteArray
    from pypy.module.micronumpy.support import calc_strides
    if (offset != 0 or not space.is_none(w_strides) or
        not space.is_none(w_buffer)):
        raise OperationError(space.w_NotImplementedError,
                             space.wrap("unsupported param"))
    dtype = space.interp_w(interp_dtype.W_Dtype,
          space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype))
    shape = _find_shape(space, w_shape, dtype)
    if not shape:
        return W_NDimArray.new_scalar(space, dtype)
    if space.is_w(w_subtype, space.gettypefor(W_NDimArray)):
        return W_NDimArray.from_shape(space, shape, dtype, order)
    strides, backstrides = calc_strides(shape, dtype.base, order)
    impl = ConcreteArray(shape, dtype.base, order, strides,
                                  backstrides)
    w_ret = space.allocate_instance(W_NDimArray, w_subtype)
    W_NDimArray.__init__(w_ret, impl)
    space.call_function(space.getattr(w_ret,
                        space.wrap('__array_finalize__')), w_subtype)
    return w_ret

@unwrap_spec(addr=int)
def descr__from_shape_and_storage(space, w_cls, w_shape, addr, w_dtype, w_subtype=None):
    """
    Create an array from an existing buffer, given its address as int.
    PyPy-only implementation detail.
    """
    from rpython.rtyper.lltypesystem import rffi
    from rpython.rlib.rawstorage import RAW_STORAGE_PTR
    storage = rffi.cast(RAW_STORAGE_PTR, addr)
    dtype = space.interp_w(interp_dtype.W_Dtype,
                     space.call_function(space.gettypefor(interp_dtype.W_Dtype),
                             w_dtype))
    shape = _find_shape(space, w_shape, dtype)
    if w_subtype:
        if not space.isinstance_w(w_subtype, space.w_type):
            raise OperationError(space.w_ValueError, space.wrap(
                "subtype must be a subtype of ndarray, not a class instance"))
        return W_NDimArray.from_shape_and_storage(space, shape, storage, dtype,
                             'C', False, w_subtype)
    else:
        return W_NDimArray.from_shape_and_storage(space, shape, storage, dtype)

W_NDimArray.typedef = TypeDef(
    "ndarray",
    __module__ = "numpypy",
    __new__ = interp2app(descr_new_array),

    __len__ = interp2app(W_NDimArray.descr_len),
    __getitem__ = interp2app(W_NDimArray.descr_getitem),
    __setitem__ = interp2app(W_NDimArray.descr_setitem),

    __repr__ = interp2app(W_NDimArray.descr_repr),
    __str__ = interp2app(W_NDimArray.descr_str),
    __int__ = interp2app(W_NDimArray.descr_int),
    __long__ = interp2app(W_NDimArray.descr_long),
    __float__ = interp2app(W_NDimArray.descr_float),

    __pos__ = interp2app(W_NDimArray.descr_pos),
    __neg__ = interp2app(W_NDimArray.descr_neg),
    __abs__ = interp2app(W_NDimArray.descr_abs),
    __invert__ = interp2app(W_NDimArray.descr_invert),
    __nonzero__ = interp2app(W_NDimArray.descr___nonzero__),

    __add__ = interp2app(W_NDimArray.descr_add),
    __sub__ = interp2app(W_NDimArray.descr_sub),
    __mul__ = interp2app(W_NDimArray.descr_mul),
    __div__ = interp2app(W_NDimArray.descr_div),
    __truediv__ = interp2app(W_NDimArray.descr_truediv),
    __floordiv__ = interp2app(W_NDimArray.descr_floordiv),
    __mod__ = interp2app(W_NDimArray.descr_mod),
    __divmod__ = interp2app(W_NDimArray.descr_divmod),
    __pow__ = interp2app(W_NDimArray.descr_pow),
    __lshift__ = interp2app(W_NDimArray.descr_lshift),
    __rshift__ = interp2app(W_NDimArray.descr_rshift),
    __and__ = interp2app(W_NDimArray.descr_and),
    __or__ = interp2app(W_NDimArray.descr_or),
    __xor__ = interp2app(W_NDimArray.descr_xor),

    __radd__ = interp2app(W_NDimArray.descr_radd),
    __rsub__ = interp2app(W_NDimArray.descr_rsub),
    __rmul__ = interp2app(W_NDimArray.descr_rmul),
    __rdiv__ = interp2app(W_NDimArray.descr_rdiv),
    __rtruediv__ = interp2app(W_NDimArray.descr_rtruediv),
    __rfloordiv__ = interp2app(W_NDimArray.descr_rfloordiv),
    __rmod__ = interp2app(W_NDimArray.descr_rmod),
    __rdivmod__ = interp2app(W_NDimArray.descr_rdivmod),
    __rpow__ = interp2app(W_NDimArray.descr_rpow),
    __rlshift__ = interp2app(W_NDimArray.descr_rlshift),
    __rrshift__ = interp2app(W_NDimArray.descr_rrshift),
    __rand__ = interp2app(W_NDimArray.descr_rand),
    __ror__ = interp2app(W_NDimArray.descr_ror),
    __rxor__ = interp2app(W_NDimArray.descr_rxor),

    __iadd__ = interp2app(W_NDimArray.descr_iadd),
    __isub__ = interp2app(W_NDimArray.descr_isub),
    __imul__ = interp2app(W_NDimArray.descr_imul),
    __idiv__ = interp2app(W_NDimArray.descr_idiv),
    __itruediv__ = interp2app(W_NDimArray.descr_itruediv),
    __ifloordiv__ = interp2app(W_NDimArray.descr_ifloordiv),
    __imod__ = interp2app(W_NDimArray.descr_imod),
    __ipow__ = interp2app(W_NDimArray.descr_ipow),
    __ilshift__ = interp2app(W_NDimArray.descr_ilshift),
    __irshift__ = interp2app(W_NDimArray.descr_irshift),
    __iand__ = interp2app(W_NDimArray.descr_iand),
    __ior__ = interp2app(W_NDimArray.descr_ior),
    __ixor__ = interp2app(W_NDimArray.descr_ixor),

    __eq__ = interp2app(W_NDimArray.descr_eq),
    __ne__ = interp2app(W_NDimArray.descr_ne),
    __lt__ = interp2app(W_NDimArray.descr_lt),
    __le__ = interp2app(W_NDimArray.descr_le),
    __gt__ = interp2app(W_NDimArray.descr_gt),
    __ge__ = interp2app(W_NDimArray.descr_ge),

    dtype = GetSetProperty(W_NDimArray.descr_get_dtype),
    shape = GetSetProperty(W_NDimArray.descr_get_shape,
                           W_NDimArray.descr_set_shape),
    strides = GetSetProperty(W_NDimArray.descr_get_strides),
    ndim = GetSetProperty(W_NDimArray.descr_get_ndim),
    size = GetSetProperty(W_NDimArray.descr_get_size),
    itemsize = GetSetProperty(W_NDimArray.descr_get_itemsize),
    nbytes = GetSetProperty(W_NDimArray.descr_get_nbytes),

    fill = interp2app(W_NDimArray.descr_fill),
    tostring = interp2app(W_NDimArray.descr_tostring),

    mean = interp2app(W_NDimArray.descr_mean),
    sum = interp2app(W_NDimArray.descr_sum),
    prod = interp2app(W_NDimArray.descr_prod),
    max = interp2app(W_NDimArray.descr_max),
    min = interp2app(W_NDimArray.descr_min),
    put = interp2app(W_NDimArray.descr_put),
    argmax = interp2app(W_NDimArray.descr_argmax),
    argmin = interp2app(W_NDimArray.descr_argmin),
    all = interp2app(W_NDimArray.descr_all),
    any = interp2app(W_NDimArray.descr_any),
    dot = interp2app(W_NDimArray.descr_dot),
    var = interp2app(W_NDimArray.descr_var),
    std = interp2app(W_NDimArray.descr_std),

    cumsum = interp2app(W_NDimArray.descr_cumsum),
    cumprod = interp2app(W_NDimArray.descr_cumprod),

    copy = interp2app(W_NDimArray.descr_copy),
    reshape = interp2app(W_NDimArray.descr_reshape),
    T = GetSetProperty(W_NDimArray.descr_get_transpose),
    transpose = interp2app(W_NDimArray.descr_get_transpose),
    tolist = interp2app(W_NDimArray.descr_tolist),
    flatten = interp2app(W_NDimArray.descr_flatten),
    ravel = interp2app(W_NDimArray.descr_ravel),
    take = interp2app(W_NDimArray.descr_take),
    compress = interp2app(W_NDimArray.descr_compress),
    repeat = interp2app(W_NDimArray.descr_repeat),
    swapaxes = interp2app(W_NDimArray.descr_swapaxes),
    nonzero = interp2app(W_NDimArray.descr_nonzero),
    flat = GetSetProperty(W_NDimArray.descr_get_flatiter,
                          W_NDimArray.descr_set_flatiter),
    item = interp2app(W_NDimArray.descr_item),
    real = GetSetProperty(W_NDimArray.descr_get_real,
                          W_NDimArray.descr_set_real),
    imag = GetSetProperty(W_NDimArray.descr_get_imag,
                          W_NDimArray.descr_set_imag),
    conj = interp2app(W_NDimArray.descr_conj),

    argsort  = interp2app(W_NDimArray.descr_argsort),
    sort  = interp2app(W_NDimArray.descr_sort),
    astype   = interp2app(W_NDimArray.descr_astype),
    base     = GetSetProperty(W_NDimArray.descr_get_base),
    byteswap = interp2app(W_NDimArray.descr_byteswap),
    choose   = interp2app(W_NDimArray.descr_choose),
    clip     = interp2app(W_NDimArray.descr_clip),
    round    = interp2app(W_NDimArray.descr_round),
    data     = GetSetProperty(W_NDimArray.descr_get_data),
    diagonal = interp2app(W_NDimArray.descr_diagonal),
    trace = interp2app(W_NDimArray.descr_trace),
    view = interp2app(W_NDimArray.descr_view),

    ctypes = GetSetProperty(W_NDimArray.descr_get_ctypes), # XXX unimplemented
    __array_interface__ = GetSetProperty(W_NDimArray.descr_array_iface),
    __weakref__ = make_weakref_descr(W_NDimArray),
    _from_shape_and_storage = interp2app(descr__from_shape_and_storage,
                                         as_classmethod=True),
    __pypy_data__ = GetSetProperty(W_NDimArray.fget___pypy_data__,
                                   W_NDimArray.fset___pypy_data__,
                                   W_NDimArray.fdel___pypy_data__),
    __reduce__ = interp2app(W_NDimArray.descr_reduce),
    __setstate__ = interp2app(W_NDimArray.descr_setstate),
    __array_finalize__ = interp2app(W_NDimArray.descr___array_finalize__),
    __array_prepare__ = interp2app(W_NDimArray.descr___array_prepare__),
    __array_wrap__ = interp2app(W_NDimArray.descr___array_wrap__),
    __array__         = interp2app(W_NDimArray.descr___array__),
)

@unwrap_spec(ndmin=int, copy=bool, subok=bool)
def array(space, w_object, w_dtype=None, copy=True, w_order=None, subok=False,
          ndmin=0):
    # for anything that isn't already an array, try __array__ method first
    if not isinstance(w_object, W_NDimArray):
        w___array__ = space.lookup(w_object, "__array__")
        if w___array__ is not None:
            if space.is_none(w_dtype):
                w_dtype = space.w_None
            w_array = space.get_and_call_function(w___array__, w_object, w_dtype)
            if isinstance(w_array, W_NDimArray):
                # feed w_array back into array() for other properties
                return array(space, w_array, w_dtype, False, w_order, subok, ndmin)
            else:
                raise operationerrfmt(space.w_ValueError,
                        "object __array__ method not producing an array")

    # scalars and strings w/o __array__ method
    isstr = space.isinstance_w(w_object, space.w_str)
    if not issequence_w(space, w_object) or isstr:
        if space.is_none(w_dtype) or isstr:
            w_dtype = interp_ufuncs.find_dtype_for_scalar(space, w_object)
        dtype = space.interp_w(interp_dtype.W_Dtype,
                space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype))
        return W_NDimArray.new_scalar(space, dtype, w_object)

    if space.is_none(w_order):
        order = 'C'
    else:
        order = space.str_w(w_order)
        if order != 'C':  # or order != 'F':
            raise operationerrfmt(space.w_ValueError, "Unknown order: %s",
                                  order)

    # arrays with correct dtype
    dtype = interp_dtype.decode_w_dtype(space, w_dtype)
    if isinstance(w_object, W_NDimArray) and \
        (space.is_none(w_dtype) or w_object.get_dtype() is dtype):
        shape = w_object.get_shape()
        if copy:
            w_ret = w_object.descr_copy(space)
        else:
            if ndmin<= len(shape):
                return w_object
            new_impl = w_object.implementation.set_shape(space, w_object, shape)
            w_ret = W_NDimArray(new_impl)
        if ndmin > len(shape):
            shape = [1] * (ndmin - len(shape)) + shape
            w_ret.implementation = w_ret.implementation.set_shape(space,
                                            w_ret, shape)
        return w_ret

    # not an array or incorrect dtype
    shape, elems_w = find_shape_and_elems(space, w_object, dtype)
    if dtype is None or (
                 dtype.is_str_or_unicode() and dtype.itemtype.get_size() < 1):
        for w_elem in elems_w:
            dtype = interp_ufuncs.find_dtype_for_scalar(space, w_elem,
                                                        dtype)
            #if dtype is interp_dtype.get_dtype_cache(space).w_float64dtype:
            #    break

        if dtype is None:
            dtype = interp_dtype.get_dtype_cache(space).w_float64dtype
    if dtype.is_str_or_unicode() and dtype.itemtype.get_size() < 1:
        # promote S0 -> S1, U0 -> U1
        dtype = interp_dtype.variable_dtype(space, dtype.char + '1')
    if ndmin > len(shape):
        shape = [1] * (ndmin - len(shape)) + shape
    w_arr = W_NDimArray.from_shape(space, shape, dtype, order=order)
    arr_iter = w_arr.create_iter()
    for w_elem in elems_w:
        arr_iter.setitem(dtype.coerce(space, w_elem))
        arr_iter.next()
    return w_arr

@unwrap_spec(order=str)
def zeros(space, w_shape, w_dtype=None, order='C'):
    dtype = space.interp_w(interp_dtype.W_Dtype,
        space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype)
    )
    shape = _find_shape(space, w_shape, dtype)
    if not shape:
        return W_NDimArray.new_scalar(space, dtype, space.wrap(0))
    return space.wrap(W_NDimArray.from_shape(space, shape, dtype=dtype, order=order))

@unwrap_spec(order=str)
def ones(space, w_shape, w_dtype=None, order='C'):
    dtype = space.interp_w(interp_dtype.W_Dtype,
        space.call_function(space.gettypefor(interp_dtype.W_Dtype), w_dtype)
    )
    shape = _find_shape(space, w_shape, dtype)
    if not shape:
        return W_NDimArray.new_scalar(space, dtype, space.wrap(0))
    w_arr = W_NDimArray.from_shape(space, shape, dtype=dtype, order=order)
    one = dtype.box(1)
    w_arr.fill(one)
    return space.wrap(w_arr)

def _reconstruct(space, w_subtype, w_shape, w_dtype):
    return descr_new_array(space, w_subtype, w_shape, w_dtype)

def build_scalar(space, w_dtype, w_state):
    from rpython.rtyper.lltypesystem import rffi, lltype

    assert isinstance(w_dtype, interp_dtype.W_Dtype)

    state = rffi.str2charp(space.str_w(w_state))
    box = w_dtype.itemtype.box_raw_data(state)
    lltype.free(state, flavor="raw")
    return box


W_FlatIterator.typedef = TypeDef(
    'flatiter',
    __iter__ = interp2app(W_FlatIterator.descr_iter),
    __getitem__ = interp2app(W_FlatIterator.descr_getitem),
    __setitem__ = interp2app(W_FlatIterator.descr_setitem),
    __len__ = interp2app(W_FlatIterator.descr_len),

    __eq__ = interp2app(W_FlatIterator.descr_eq),
    __ne__ = interp2app(W_FlatIterator.descr_ne),
    __lt__ = interp2app(W_FlatIterator.descr_lt),
    __le__ = interp2app(W_FlatIterator.descr_le),
    __gt__ = interp2app(W_FlatIterator.descr_gt),
    __ge__ = interp2app(W_FlatIterator.descr_ge),

    next = interp2app(W_FlatIterator.descr_next),
    base = GetSetProperty(W_FlatIterator.descr_base),
    index = GetSetProperty(W_FlatIterator.descr_index),
    coords = GetSetProperty(W_FlatIterator.descr_coords),
)

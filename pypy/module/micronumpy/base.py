from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from rpython.tool.pairtype import extendabletype
from pypy.module.micronumpy import support

def wrap_impl(space, w_cls, w_instance, impl):
    if w_cls is None or space.is_w(w_cls, space.gettypefor(W_NDimArray)):
        w_ret = W_NDimArray(impl)
    else:
        w_ret = space.allocate_instance(W_NDimArray, w_cls)
        W_NDimArray.__init__(w_ret, impl)
        assert isinstance(w_ret, W_NDimArray)
        space.call_method(w_ret, '__array_finalize__', w_instance)
    return w_ret


class ArrayArgumentException(Exception):
    pass


class W_NumpyObject(W_Root):
    """Base class for ndarrays and scalars (aka boxes)."""
    _attrs_ = []


class W_NDimArray(W_NumpyObject):
    __metaclass__ = extendabletype

    def __init__(self, implementation):
        from pypy.module.micronumpy.concrete import BaseConcreteArray
        assert isinstance(implementation, BaseConcreteArray)
        assert isinstance(self, W_NDimArray)
        self.implementation = implementation

    @staticmethod
    def from_shape(space, shape, dtype, order='C', w_instance=None, zero=True):
        from pypy.module.micronumpy import concrete
        from pypy.module.micronumpy.strides import calc_strides
        strides, backstrides = calc_strides(shape, dtype.base, order)
        impl = concrete.ConcreteArray(shape, dtype.base, order, strides,
                                      backstrides, zero=zero)
        if w_instance:
            return wrap_impl(space, space.type(w_instance), w_instance, impl)
        return W_NDimArray(impl)

    @staticmethod
    def from_shape_and_storage(space, shape, storage, dtype, storage_bytes=-1,
                               order='C', owning=False, w_subtype=None,
                               w_base=None, writable=True, strides=None):
        from pypy.module.micronumpy import concrete
        from pypy.module.micronumpy.strides import (calc_strides,
                                                    calc_backstrides)
        isize = dtype.elsize
        if storage_bytes > 0 :
            totalsize = support.product(shape) * isize
            if totalsize > storage_bytes:
                raise OperationError(space.w_TypeError, space.wrap(
                    "buffer is too small for requested array"))
        else:
            storage_bytes = support.product(shape) * isize
        if strides is None:
            strides, backstrides = calc_strides(shape, dtype, order)
        else:
            if len(strides) != len(shape):
                raise oefmt(space.w_ValueError,
                    'strides, if given, must be the same length as shape')
            for i in range(len(strides)):
                if strides[i] < 0 or strides[i]*shape[i] > storage_bytes:
                    raise oefmt(space.w_ValueError,
                        'strides is incompatible with shape of requested '
                        'array and size of buffer')
            backstrides = calc_backstrides(strides, shape)
        if w_base is not None:
            if owning:
                raise OperationError(space.w_ValueError,
                        space.wrap("Cannot have owning=True when specifying a buffer"))
            if writable:
                impl = concrete.ConcreteArrayWithBase(shape, dtype, order, strides,
                                                      backstrides, storage, w_base)
            else:
                impl = concrete.ConcreteNonWritableArrayWithBase(shape, dtype, order,
                                                                 strides, backstrides,
                                                                 storage, w_base)
        elif owning:
            # Will free storage when GCd
            impl = concrete.ConcreteArray(shape, dtype, order, strides,
                                          backstrides, storage=storage)
        else:
            impl = concrete.ConcreteArrayNotOwning(shape, dtype, order, strides,
                                                   backstrides, storage)
        if w_subtype:
            w_ret = space.allocate_instance(W_NDimArray, w_subtype)
            W_NDimArray.__init__(w_ret, impl)
            space.call_method(w_ret, '__array_finalize__', w_subtype)
            return w_ret
        return W_NDimArray(impl)

    @staticmethod
    def new_slice(space, offset, strides, backstrides, shape, parent, orig_arr, dtype=None):
        from pypy.module.micronumpy import concrete

        impl = concrete.SliceArray(offset, strides, backstrides, shape, parent,
                                   orig_arr, dtype)
        return wrap_impl(space, space.type(orig_arr), orig_arr, impl)

    @staticmethod
    def new_scalar(space, dtype, w_val=None):
        if w_val is not None:
            w_val = dtype.coerce(space, w_val)
        else:
            w_val = dtype.coerce(space, space.wrap(0))
        return convert_to_array(space, w_val)

    @staticmethod
    def from_scalar(space, w_scalar):
        """Convert a scalar into a 0-dim array"""
        dtype = w_scalar.get_dtype(space)
        w_arr = W_NDimArray.from_shape(space, [], dtype)
        w_arr.set_scalar_value(w_scalar)
        return w_arr

    def get_shape(self):
        return self.implementation.get_shape()

    def get_dtype(self):
        return self.implementation.dtype

    def get_order(self):
        return self.implementation.order

    def ndims(self):
        return len(self.get_shape())
    ndims._always_inline_ = True


def convert_to_array(space, w_obj):
    from pypy.module.micronumpy.ctors import array
    if isinstance(w_obj, W_NDimArray):
        return w_obj
    return array(space, w_obj)


from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root
from rpython.tool.pairtype import extendabletype
from pypy.module.micronumpy.support import calc_strides
from pypy.module.micronumpy.arrayimpl.base import BaseArrayImplementation


def issequence_w(space, w_obj):
    return (space.isinstance_w(w_obj, space.w_tuple) or
            space.isinstance_w(w_obj, space.w_list) or
            isinstance(w_obj, W_NDimArray))

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


class W_NDimArray(W_Root):
    __metaclass__ = extendabletype

    def __init__(self, implementation):
        assert isinstance(implementation, BaseArrayImplementation)
        assert isinstance(self, W_NDimArray)
        self.implementation = implementation

    @staticmethod
    def from_shape(space, shape, dtype, order='C', w_instance=None):
        from pypy.module.micronumpy.arrayimpl import concrete, scalar

        if not shape:
            w_val = dtype.base.coerce(space, space.wrap(0))
            impl = scalar.Scalar(dtype.base, w_val)
        else:
            strides, backstrides = calc_strides(shape, dtype.base, order)
            impl = concrete.ConcreteArray(shape, dtype.base, order, strides,
                                      backstrides)
        if w_instance:
            return wrap_impl(space, space.type(w_instance), w_instance, impl)
        return W_NDimArray(impl)

    @staticmethod
    def from_shape_and_storage(space, shape, storage, dtype, order='C', owning=False, w_subtype=None):
        from pypy.module.micronumpy.arrayimpl import concrete
        assert shape
        strides, backstrides = calc_strides(shape, dtype, order)
        if owning:
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
        from pypy.module.micronumpy.arrayimpl import concrete

        impl = concrete.SliceArray(offset, strides, backstrides, shape, parent,
                                   orig_arr, dtype)
        return wrap_impl(space, space.type(orig_arr), orig_arr, impl)

    @staticmethod
    def new_scalar(space, dtype, w_val=None):
        from pypy.module.micronumpy.arrayimpl import scalar

        if w_val is not None:
            w_val = dtype.coerce(space, w_val)
        else:
            w_val = dtype.coerce(space, space.wrap(0))
        return W_NDimArray(scalar.Scalar(dtype, w_val))


def convert_to_array(space, w_obj, use_prepare=False):
    #XXX: This whole routine should very likely simply be array()
    from pypy.module.micronumpy.interp_numarray import array
    from pypy.module.micronumpy import interp_ufuncs

    if isinstance(w_obj, W_NDimArray):
        return w_obj
    else:
        # Use __array__() method if it exists
        w_array = space.lookup(w_obj, "__array__")
        if w_array is not None:
            w_result = space.get_and_call_function(w_array, w_obj)
            if isinstance(w_result, W_NDimArray):
                return w_result
            else:
                raise OperationError(space.w_ValueError,
                        space.wrap("object __array__ method not producing an array"))
        elif issequence_w(space, w_obj):
            # Convert to array.
            return array(space, w_obj, w_order=None)
        else:
            # If it's a scalar
            dtype = interp_ufuncs.find_dtype_for_scalar(space, w_obj)
            return W_NDimArray.new_scalar(space, dtype, w_obj)

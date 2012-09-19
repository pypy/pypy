
from pypy.module.micronumpy.arrayimpl import base
from pypy.module.micronumpy.base import W_NDimArray
from pypy.module.micronumpy import support
from pypy.interpreter.error import OperationError

class ScalarIterator(base.BaseArrayIterator):
    def __init__(self, v):
        self.v = v

    def next(self):
        pass

    def getitem(self):
        return self.v

    def setitem(self, v):
        raise Exception("Don't call setitem on scalar iterators")

    def done(self):
        raise Exception("should not call done on scalar")

    def reset(self):
        pass

class Scalar(base.BaseArrayImplementation):
    def __init__(self, dtype, value=None):
        self.dtype = dtype
        self.value = value

    def is_scalar(self):
        return True

    def get_shape(self):
        return []

    def create_iter(self, shape):
        return ScalarIterator(self.value)

    def get_scalar_value(self):
        return self.value

    def set_scalar_value(self, w_val):
        self.value = w_val.convert_to(self.dtype)

    def copy(self):
        scalar = Scalar(self.dtype)
        scalar.value = self.value
        return scalar

    def get_size(self):
        return 1

    def transpose(self):
        return self

    def descr_getitem(self, space, w_idx):
        raise OperationError(space.w_IndexError,
                             space.wrap("scalars cannot be indexed"))

    def getitem_index(self, space, idx):
        raise OperationError(space.w_IndexError,
                             space.wrap("scalars cannot be indexed"))

    def descr_setitem(self, space, w_idx, w_val):
        raise OperationError(space.w_IndexError,
                             space.wrap("scalars cannot be indexed"))
        
    def setitem_index(self, space, idx, w_val):
        raise OperationError(space.w_IndexError,
                             space.wrap("scalars cannot be indexed"))
    def set_shape(self, space, new_shape):
        if not new_shape:
            return self
        if support.product(new_shape) == 1:
            arr = W_NDimArray.from_shape(new_shape, self.dtype)
            arr_iter = arr.create_iter(new_shape)
            arr_iter.setitem(self.value)
            return arr.implementation
        raise OperationError(space.w_ValueError, space.wrap(
            "total size of the array must be unchanged"))

    def reshape(self, space, new_shape):
        return self.set_shape(space, new_shape)
        
    def create_axis_iter(self, shape, dim):
        raise Exception("axis iter should not happen on scalar")

    def swapaxes(self, axis1, axis2):
        raise Exception("should not be called")

    def fill(self, w_value):
        self.value = w_value

    def get_storage_as_int(self, space):
        raise OperationError(space.w_ValueError,
                             space.wrap("scalars have no address"))

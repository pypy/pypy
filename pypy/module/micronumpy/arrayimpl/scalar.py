
from pypy.module.micronumpy.arrayimpl import base

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
        return False

class Scalar(base.BaseArrayImplementation):
    def __init__(self, dtype):
        self.value = None
        self.dtype = dtype

    def is_scalar(self):
        return True

    def get_shape(self):
        return []

    def create_iter(self, shape):
        return ScalarIterator(self.value)

    def set_scalar_value(self, value):
        self.value = value

    def get_scalar_value(self):
        return self.value

    def copy(self):
        scalar = Scalar(self.dtype)
        scalar.value = self.value
        return scalar

    def get_size(self):
        return 1

    def transpose(self):
        return self

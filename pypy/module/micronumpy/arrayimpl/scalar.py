
from pypy.module.micronumpy.arrayimpl import base

class Scalar(base.BaseArrayImplementation):
    def __init__(self, dtype):
        self.value = None
        self.dtype = dtype

    def is_scalar(self):
        return True

    def get_shape(self):
        return []

    def set_scalar_value(self, value):
        self.value = value

    def get_scalar_value(self):
        return self.value

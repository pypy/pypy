
from pypy.module.micronumpy.arrayimpl import base

class Scalar(base.BaseArrayImplementation):
    is_scalar = True
    
    def __init__(self, dtype):
        self.value = None
        self.dtype = dtype

    def get_shape(self):
        return []

    def set_scalar_value(self, value):
        self.value = value

    def get_scalar_value(self):
        return self.value

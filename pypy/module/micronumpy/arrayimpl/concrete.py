
from pypy.module.micronumpy.arrayimpl import base

class ConcreteArray(base.BaseArrayImplementation):
    def __init__(self, shape, dtype):
        self.shape = shape

    def get_shape(self):
        return self.shape

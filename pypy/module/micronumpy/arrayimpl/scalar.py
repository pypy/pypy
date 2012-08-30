
from pypy.module.micronumpy.arrayimpl import base

class Scalar(base.BaseArrayImplementation):
    def __init__(self, dtype):
        pass

    def get_shape(self):
        return []

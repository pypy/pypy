
from pypy.module.micronumpy.arrayimpl import base

class Scalar(base.BaseArrayImplementation):
    is_scalar = True
    
    def __init__(self, dtype):
        pass

    def get_shape(self):
        return []

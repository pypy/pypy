
from pypy.module.micronumpy.arrayimpl import scalar, concrete

def create_implementation(shape, dtype):
    if not shape:
        return scalar.Scalar(dtype)
    else:
        return concrete.ConcreteArray(shape, dtype)

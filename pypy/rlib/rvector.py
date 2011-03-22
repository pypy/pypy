
from pypy.rpython.extregistry import ExtRegistryEntry

class VectorContainer(object):
    """ Class that is a container for multiple float/int objects.
    Can be represented at jit-level by a single register, like xmm
    on x86 architecture
    """

class FloatVectorContainer(VectorContainer):
    """ A container for float values
    """
    def __init__(self, val1, val2):
        self.v1 = val1
        self.v2 = val2

    def __repr__(self):
        return '<FloatVector %f %f>' % (self.v1, self.v2)

def vector_float_read(arr, index):
    return FloatVectorContainer(arr[index], arr[index + 1])
vector_float_read.oopspec = 'vector_float_read(arr, index)'

def vector_float_write(arr, index, container):
    arr[index] = container.v1
    arr[index + 1] = container.v2
vector_float_write.oopspec = 'vector_from_write(arr, index, container)'

def vector_float_add(left, right):
    return FloatVectorContainer(left.v1 + right.v1, left.v2 + right.v2)
vector_float_add.oopspec = 'vector_float_add(left, right)'

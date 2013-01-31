
from pypy.module.micronumpy.arrayimpl.base import BaseArrayImplementation
from rpython.rlib.rawstorage import free_raw_storage, alloc_raw_storage

class VoidBoxStorage(BaseArrayImplementation):
    def __init__(self, size, dtype):
        self.storage = alloc_raw_storage(size)
        self.dtype = dtype
        self.size = size

    def __del__(self):
        free_raw_storage(self.storage)

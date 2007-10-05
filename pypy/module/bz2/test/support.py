class CheckAllocation:
    def teardown_method(self, fun):
        from pypy.rpython.lltypesystem import ll2ctypes
        import gc
        gc.collect()
        gc.collect()
        gc.collect() # to make sure we disallocate buffers
        assert not ll2ctypes.ALLOCATED

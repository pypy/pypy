class CheckAllocation:
    def teardown_method(self, fun):
        from pypy.rpython.lltypesystem import ll2ctypes
        import gc
        tries = 20
        while tries and ll2ctypes.ALLOCATED:
            gc.collect() # to make sure we disallocate buffers
            tries -= 1
        assert not ll2ctypes.ALLOCATED

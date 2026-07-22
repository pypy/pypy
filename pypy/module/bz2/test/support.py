class CheckAllocation:
    def teardown_method(self, fun):
        from rpython.rtyper.lltypesystem import ll2ctypes
        import gc
        tries = 20
        while tries:
            # gc-kind entries (rpy_string keepalives, some created while
            # running finalizers below) are not real leaks -- drop them so
            # only raw buffer allocations remain to be checked.
            for key, value in list(ll2ctypes.ALLOCATED.items()):
                if value._TYPE._gckind == 'gc':
                    del ll2ctypes.ALLOCATED[key]
            if not ll2ctypes.ALLOCATED:
                break
            gc.collect() # to make sure we disallocate buffers
            self.space.getexecutioncontext()._run_finalizers_now()
            tries -= 1
        assert not ll2ctypes.ALLOCATED

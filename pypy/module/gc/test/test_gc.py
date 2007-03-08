class AppTestGC(object):
    def test_collect(self):
        import gc
        gc.collect() # mostly a "does not crash" kind of test

    def test_estimate_heap_size(self):
        import sys, gc
        if sys.platform == "linux2":
            assert gc.estimate_heap_size() > 1024
        else:
            raises(RuntimeError, gc.estimate_heap_size)

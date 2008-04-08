class AppTestGC(object):
    def test_collect(self):
        import gc
        gc.collect() # mostly a "does not crash" kind of test

    def test_disable_finalizers(self):
        # on top of PyPy we can't easily test this, except by using
        # obsure hacks, so for now we'll live with a "does not crash"
        # kind of test
        import gc
        gc.disable_finalizers()
        gc.enable_finalizers()
        # we can test that nesting appears to work
        gc.disable_finalizers()
        gc.disable_finalizers()
        gc.enable_finalizers()
        gc.enable_finalizers()
        raises(ValueError, gc.enable_finalizers)

    def test_estimate_heap_size(self):
        import sys, gc
        if sys.platform == "linux2":
            assert gc.estimate_heap_size() > 1024
        else:
            raises(RuntimeError, gc.estimate_heap_size)

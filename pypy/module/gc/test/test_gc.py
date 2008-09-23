class AppTestGC(object):
    def test_collect(self):
        import gc
        gc.collect() # mostly a "does not crash" kind of test

    def test_disable_finalizers(self):
        import gc

        class X(object):
            created = 0
            deleted = 0
            def __init__(self):
                X.created += 1
            def __del__(self):
                X.deleted += 1

        class OldX:
            created = 0
            deleted = 0
            def __init__(self):
                OldX.created += 1
            def __del__(self):
                OldX.deleted += 1

        def runtest(should_be_enabled):
            runtest1(should_be_enabled, X)
            runtest1(should_be_enabled, OldX)

        def runtest1(should_be_enabled, Cls):
            gc.collect()
            if should_be_enabled:
                assert Cls.deleted == Cls.created
            else:
                old_deleted = Cls.deleted
            Cls(); Cls(); Cls()
            gc.collect()
            if should_be_enabled:
                assert Cls.deleted == Cls.created
            else:
                assert Cls.deleted == old_deleted

        runtest(True)
        gc.disable_finalizers()
        runtest(False)
        runtest(False)
        gc.enable_finalizers()
        runtest(True)
        # test nesting
        gc.disable_finalizers()
        gc.disable_finalizers()
        runtest(False)
        gc.enable_finalizers()
        runtest(False)
        gc.enable_finalizers()
        runtest(True)
        raises(ValueError, gc.enable_finalizers)
        runtest(True)

    def test_estimate_heap_size(self):
        import sys, gc
        if sys.platform == "linux2":
            assert gc.estimate_heap_size() > 1024
        else:
            raises(RuntimeError, gc.estimate_heap_size)

    def test_enable(self):
        import gc
        assert gc.isenabled()
        gc.disable()
        assert not gc.isenabled()
        gc.enable()
        assert gc.isenabled()
        gc.enable()
        assert gc.isenabled()
        

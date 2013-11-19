import py

class AppTestGC(object):
    def test_collect(self):
        import gc
        gc.collect() # mostly a "does not crash" kind of test
        gc.collect(0) # mostly a "does not crash" kind of test

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

    def test_enable(self):
        import gc
        assert gc.isenabled()
        gc.disable()
        assert not gc.isenabled()
        gc.enable()
        assert gc.isenabled()
        gc.enable()
        assert gc.isenabled()

class AppTestGcDumpHeap(object):
    pytestmark = py.test.mark.xfail(run=False)

    def setup_class(cls):
        import py
        from rpython.tool.udir import udir
        from rpython.rlib import rgc
        class X(object):
            def __init__(self, count, size, links):
                self.count = count
                self.size = size
                self.links = links
        
        def fake_heap_stats():
            return [X(1, 12, [0, 0]), X(2, 10, [10, 0])]
        
        cls._heap_stats = rgc._heap_stats
        rgc._heap_stats = fake_heap_stats
        fname = udir.join('gcdump.log')
        cls.w_fname = cls.space.wrap(str(fname))
        cls._fname = fname

    def teardown_class(cls):
        import py
        from rpython.rlib import rgc
        
        rgc._heap_stats = cls._heap_stats
        assert py.path.local(cls._fname).read() == '1 12 0,0\n2 10 10,0\n'
    
    def test_gc_heap_stats(self):
        import gc
        gc.dump_heap_stats(self.fname)


class AppTestGcMethodCache(object):
    spaceconfig = {"objspace.std.withmethodcache": True}

    def test_clear_method_cache(self):
        import gc, weakref
        rlist = []
        def f():
            class C(object):
                def f(self):
                    pass
            C().f()    # Fill the method cache
            rlist.append(weakref.ref(C))
        for i in range(10):
            f()
        gc.collect()    # the classes C should all go away here
        # the last class won't go in mapdict, as long as the code object of f
        # is around
        rlist.pop()
        for r in rlist:
            assert r() is None

class AppTestGcMapDictIndexCache(AppTestGcMethodCache):
    spaceconfig = {"objspace.std.withmethodcache": True,
                   "objspace.std.withmapdict": True}

    def test_clear_index_cache(self):
        import gc, weakref
        rlist = []
        def f():
            class C(object):
                def f(self):
                    pass
            c = C()
            c.x = 1
            getattr(c, "x") # fill the index cache without using the local cache
            getattr(c, "x")
            rlist.append(weakref.ref(C))
        for i in range(5):
            f()
        gc.collect()    # the classes C should all go away here
        for r in rlist:
            assert r() is None

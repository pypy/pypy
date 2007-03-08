class AppTestGC(object):
    def test_collect(self):
        import gc
        gc.collect() # mostly a "does not crash" kind of test

import autopath
from pypy.tool.cache import Cache 

class TestCache: 
    def test_getorbuild(self):
        cache = Cache()
        assert cache.getorbuild(1, lambda k,s: 42, None) == 42
        assert cache.getorbuild(1, lambda k,s: self.fail(), None) == 42
        # XXX   cannot test that any longer:
        # XXX   hash(cache) now freezes the cache "just-in-time".
        # XXX      --disabled-- self.assertRaises(TypeError, hash, cache)
        cache.clear()
        assert cache.getorbuild(1, lambda k,s: 44, None) == 44
        assert cache.getorbuild(1, lambda k,s: self.fail(), None) == 44
        cache.freeze()
        hash(cache)
        assert cache.getorbuild(1, lambda k,s: self.fail(), None) == 44
        raises(TypeError, cache.clear)
        raises(AssertionError, cache.getorbuild,
                          2, lambda k,s: self.fail(), 4)

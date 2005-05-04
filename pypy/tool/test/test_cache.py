import autopath
from pypy.tool.cache import Cache 

class TestCache: 
    def test_getorbuild(self):
        cache = Cache()
        assert cache.getorbuild(1, lambda k,s: 42, None) == 42
        assert cache.getorbuild(1, lambda k,s: self.fail(), None) == 42
        assert cache.getorbuild(2, lambda k,s: 24, None) == 24
        assert cache.getorbuild(1, lambda k,s: self.fail(), None) == 42
        assert cache.getorbuild(2, lambda k,s: self.fail(), None) == 24

import autopath
import unittest
from pypy.tool.cache import Cache 

class TestCache(unittest.TestCase): 
    def test_getorbuild(self):
        cache = Cache()
        assert cache.getorbuild(1, lambda k,s: 42, None) == 42
        assert cache.getorbuild(1, lambda k,s: self.fail(), None) == 42
        self.assertRaises(TypeError, hash, cache)
        cache.clear()
        assert cache.getorbuild(1, lambda k,s: 44, None) == 44
        assert cache.getorbuild(1, lambda k,s: self.fail(), None) == 44
        cache.freeze()
        hash(cache)
        assert cache.getorbuild(1, lambda k,s: self.fail(), None) == 44
        self.assertRaises(TypeError, cache.clear)
        self.assertRaises(AssertionError, cache.getorbuild,
                          2, lambda k,s: self.fail(), 4)
   
if __name__ == '__main__':
    unittest.main() 

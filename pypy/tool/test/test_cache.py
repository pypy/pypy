import autopath
import unittest
from pypy.tool.cache import Cache 

class TestCache(unittest.TestCase): 
    def test_getorbuild(self):
        cache = Cache()
        cache.getorbuild(1, lambda k,s: 42, None)
        assert 1 in cache 
        assert cache[1] == 42 
        assert cache.getorbuild(1, lambda k,s: 44, None) == 42 
        self.assertRaises(TypeError, hash, cache)
        cache.freeze()
        hash(cache) 
   
if __name__ == '__main__':
    unittest.main() 

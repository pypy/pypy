
import py
from pypy.tool.pytest.overview import ResultCache 

class TestResultCache: 
    def setup_class(cls): 
        cls.rc = ResultCache() 
        cls.rc.parselatest()

    def test_getlatest_all(self): 
        for type in 'error', 'timeout', 'ok': 
            for name in self.rc.getnames(): 
                result = self.rc.getlatest(name, **{type:1})
                if result: 
                    meth = getattr(result, 'is'+type)
                    assert meth()

    def test_getlatest_datetime(self): 
        result = self.rc.getlatest('test_datetime', ok=1) 
        assert result

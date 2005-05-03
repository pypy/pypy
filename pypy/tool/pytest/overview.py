from pypy.tool.pytest.confpath import testresultdir 
from pypy.tool.pytest import result 


class ResultCache: 
    def __init__(self): 
        self.name2result = {}

    def parselatest(self): 
        def filefilter(p): 
            return p.check(fnmatch='test_*.txt', file=1)
        def rec(p): 
            return p.check(dotfile=0)
        for x in testresultdir.visit(filefilter, rec): 
            self.parse_one(x)
    
    def parse_one(self, resultpath): 
        try: 
            res = result.ResultFromMime(resultpath) 
            ver = res['testreport-version']
            if ver != "1.1":
                raise TypeError
        except TypeError: 
            return
        name = res.fspath.purebasename 
        self.name2result.setdefault(name, []).append(res) 
        return res 

    def getnames(self): 
        return self.name2result.keys()

    def getlatest(self, name, timeout=0, error=0, ok=0): 
        l = []
        resultlist = self.name2result[name]
        maxrev = 0
        maxresult = None
        for res in resultlist: 
            resrev = res['pypy-revision']
            if resrev == 'unknown': 
                continue 
            if resrev <= maxrev: 
                continue 
            if timeout or error or ok:
                if not (timeout and res.istimeout() or
                        error and res.iserror() or 
                        ok and res.isok()): 
                    continue 
            maxrev = resrev 
            maxresult = res 
        return maxresult 


import py

from pypy.tool.bench.pypyresult import ResultDB
import pickle

def setup_module(mod):
    mod.tmpdir = py.test.ensuretemp(__name__) 

def gettestpickle(cache=[]):
    if cache:
        return cache[0]
    pp = tmpdir.join("testpickle")
    f = pp.open("wb")
    pickle.dump({'./pypy-llvm-39474-faassen-c_richards': 5}, f)
    pickle.dump({'./pypy-llvm-39474-faassen-c_richards': 42.0}, f)
    f.close()
    cache.append(pp)
    return pp

def test_unpickle():
    pp = gettestpickle()
    db = ResultDB()
    db.parsepickle(pp)
    assert len(db.benchmarks) == 1
    l = db.getbenchmarks(name="c_richards")
    assert len(l) == 1
    bench = l[0]
    assert bench.executable == "pypy-llvm-39474-faassen"
    assert bench.name == "c_richards"
    assert bench.revision == 39474
    assert bench.numruns == 5
    assert bench.besttime == 42.0
    

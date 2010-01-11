
import sys
from pypy.translator.benchmark.benchmarks import (run_richards, Benchmark,
     run_mako, check_mako)

def test_run_richards():
    bm = Benchmark('richards', run_richards, False, 'ms')
    assert bm.check()
    res = bm.run(sys.executable)
    assert isinstance(res, float)

def test_run_mako():
    bm = Benchmark('mako', run_mako, False,
                   's', check_mako)
    assert bm.check()
    res = bm.run(sys.executable)
    assert isinstance(res, float)

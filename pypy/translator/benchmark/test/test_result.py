import py
from pypy.translator.benchmark import result

py.test.skip("not doing TDD for this :/")

temp = py.test.ensuretemp("report")

def test_simple():
    fname = temp.join("simple")
    b = result.BenchmarkResult()

    b.update('foo', 1, True)
    assert b.get_best_result('foo') == 1

    b.update('foo', 2, True)
    assert b.get_best_result('foo') == 2
    assert not b.is_stable('foo')

    b.update('foo', 1, True)
    assert b.get_best_result('foo') == 2
    assert b.is_stable('foo')

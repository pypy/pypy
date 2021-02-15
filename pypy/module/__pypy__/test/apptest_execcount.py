from __pypy__ import ExecutionCounter


def test_simple():
    prof = ExecutionCounter()
    def h(): pass
    def g(): h()
    prof.enable()
    g()
    prof.disable()
    d = prof.getstats()
    assert d[h.__code__][0] == 1
    assert d[g.__code__][0] == 1
    assert 1 in d[test_simple.__code__]

def test_builtin():
    prof = ExecutionCounter()
    def g(): len([])
    prof.enable()
    g()
    prof.disable()
    d = prof.getstats()
    print(d)

def test_saturating():
    prof = ExecutionCounter()
    def h(): pass
    def g(): h()
    prof.enable_saturating()
    g()
    g()
    g()
    g()
    prof.disable()
    d = prof.getstats()
    assert d[h.__code__][0] == 1
    assert d[g.__code__][0] == 1
    assert 1 in d[test_saturating.__code__]


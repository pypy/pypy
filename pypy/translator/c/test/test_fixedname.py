import autopath
from pypy.translator.c.test.test_genc import compile


def test_time_clock():
    import time
    def does_stuff():
        return time.clock()
    f1 = compile(does_stuff, [])
    t0 = time.clock()
    t1 = f1()
    assert type(t1) is float
    t2 = time.clock()
    assert t0 <= t1 <= t2

import time

from pypy.rlib.rtimer import read_timestamp


def test_timer():
    t1 = read_timestamp()
    start = time.time()
    while time.time() - start < 1.0:
        # busy wait
        pass
    t2 = read_timestamp()
    # We're counting ticks, verify they look correct
    assert t2 - t1 > 1000

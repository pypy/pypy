import py
import math
from pypy.module.math import app_math

def test_factorial_extra():
    for x in range(1000):
        r1 = app_math.factorial(x)
        r2 = math.factorial(x)
        assert r1 == r2
        assert type(r1) == type(r2)

def test_timing():
    py.test.skip("for manual running only")
    x = 59999
    t1 = time.time()
    r1 = app_math.factorial(x)
    t2 = time.time()
    r2 = math.factorial(x)
    t3 = time.time()
    assert r1 == r2
    print t2 - t1
    print t3 - t2

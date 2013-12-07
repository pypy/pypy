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
    import time
    x = 5000
    repeat = 1000
    r1 = app_math.factorial(x)
    r2 = math.factorial(x)
    assert r1 == r2
    t1 = time.time()
    for i in range(repeat):
        app_math.factorial(x)
    t2 = time.time()
    for i in range(repeat):
        math.factorial(x)
    t3 = time.time()
    assert r1 == r2
    print (t2 - t1) / repeat
    print (t3 - t2) / repeat

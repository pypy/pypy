from pypy.translator.stackless.test.test_transform import \
     llinterp_stackless_function, run_stackless_function
from pypy.translator.stackless import code
import os

def test_simple():
    def g1():
        "just to check Void special cases around the code"
    def g2(ignored):
        pass
        g1()
    def f(n):
        g1()
        if n > 0:
            res = f(n-1)
        else:
            res = code.stack_frames_depth()
        g2(g1)
        return res

    def fn(ignored):
        count0 = f(0)
        count10 = f(10)
        return count10 - count0

    res = llinterp_stackless_function(fn, fn, f, g2, g1)
    assert res == 10

    res = run_stackless_function(fn, fn, f, g2, g1)
    assert res.strip() == "10"

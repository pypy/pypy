from pypy.translator.stackless.test.test_transform import \
     llinterp_stackless_function, run_stackless_function
from pypy.rpython import rstack
import py
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
            res = rstack.stack_frames_depth()
        g2(g1)
        return res

    def fn():
        count0 = f(0)
        count10 = f(10)
        return count10 - count0

    res = llinterp_stackless_function(fn)
    assert res == 10

    res = run_stackless_function(fn)
    assert res == 10

def test_with_ptr():
    def f(n):
        if n > 0:
            res = f(n-1)
        else:
            res = rstack.stack_frames_depth(), 1
        return res

    def fn():
        count0, _ = f(0)
        count10, _ = f(10)
        return count10 - count0

    res = llinterp_stackless_function(fn)
    assert res == 10

    res = run_stackless_function(fn)
    assert res == 10

def test_manytimes():
    def f(n):
        if n > 0:
            res = f(n-1)
        else:
            res = rstack.stack_frames_depth(), 1
        return res

    def fn():
        count0, _ = f(0)
        count10, _ = f(100)
        return count10 - count0

    res = llinterp_stackless_function(fn)
    assert res == 100

    res = run_stackless_function(fn)
    assert res == 100

def test_arguments():
    def f(n, d, t):
        if n > 0:
            res = f(n-1, d, t)
        else:
            res = rstack.stack_frames_depth(), d, t
        return res

    def fn():
        count0, d, t = f(0, 5.5, (1, 2))
        count10, d, t = f(10, 5.5, (1, 2))
        return count10 - count0 + int(d)

    res = llinterp_stackless_function(fn)
    assert res == 15

    res = run_stackless_function(fn)
    assert res == 15

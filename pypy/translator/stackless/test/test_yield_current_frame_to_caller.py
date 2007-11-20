from pypy.translator.stackless.test.test_transform import \
     llinterp_stackless_function, run_stackless_function
from pypy.rlib import rstack
import py
import os


def test_simple():
    def f():
        c = g()
        assert c
        return 1
    def g():
        d = rstack.yield_current_frame_to_caller()
        return d

    data = llinterp_stackless_function(f)
    assert data == 1

    res = run_stackless_function(f)
    assert res == 1

def test_switch():
    def f():
        c = g()
        c.switch()
        return 1
    def g():
        d = rstack.yield_current_frame_to_caller()
        return d

    data = llinterp_stackless_function(f)
    assert data == 1

    res = run_stackless_function(f)
    assert res == 1

def test_yield_frame():

    def g(lst):
        lst.append(2)
        frametop_before_5 = rstack.yield_current_frame_to_caller()
        lst.append(4)
        frametop_before_7 = frametop_before_5.switch()
        lst.append(6)
        return frametop_before_7

    def f():
        lst = [1]
        frametop_before_4 = g(lst)
        lst.append(3)
        frametop_before_6 = frametop_before_4.switch()
        lst.append(5)
        frametop_after_return = frametop_before_6.switch()
        lst.append(7)
        assert not frametop_after_return
        n = 0
        for i in lst:
            n = n*10 + i
        return n

    data = llinterp_stackless_function(f)
    assert data == 1234567

    res = run_stackless_function(f)
    assert res == 1234567


def test_frame_none_mix():
    def h(flag):
        if flag:
            c = g()
        else:
            c = None
        return c
    def f():
        return bool(h(False)) * 2 + bool(h(True))
    def g():
        d = rstack.yield_current_frame_to_caller()
        return d

    data = llinterp_stackless_function(f)
    assert data == 1

    res = run_stackless_function(f)
    assert res == 1



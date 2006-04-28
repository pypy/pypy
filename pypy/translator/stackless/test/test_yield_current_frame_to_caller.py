from pypy.translator.stackless.test.test_transform import \
     llinterp_stackless_function, run_stackless_function
from pypy.translator.stackless import code
import py
import os

py.test.skip('in progress')

def test_simple():
    def f(ignored):
        c = g()
        #c.switch()
        return 1
    def g():
        d = code.yield_current_frame_to_caller()
        return d

    data = llinterp_stackless_function(f)
    assert data == 1234567


def test_yield_frame():

    def g(lst):
        lst.append(2)
        frametop_before_5 = code.yield_current_frame_to_caller()
        lst.append(4)
        frametop_before_7 = frametop_before_5.switch()
        lst.append(6)
        return frametop_before_7

    def f(ignored):
        lst = [1]
        frametop_before_4 = g(lst)
        lst.append(3)
        frametop_before_6 = frametop_before_4.switch()
        lst.append(5)
        frametop_after_return = frametop_before_6.switch()
        lst.append(7)
        assert frametop_after_return is None
        n = 0
        for i in lst:
            n = n*10 + i
        return n

    data = llinterp_stackless_function(f)
    assert data == 1234567

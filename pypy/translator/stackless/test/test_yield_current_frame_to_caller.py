from pypy.translator.stackless.test.test_transform import \
     llinterp_stackless_function, run_stackless_function
from pypy.translator.stackless import code
from pypy.rpython import rstack
import py
import os


class TestFromCode:
    yield_current_frame_to_caller = staticmethod(
        code.yield_current_frame_to_caller)
    switch = staticmethod(code.ll_frame_switch)

    def _freeze_(self):
        return True

    def test_simple(self):
        def f(ignored):
            c = g()
            return 1
        def g():
            self.yield_current_frame_to_caller()

        data = llinterp_stackless_function(f)
        assert data == 1

        res = run_stackless_function(f)
        assert res.strip() == "1"

    def test_switch(self):
        def f(ignored):
            c = g()
            self.switch(c)
            return 1
        def g():
            d = self.yield_current_frame_to_caller()
            return d

        data = llinterp_stackless_function(f)
        assert data == 1

        res = run_stackless_function(f)
        assert res.strip() == "1"

    def test_yield_frame(self):

        def g(lst):
            lst.append(2)
            frametop_before_5 = self.yield_current_frame_to_caller()
            lst.append(4)
            frametop_before_7 = self.switch(frametop_before_5)
            lst.append(6)
            return frametop_before_7

        def f(ignored):
            lst = [1]
            frametop_before_4 = g(lst)
            lst.append(3)
            frametop_before_6 = self.switch(frametop_before_4)
            lst.append(5)
            frametop_after_return = self.switch(frametop_before_6)
            lst.append(7)
            assert bool(frametop_after_return)
            n = 0
            for i in lst:
                n = n*10 + i
            return n

        data = llinterp_stackless_function(f)
        assert data == 1234567

        res = run_stackless_function(f)
        assert res.strip() == "1234567"


class TestFromRStack(TestFromCode):
    yield_current_frame_to_caller = staticmethod(
        rstack.yield_current_frame_to_caller)

    def switch(state):
        return state.switch()
    switch = staticmethod(switch)

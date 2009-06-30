from pypy.translator.stackless.test.test_transform import \
     llinterp_stackless_function, run_stackless_function
from pypy.rlib import rstack
import py
import os, sys


def test_simple():
    def g1():
        "just to check Void special cases around the code"
    def g2(ignored):
        pass
        g1()
    def f(n):
        g1()
        if n > 0:
            res = f(n-1) + 0
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
            res, dummy = f(n-1)
            return (res, dummy)
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
            res, dummy = f(n-1)
            return (res, dummy)
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
            res, y, z = f(n-1, d, t)
            return res, y, z
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

def test_stack_capture():
    def fn():
        frame = rstack.stack_capture()
        return int(bool(frame))

    res = llinterp_stackless_function(fn)
    assert res == 1

def test_eliminate_tail_calls():
    # make sure that when unwinding the stack there are no frames saved
    # for tail calls
    def f(n):
        if n > 0:
            res = f(n-1)
        else:
            res = rstack.stack_frames_depth()
        return res
    def fn():
        count0 = f(0)
        count10 = f(10)
        return count10 - count0
    res = llinterp_stackless_function(fn)
    assert res == 0


def test_depth_bug():
    def g(base):
        print rstack.stack_frames_depth()
        return rstack.stack_frames_depth() - base
    def fn():
        base = rstack.stack_frames_depth()
        print base
        base = rstack.stack_frames_depth()
        print base
        return g(base) + 100
    res = llinterp_stackless_function(fn)
    assert res == 101

def test_depth_along_yield_frame():

    def h():
        x = rstack.stack_frames_depth()
        x += 1      # don't remove! otherwise it becomes a tail call
        x -= 1
        return x

    def g(base, lst):
        lst.append(rstack.stack_frames_depth() - base)
        #print lst
        frametop_before_5 = rstack.yield_current_frame_to_caller()
        lst.append(h())
        frametop_before_7 = frametop_before_5.switch()
        lst.append(rstack.stack_frames_depth())
        return frametop_before_7

    def f(base):
        lst = [rstack.stack_frames_depth() - base]
        #print lst
        frametop_before_4 = g(base, lst)
        lst.append(rstack.stack_frames_depth() - base)
        #print lst
        frametop_before_6 = frametop_before_4.switch()
        lst.append(h() - base)
        frametop_after_return = frametop_before_6.switch()
        lst.append(rstack.stack_frames_depth() - base)
        assert not frametop_after_return
        n = 0
        for i in lst:
            n = n*10 + i
        return n

    def loop(base, n):
        if n > 0:
            return loop(base, n-1) + 1
        else:
            return f(base) + 1

    def entrypoint():
        base = rstack.stack_frames_depth()
        return loop(base, 5) - 6

    data = llinterp_stackless_function(entrypoint)
    assert data == 7874837

    res = run_stackless_function(entrypoint)
    assert res == 7874837

def test_get_set_stack_depth_limit():
    def f():
        rstack.set_stack_depth_limit(12321)
        return rstack.get_stack_depth_limit()
    data = llinterp_stackless_function(f, assert_unwind=False)
    assert data == 12321

def test_stack_limit():
    def g():
        return rstack.stack_frames_depth()
    def f():
        rstack.set_stack_depth_limit(1)
        try:
            return g()
        except RuntimeError:
            return -123
    data = llinterp_stackless_function(f)
    assert data == -123

def test_stack_limit_2():
    def g():
        return rstack.stack_frames_depth()
    def f():
        rstack.stack_frames_depth()
        rstack.set_stack_depth_limit(1)
        try:
            return g()
        except RuntimeError:
            return -123
    data = llinterp_stackless_function(f)
    assert data == -123

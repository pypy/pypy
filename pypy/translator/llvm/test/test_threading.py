import sys

import py
py.test.skip("threading is broken")

import thread

from pypy.translator.llvm.test.runtest import *

def test_lock():
    def fn():
        l = thread.allocate_lock()
        ok1 = l.acquire(True)
        ok2 = l.acquire(False)
        l.release()
        ok2_and_a_half = False
        try:
            l.release()
        except thread.error:
            ok2_and_a_half = True
        ok3 = l.acquire(False)
        return ok1 and not ok2 and ok2_and_a_half and ok3
    f = compile_function(fn, [])
    res = f()
    assert res

def test_simple_start_new_thread():
    class Arg:
        pass
    def mythreadedfunction(arg):
        assert arg.value == 42
    def myotherthreadedfunction(arg):
        assert arg.value == 43
    a42 = Arg()
    a42.value = 42
    a43 = Arg()
    a43.value = 43
    def fn(i):
        thread.start_new_thread(mythreadedfunction, (a42,))
        thread.start_new_thread(myotherthreadedfunction, (a43,))
        if i == 1:
            x = mythreadedfunction
            a = a42
        else:
            x = myotherthreadedfunction
            a = a43
        thread.start_new_thread(x, (a,))
        return 42
    f = compile_function(fn, [int])
    res = f(1)
    assert res == 42

def test_start_new_thread():
    class Arg:
        pass
    a = Arg()
    a.x = 5
    def mythreadedfunction(arg):
        arg.x += 37
        arg.myident = thread.get_ident()
        arg.lock.release()
    def fn():
        a.lock = thread.allocate_lock()
        a.lock.acquire(True)
        ident = thread.start_new_thread(mythreadedfunction, (a,))
        assert ident != thread.get_ident()
        a.lock.acquire(True)  # wait for the thread to finish
        assert a.myident == ident
        return a.x
    f = compile_function(fn, [])
    res = f()
    assert res == 42

def test_prebuilt_lock():
    lock0 = thread.allocate_lock()
    lock1 = thread.allocate_lock()
    lock1.acquire()
    def fn(i):
        lock = [lock0, lock1][i]
        ok = lock.acquire(False)
        if ok: lock.release()
        return ok
    f = compile_function(fn, [int])
    res = f(0)
    assert res == True
    res = f(1)
    assert res == False


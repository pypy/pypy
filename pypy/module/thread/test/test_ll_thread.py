
from pypy.module.thread.ll_thread import *
import py

def test_lock():
    l = ll_allocate_lock()
    ok1 = ll_acquire_lock(l, 1)
    ok2 = ll_acquire_lock(l, 0)
    ll_release_lock(l)
    ok3 = ll_acquire_lock(l, 0)
    res = ok1 and not ok2 and ok3
    assert res == 1

def test_thread_error():
    l = ll_allocate_lock()
    py.test.raises(ThreadError, ll_release_lock, l)

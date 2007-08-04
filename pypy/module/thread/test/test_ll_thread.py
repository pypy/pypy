
from pypy.module.thread.ll_thread import *
from pypy.translator.c.test.test_genc import compile
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

def test_thread_init_new():
    """ This test works only after translation
    """
    py.test.skip("does not work")
    import time
    import thread

    class X(BaseBootstrapper):
        def __init__(self):
            self.top = []

        def bootstrap(self):
            self.top.append(1)
    
    def f():
        x = X()
        ll_start_new_thread(X.bootstrap, x)
        time.sleep(.3)
        return len(x.top)

    fn = compile(f, [])
    assert fn() == 1

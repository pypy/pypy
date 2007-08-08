
from pypy.module.thread.ll_thread import *
from pypy.translator.c.test.test_genc import compile
from pypy.rpython.lltypesystem import lltype
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

def test_start_new_thread():
    import time
    class Y:
        _alloc_flavor_ = 'raw'
        
        def __init__(self):
            self.top = []

        def bootstrap(self):
            self.top.append(ll_get_ident())
    
    def f():
        y = Y()
        start_new_thread(Y.bootstrap, y)
        time.sleep(1)
        res = len(y.top)
        lltype.free(y.top, flavor='raw')
        lltype.free(y, flavor='raw')
        return res == ll_get_ident()

    # XXX is this testable on top of llinterp at all?
    fn = compile(f, [])
    # XXX where does additional malloc come from???
    assert fn(expected_extra_mallocs=1) == False
    


from pypy.module.thread.ll_thread import *
from pypy.translator.c.test.test_genc import compile
from pypy.rpython.lltypesystem import lltype
import py

def test_lock():
    l = allocate_lock()
    ok1 = l.acquire(True)
    ok2 = l.acquire(False)
    l.release()
    ok3 = l.acquire(False)
    res = ok1 and not ok2 and ok3
    assert res == 1

def test_thread_error():
    l = allocate_lock()
    try:
        l.release()
    except error:
        pass
    else:
        py.test.fail("Did not raise")

def test_start_new_thread():
    import time
    class Y:
        _alloc_flavor_ = 'raw'
        
        def __init__(self):
            self.top = []

        def bootstrap(self):
            self.top.append(get_ident())

    def f():
        y = Y()
        start_new_thread(Y.bootstrap, (y,))
        time.sleep(.3)
        res = len(y.top)
        lltype.free(y, flavor='raw')
        return 1 == get_ident()

    # for some reason, refcounting does not handle _alloc_flavor_ = 'raw'
    # XXX is this testable on top of llinterp at all?
    fn = compile(f, [], gcpolicy='boehm')
    assert fn() == False

def test_prebuilt_lock():
    py.test.skip("Does not work (prebuilt opaque object)")
    l = allocate_lock()

    def f():
        l.acquire(True)
        l.release()

    fn = compile(f, [], gcpolicy='boehm')
    fn()

    

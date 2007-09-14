
from pypy.module.thread.ll_thread import *
from pypy.translator.c.test.test_genc import compile
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.objectmodel import free_non_gc_object
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

def test_fused():
    l = allocate_lock()
    try:
        l.fused_release_acquire()
    except error:
        pass
    else:
        py.test.fail("Did not raise")
    l.acquire(True)
    l.fused_release_acquire()
    could_acquire_again = l.acquire(False)
    assert not could_acquire_again

def test_start_new_thread():
    import time
    

    class State:
        pass
    state = State()
    
    class Z:
        def __init__(self, value):
            self.value = value
        def __del__(self):
            state.freed_counter += 1
            
    class Y:
        _alloc_flavor_ = 'raw'

        def bootstrap(self):
            state.my_thread_ident = get_ident()
            assert state.my_thread_ident == get_ident()
            state.seen_value = self.z.value
            self.z = None
            free_non_gc_object(self)
            state.done = 1

    def g(i):
        y = Y()
        y.z = Z(i)
        start_new_thread(Y.bootstrap, (y,))
    g.dont_inline = True

    def f():
        main_ident = get_ident()
        assert main_ident == get_ident()
        state.freed_counter = 0
        for i in range(50):
            state.done = 0
            state.seen_value = 0
            g(i)
            willing_to_wait_more = 1000
            while not state.done:
                willing_to_wait_more -= 1
                if not willing_to_wait_more:
                    raise Exception("thread didn't start?")
                time.sleep(0.01)
            assert state.my_thread_ident != main_ident
            assert state.seen_value == i
        # try to force Boehm to do some freeing
        for i in range(3):
            llop.gc__collect(lltype.Void)
        return state.freed_counter

    fn = compile(f, [], gcpolicy='boehm')
    freed_counter = fn()
    print freed_counter
    assert freed_counter > 0

def test_prebuilt_lock():
    py.test.skip("Does not work (prebuilt opaque object)")
    l = allocate_lock()

    def f():
        l.acquire(True)
        l.release()

    fn = compile(f, [], gcpolicy='boehm')
    fn()

    

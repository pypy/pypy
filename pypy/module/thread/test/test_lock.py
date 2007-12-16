from pypy.module.thread.test.support import GenericTestThread
from pypy.translator.c.test.test_genc import compile


class AppTestLock(GenericTestThread):

    def test_lock(self):
        import thread
        lock = thread.allocate_lock()
        assert type(lock) is thread.LockType
        assert lock.locked() is False
        raises(thread.error, lock.release)
        assert lock.locked() is False
        lock.acquire()
        assert lock.locked() is True
        lock.release()
        assert lock.locked() is False
        raises(thread.error, lock.release)
        assert lock.locked() is False
        feedback = []
        lock.acquire()
        def f():
            self.busywait(0.25)
            feedback.append(42)
            lock.release()
        assert lock.locked() is True
        thread.start_new_thread(f, ())
        lock.acquire()
        assert lock.locked() is True
        assert feedback == [42]


def test_compile_lock():
    from pypy.rlib import rgc
    from pypy.module.thread.ll_thread import allocate_lock
    def g():
        l = allocate_lock()
        ok1 = l.acquire(True)
        ok2 = l.acquire(False)
        l.release()
        ok3 = l.acquire(False)
        res = ok1 and not ok2 and ok3
        return res
    g._dont_inline_ = True
    def f():
        res = g()
        # the lock must have been freed by now - we use refcounting
        return res
    fn = compile(f, [], gcpolicy='ref')
    res = fn()
    assert res


class AppTestLockAgain(GenericTestThread):
    # test it at app-level again to detect strange interactions
    test_lock_again = AppTestLock.test_lock.im_func

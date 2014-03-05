from __future__ import with_statement
import py
import sys, os
from pypy.module.thread.test.support import GenericTestThread
from rpython.translator.c.test.test_genc import compile


class AppTestLock(GenericTestThread):

    def test_lock(self):
        import thread
        lock = thread.allocate_lock()
        assert type(lock) is thread.LockType
        assert lock.locked() is False
        raises(thread.error, lock.release)
        assert lock.locked() is False
        r = lock.acquire()
        assert r is True
        r = lock.acquire(False)
        assert r is False
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

    def test_lock_in_with(self):
        import thread
        lock = thread.allocate_lock()
        feedback = []
        lock.acquire()
        def f():
            self.busywait(0.25)
            feedback.append(42)
            lock.release()
        assert lock.locked() is True
        thread.start_new_thread(f, ())
        with lock:
            assert lock.locked() is True
            assert feedback == [42]
        assert lock.locked() is False

    def test_timeout(self):
        import thread
        lock = thread.allocate_lock()
        assert lock.acquire() is True
        assert lock.acquire(False) is False
        raises(TypeError, lock.acquire, True, timeout=.1)
        lock._py3k_acquire(True, timeout=.01)
        lock._py3k_acquire(True, .01)


def test_compile_lock():
    from rpython.rlib import rgc
    from rpython.rlib.rthread import allocate_lock
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


class AppTestLockSignals(GenericTestThread):
    pytestmark = py.test.mark.skipif("os.name != 'posix'")

    def setup_class(cls):
        cls.w_using_pthread_cond = cls.space.wrap(sys.platform == 'freebsd6')

    def w_acquire_retries_on_intr(self, lock):
        import thread, os, signal, time
        self.sig_recvd = False
        def my_handler(signal, frame):
            self.sig_recvd = True
        old_handler = signal.signal(signal.SIGUSR1, my_handler)
        try:
            def other_thread():
                # Acquire the lock in a non-main thread, so this test works for
                # RLocks.
                lock.acquire()
                # Wait until the main thread is blocked in the lock acquire, and
                # then wake it up with this.
                time.sleep(0.5)
                os.kill(os.getpid(), signal.SIGUSR1)
                # Let the main thread take the interrupt, handle it, and retry
                # the lock acquisition.  Then we'll let it run.
                time.sleep(0.5)
                lock.release()
            thread.start_new_thread(other_thread, ())
            # Wait until we can't acquire it without blocking...
            while lock.acquire(blocking=False):
                lock.release()
                time.sleep(0.01)
            result = lock.acquire()  # Block while we receive a signal.
            assert self.sig_recvd
            assert result
        finally:
            signal.signal(signal.SIGUSR1, old_handler)

    def test_lock_acquire_retries_on_intr(self):
        import thread
        self.acquire_retries_on_intr(thread.allocate_lock())

    def w_alarm_interrupt(self, sig, frame):
        raise KeyboardInterrupt

    def test_lock_acquire_interruption(self):
        if self.using_pthread_cond:
            skip('POSIX condition variables cannot be interrupted')
        import thread, signal, time
        # Mimic receiving a SIGINT (KeyboardInterrupt) with SIGALRM while stuck
        # in a deadlock.
        # XXX this test can fail when the legacy (non-semaphore) implementation
        # of locks is used in thread_pthread.h, see issue #11223.
        oldalrm = signal.signal(signal.SIGALRM, self.alarm_interrupt)
        try:
            lock = thread.allocate_lock()
            lock.acquire()
            signal.alarm(1)
            t1 = time.time()
            # XXX: raises doesn't work here?
            #raises(KeyboardInterrupt, lock.acquire, timeout=5)
            try:
                lock._py3k_acquire(timeout=10)
            except KeyboardInterrupt:
                pass
            else:
                assert False, 'Expected KeyboardInterrupt'
            dt = time.time() - t1
            # Checking that KeyboardInterrupt was raised is not sufficient.
            # We want to assert that lock.acquire() was interrupted because
            # of the signal, not that the signal handler was called immediately
            # after timeout return of lock.acquire() (which can fool assertRaises).
            assert dt < 8.0
        finally:
            signal.signal(signal.SIGALRM, oldalrm)

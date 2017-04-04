from __future__ import with_statement
import py
import sys, os
from pypy.module.thread.test.support import GenericTestThread
from rpython.translator.c.test.test_genc import compile
from platform import machine


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
        if hasattr(lock, '_py3k_acquire'):
            lock._py3k_acquire(True, timeout=.01)
            lock._py3k_acquire(True, .01)
        else:
            assert self.runappdirect, "missing lock._py3k_acquire()"

    def test_py3k_acquire_timeout_overflow(self):
        import thread
        lock = thread.allocate_lock()
        if not hasattr(lock, '_py3k_acquire'):
            skip("missing lock._py3k_acquire()")
        maxint = 2**63 - 1
        boundary = int(maxint * 1e-6)
        for i in [-100000, -10000, -1000, -100, -10, -1, 0,
                  1, 10, 100, 1000, 10000, 100000]:
            timeout = (maxint + i) * 1e-6
            try:
                lock._py3k_acquire(True, timeout=timeout)
            except OverflowError:
                got_ovf = True
            else:
                got_ovf = False
                lock.release()
            assert (i, got_ovf) == (i, int(timeout * 1e6) > maxint)

    @py.test.mark.xfail(machine()=='s390x', reason='may fail under heavy load')
    def test_ping_pong(self):
        # The purpose of this test is that doing a large number of ping-pongs
        # between two threads, using locks, should complete in a reasonable
        # time on a translated pypy with -A.  If the GIL logic causes too
        # much sleeping, then it will fail.
        import thread, time
        COUNT = 100000 if self.runappdirect else 50
        lock1 = thread.allocate_lock()
        lock2 = thread.allocate_lock()
        def fn():
            for i in range(COUNT):
                lock1.acquire()
                lock2.release()
        lock2.acquire()
        print "STARTING"
        start = time.time()
        thread.start_new_thread(fn, ())
        for i in range(COUNT):
            lock2.acquire()
            lock1.release()
        stop = time.time()
        assert stop - start < 30.0    # ~0.6 sec on pypy-c-jit


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

    def w_acquire_retries_on_intr(self, lock):
        import thread, os, signal, time
        self.sig_recvd = False
        def my_handler(signal, frame):
            self.sig_recvd = True
        old_handler = signal.signal(signal.SIGUSR1, my_handler)
        try:
            ready = thread.allocate_lock()
            ready.acquire()
            def other_thread():
                # Acquire the lock in a non-main thread, so this test works for
                # RLocks.
                lock.acquire()
                # Notify the main thread that we're ready
                ready.release()
                # Wait for 5 seconds here
                for n in range(50):
                    time.sleep(0.1)
                # Send the signal
                os.kill(os.getpid(), signal.SIGUSR1)
                # Let the main thread take the interrupt, handle it, and retry
                # the lock acquisition.  Then we'll let it run.
                for n in range(50):
                    time.sleep(0.1)
                lock.release()
            thread.start_new_thread(other_thread, ())
            ready.acquire()
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

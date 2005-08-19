from pypy.module.thread.test.support import GenericTestThread


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

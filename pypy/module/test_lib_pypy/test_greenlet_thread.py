import py
try:
    import thread, time
    from lib_pypy import greenlet
    #import greenlet
except ImportError as e:
    py.test.skip(e)


class TestThread:

    def test_cannot_switch_to_main_of_different_thread(self):
        mains = []
        mains.append(greenlet.getcurrent())
        lock = thread.allocate_lock()
        lock.acquire()
        got_exception = []
        #
        def run_thread():
            main = greenlet.getcurrent()
            assert main not in mains
            mains.append(main)
            try:
                mains[0].switch()
            except Exception as e:
                got_exception.append(e)
            lock.release()
        #
        thread.start_new_thread(run_thread, ())
        lock.acquire()
        assert isinstance(got_exception[0], greenlet.error)

    def test_nonstarted_greenlet_is_still_attached_to_thread(self):
        subs = []
        lock = thread.allocate_lock()
        lock.acquire()
        got_exception = []
        #
        def run_thread():
            g = greenlet.greenlet(lambda *args: None)
            subs.append(g)
            lock.release()
            time.sleep(1)
        #
        thread.start_new_thread(run_thread, ())
        lock.acquire()
        [g] = subs
        py.test.raises(greenlet.error, g.switch)

    def test_noninited_greenlet_is_still_attached_to_thread(self):
        subs = []
        lock = thread.allocate_lock()
        lock.acquire()
        got_exception = []
        #
        def run_thread():
            g = greenlet.greenlet.__new__(greenlet.greenlet)
            subs.append(g)
            lock.release()
            time.sleep(1)
        #
        thread.start_new_thread(run_thread, ())
        lock.acquire()
        [g] = subs
        py.test.raises(greenlet.error, g.switch)

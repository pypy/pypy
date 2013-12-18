from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC


class TestThread(BaseTestPyPyC):
    def test_simple(self):
        def main(n):
            import thread
            def f():
                i = 0
                while i < n:
                    i += 1
                done.release()

            done = thread.allocate_lock()
            done.acquire()
            thread.start_new_thread(f, ())
            done.acquire()
            return 0
        log = self.run(main, [500])
        assert round(log.result, 6) == round(main(500), 6)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i2 = int_lt(i0, i1)
            guard_true(i2, descr=...)
            i3 = int_add(i0, 1)
            --THREAD-TICK--
            jump(..., descr=...)
        """)

    def test_tls(self):
        def main(n):
            import thread
            local = thread._local()
            local.x = 1
            i = 0
            while i < n:
                i += local.x
            return 0
        log = self.run(main, [500])
        assert round(log.result, 6) == round(main(500), 6)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i53 = int_lt(i48, i27)
            guard_true(i53, descr=...)
            i54 = int_add_ovf(i48, i47)
            guard_no_overflow(descr=...)
            --TICK--
            i58 = arraylen_gc(p43, descr=...)
            jump(..., descr=...)
        """)

    def test_lock_acquire_release(self):
        def main(n):
            import threading
            lock = threading.Lock()
            while n > 0:
                with lock:
                    n -= 1
        log = self.run(main, [500])
        assert log.result == main(500)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
        i56 = int_gt(i44, 0)
        guard_true(i56, descr=...)
        p57 = force_token()
        setfield_gc(p0, p57, descr=<FieldP pypy.interpreter.pyframe.PyFrame.vable_token 8>)
        i58 = call_release_gil(..., i37, 1, descr=<Calli 4 ii EF=6>)
        guard_not_forced(descr=...)
        guard_no_exception(descr=...)
        i59 = int_is_true(i58)
        guard_true(i59, descr=...)
        i60 = int_sub(i44, 1)
        guard_not_invalidated(descr=...)
        p62 = force_token()
        setfield_gc(p0, p62, descr=<FieldP pypy.interpreter.pyframe.PyFrame.vable_token 8>)
        i63 = call_release_gil(..., i37, 0, descr=<Calli 4 ii EF=6>)
        guard_not_forced(descr=...)
        guard_no_exception(descr=...)
        i64 = int_is_true(i63)
        guard_false(i64, descr=...)
        p65 = force_token()
        setfield_gc(p0, p65, descr=<FieldP pypy.interpreter.pyframe.PyFrame.vable_token 8>)
        call_release_gil(..., i37, descr=<Callv 0 i EF=6>)
        guard_not_forced(descr=...)
        guard_no_exception(descr=...)
        guard_not_invalidated(descr=...)
        --TICK--
        jump(..., descr=...)
        """)

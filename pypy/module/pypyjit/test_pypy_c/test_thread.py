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
        i63 = int_gt(i48, 0)
        guard_true(i63, descr=...)
        p64 = force_token()
        setfield_gc(p0, p64, descr=<FieldP pypy.interpreter.pyframe.PyFrame.vable_token .*>)
        i65 = call_release_gil(..., i39, 1, descr=<Calli 4 ii EF=6>)
        guard_not_forced(descr=...)
        guard_no_exception(descr=...)
        i66 = int_is_true(i65)
        guard_true(i66, descr=...)
        p67 = getfield_gc(p1, descr=<FieldP pypy.interpreter.executioncontext.ExecutionContext.inst_w_tracefunc .*>)
        guard_value(p67, ConstPtr(ptr46), descr=...)
        i68 = int_sub(i48, 1)
        guard_not_invalidated(descr=...)
        p69 = force_token()
        setfield_gc(p0, p69, descr=<FieldP pypy.interpreter.pyframe.PyFrame.vable_token .*>)
        i70 = call_release_gil(..., i39, 0, descr=<Calli 4 ii EF=6>)
        guard_not_forced(descr=...)
        guard_no_exception(descr=...)
        i71 = int_is_true(i70)
        guard_false(i71, descr=...)
        p72 = force_token()
        setfield_gc(p0, p72, descr=<FieldP pypy.interpreter.pyframe.PyFrame.vable_token .*>)
        call_release_gil(..., i39, descr=<Callv 0 i EF=6>)
        guard_not_forced(descr=...)
        guard_no_exception(descr=...)
        p73 = getfield_gc(p1, descr=<FieldP pypy.interpreter.executioncontext.ExecutionContext.inst_w_tracefunc .*>)
        guard_value(p73, ConstPtr(ptr58), descr=...)
        guard_not_invalidated(descr=...)
        --TICK--
        jump(..., descr=...)
        """)

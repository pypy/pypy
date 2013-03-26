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

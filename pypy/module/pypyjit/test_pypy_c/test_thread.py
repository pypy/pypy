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
            i60 = int_lt(i55, i27)
            guard_true(i60, descr=...)
            i61 = call(ConstClass(ll_dict_lookup_trampoline__v1134___simple_call__function_), p33, p32, i35, descr=...)
            guard_no_exception(descr=...)
            i62 = int_and(i61, -2147483648)
            i63 = int_is_true(i62)
            guard_false(i63, descr=...)
            p64 = getinteriorfield_gc(p41, i61, descr=...)
            guard_nonnull_class(p64, ConstClass(W_DictMultiObject), descr=...)
            p65 = getfield_gc(p64, descr=...)
            guard_class(p65, 176132160, descr=...)
            p66 = getfield_gc(p64, descr=...)
            guard_class(p66, 175975744, descr=...)
            p67 = getfield_gc(p66, descr=...)
            guard_value(p67, ConstPtr(ptr49), descr=...)
            p68 = getfield_gc(p66, descr=...)
            p69 = getarrayitem_gc(p68, 0, descr=...)
            guard_nonnull_class(p69, ConstClass(W_IntObject), descr=...)
            i70 = getfield_gc_pure(p69, descr=...)
            i71 = int_add_ovf(i55, i70)
            guard_no_overflow(descr=...)
            --TICK--
            jump(p0, p1, p3, p5, p10, p12, p14, i71, i27, p33, p32, i35, p41, descr=...)
        """)

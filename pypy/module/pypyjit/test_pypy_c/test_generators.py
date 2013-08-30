from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC


class TestGenerators(BaseTestPyPyC):
    def test_simple_generator(self):
        def main(n):
            def f():
                for i in range(10000):
                    i -= 1
                    i -= 42    # ID: subtract
                    yield i

            def g():
                for i in f():  # ID: generator
                    pass

            g()

        log = self.run(main, [500])
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id("generator", """
            cond_call(..., descr=...)
            i16 = force_token()
            p45 = new_with_vtable(ConstClass(W_IntObject))
            setfield_gc(p45, i29, descr=<FieldS .*>)
            setarrayitem_gc(p8, 0, p45, descr=<ArrayP .>)
            i47 = arraylen_gc(p8, descr=<ArrayP .>) # Should be removed by backend
            jump(..., descr=...)
            """)
        assert loop.match_by_id("subtract", """
            setfield_gc(p7, 35, descr=<.*last_instr .*>)     # XXX bad, kill me
            i2 = int_sub_ovf(i1, 42)
            guard_no_overflow(descr=...)
            """)

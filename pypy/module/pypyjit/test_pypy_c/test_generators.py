from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC


class TestGenerators(BaseTestPyPyC):
    def test_simple_generator(self):
        def main(n):
            def f():
                for i in range(10000):
                    yield i

            def g():
                for i in f():  # ID: generator
                    pass

            g()

        log = self.run(main, [500])
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id("generator", """
            i16 = force_token()
            p45 = new_with_vtable(ConstClass(W_IntObject))
            setfield_gc(p45, i29, descr=<SignedFieldDescr .*>)
            i47 = arraylen_gc(p8, descr=<GcPtrArrayDescr>) # Should be removed by backend
            setarrayitem_gc(p8, 0, p45, descr=<GcPtrArrayDescr>)
            jump(..., descr=...)
            """)

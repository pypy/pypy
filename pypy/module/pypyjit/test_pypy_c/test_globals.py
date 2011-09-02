from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC


class TestGlobals(BaseTestPyPyC):
    def test_load_builtin(self):
        def main(n):
            import pypyjit

            i = 0
            while i < n:
                l = len # ID: loadglobal
                i += pypyjit.residual_call(l, "a")
            return i
        #
        log = self.run(main, [500])
        assert log.result == 500
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id("loadglobal", """
            p10 = getfield_gc(p0, descr=<GcPtrFieldDescr .*Frame.inst_w_globals .*>)
            guard_value(p10, ConstPtr(ptr11), descr=...)
            p12 = getfield_gc(p10, descr=<GcPtrFieldDescr .*W_DictMultiObject.inst_strategy .*>)
            guard_value(p12, ConstPtr(ptr13), descr=...)
            guard_not_invalidated(descr=...)
            p19 = getfield_gc(ConstPtr(p17), descr=<GcPtrFieldDescr .*W_DictMultiObject.inst_strategy .*>)
            guard_value(p19, ConstPtr(ptr20), descr=...)
            p22 = getfield_gc(ConstPtr(ptr21), descr=<GcPtrFieldDescr .*ModuleCell.inst_w_value .*>)
            guard_nonnull(p22, descr=...)
        """)

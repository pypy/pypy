from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC


class TestThread(BaseTestPyPyC):
    def test_make_ref_with_callback(self):
        log = self.run("""
        import weakref

        class Dummy(object):
            pass

        def noop(obj):
            pass

        def main(n):
            obj = Dummy()
            for i in xrange(n):
                weakref.ref(obj, noop)
        """, [500])
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
        i58 = getfield_gc(p18, descr=<FieldS pypy.module.__builtin__.functional.W_XRangeIterator.inst_current .>)
        i59 = getfield_gc(p18, descr=<FieldS pypy.module.__builtin__.functional.W_XRangeStepOneIterator.inst_stop \d+>)
        i60 = int_lt(i58, i59)
        guard_true(i60, descr=...)
        i61 = int_add(i58, 1)
        p62 = getfield_gc(ConstPtr(ptr37), descr=<FieldP pypy.objspace.std.dictmultiobject.W_DictMultiObject.inst_strategy \d+>)
        setfield_gc(p18, i61, descr=<FieldS pypy.module.__builtin__.functional.W_XRangeIterator.inst_current 8>)
        guard_value(p62, ConstPtr(ptr39), descr=...)
        guard_not_invalidated(descr=...)
        p64 = getfield_gc(ConstPtr(ptr40), descr=<FieldP pypy.objspace.std.dictmultiobject.W_DictMultiObject.inst_strategy \d+>)
        guard_value(p64, ConstPtr(ptr42), descr=...)
        p65 = getfield_gc(p14, descr=<FieldP pypy.objspace.std.mapdict.W_ObjectObjectSize5.inst_map \d+>)
        guard_value(p65, ConstPtr(ptr45), descr=...)
        p66 = getfield_gc(p14, descr=<FieldP pypy.objspace.std.mapdict.W_ObjectObjectSize5.inst__value0 \d+>)
        guard_nonnull_class(p66, ..., descr=...)
        p67 = force_token()
        setfield_gc(p0, p67, descr=<FieldP pypy.interpreter.pyframe.PyFrame.vable_token \d+>)
        p68 = call_may_force(ConstClass(WeakrefLifelineWithCallbacks.make_weakref_with_callback), p66, ConstPtr(ptr50), p14, ConstPtr(ptr51), descr=<Callr \d rrrr EF=6>)
        guard_not_forced(descr=...)
        guard_no_exception(descr=...)
        guard_nonnull_class(p68, ..., descr=...)
        guard_not_invalidated(descr=...)
        --TICK--
        jump(..., descr=...)
        """)

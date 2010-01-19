import py
from pypy.rpython.lltypesystem import lltype, llmemory, lloperation
from pypy.rlib.jit import JitDriver, dont_look_inside, vref_None
from pypy.rlib.jit import virtual_ref, virtual_ref_finish
from pypy.rlib.objectmodel import compute_unique_id
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.virtualref import VirtualRefInfo

debug_print = lloperation.llop.debug_print


class VRefTests:

    def finish_metainterp_for_interp_operations(self, metainterp):
        self.vrefinfo = VirtualRefInfo(metainterp.staticdata.state)
        metainterp.staticdata.virtualref_info = self.vrefinfo

    def test_make_vref_simple(self):
        class X:
            pass
        class ExCtx:
            pass
        exctx = ExCtx()
        #
        def f():
            x = X()
            exctx.topframeref = virtual_ref(x)
            exctx.topframeref = vref_None
            virtual_ref_finish(x)
            return 1
        #
        self.interp_operations(f, [])
        self.check_operations_history(new_with_vtable=1,     # X()
                                      virtual_ref=1,
                                      virtual_ref_finish=1)

    def test_make_vref_guard(self):
        if not isinstance(self, TestLLtype):
            py.test.skip("purely frontend test")
        #
        class X:
            def __init__(self, n):
                self.n = n
        class ExCtx:
            pass
        exctx = ExCtx()
        #
        @dont_look_inside
        def external(n):
            if n > 100:
                return exctx.topframeref().n
            return n
        def enter(n):
            x = X(n + 10)
            exctx._frame = x
            exctx.topframeref = virtual_ref(x)
        def leave():
            exctx.topframeref = vref_None
            virtual_ref_finish(exctx._frame)
        def f(n):
            enter(n)
            n = external(n)
            # ^^^ the point is that X() and the vref should be kept alive here
            leave()
            return n
        #
        res = self.interp_operations(f, [5])
        assert res == 5
        self.check_operations_history(virtual_ref=1, guard_not_forced=1)
        #
        ops = self.metainterp.staticdata.stats.loops[0].operations
        [guard_op] = [op for op in ops
                         if op.opnum == rop.GUARD_NOT_FORCED]
        bxs1 = [box for box in guard_op.fail_args
                  if str(box._getrepr_()).endswith('.X')]
        assert len(bxs1) == 1
        bxs2 = [box for box in guard_op.fail_args
                  if str(box._getrepr_()).endswith('JitVirtualRef')]
        assert len(bxs2) == 1
        JIT_VIRTUAL_REF = self.vrefinfo.JIT_VIRTUAL_REF
        bxs2[0].getref(lltype.Ptr(JIT_VIRTUAL_REF)).virtual_token = 1234567
        #
        self.metainterp.rebuild_state_after_failure(guard_op.descr,
                                                    guard_op.fail_args[:])
        assert len(self.metainterp.framestack) == 1
        assert len(self.metainterp.virtualref_boxes) == 2
        assert self.metainterp.virtualref_boxes[0].value == bxs1[0].value
        assert self.metainterp.virtualref_boxes[1].value == bxs2[0].value

    def test_make_vref_escape_after_finish(self):
        jitdriver = JitDriver(greens = [], reds = ['n'])
        #
        class X:
            pass
        class ExCtx:
            pass
        exctx = ExCtx()
        #
        @dont_look_inside
        def g(vref):
            debug_print(lltype.Void, '-+-+-+-+- external read:', vref().n)
        #
        def f(n):
            while n > 0:
                jitdriver.can_enter_jit(n=n)
                jitdriver.jit_merge_point(n=n)
                x = X()
                x.n = n
                exctx.topframeref = vref = virtual_ref(x)
                # here, 'x' should be virtual
                exctx.topframeref = vref_None
                virtual_ref_finish(x)
                # 'x' and 'vref' can randomly escape after the call to
                # finish().
                g(vref)
                n -= 1
            return 1
        #
        self.meta_interp(f, [10])
        self.check_loops(new_with_vtable=2)   # the vref and the X
        self.check_aborted_count(0)

    def test_simple_all_removed(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        #
        A = lltype.GcArray(lltype.Signed)
        class XY:
            pass
        class ExCtx:
            pass
        exctx = ExCtx()
        #
        @dont_look_inside
        def externalfn(n):
            return 1
        #
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                xy = XY()
                xy.next1 = lltype.malloc(A, 0)
                xy.next2 = lltype.malloc(A, 0)
                xy.next3 = lltype.malloc(A, 0)
                exctx.topframeref = virtual_ref(xy)
                n -= externalfn(n)
                exctx.topframeref = vref_None
                xy.next1 = lltype.nullptr(A)
                xy.next2 = lltype.nullptr(A)
                xy.next3 = lltype.nullptr(A)
                virtual_ref_finish(xy)
        #
        self.meta_interp(f, [15])
        self.check_loops(new_with_vtable=0,     # all virtualized
                         new_array=0)
        self.check_aborted_count(0)

    def test_simple_no_access(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        #
        A = lltype.GcArray(lltype.Signed)
        class XY:
            pass
        class ExCtx:
            pass
        exctx = ExCtx()
        #
        @dont_look_inside
        def externalfn(n):
            if n > 1000:
                return compute_unique_id(exctx.topframeref())
            return 1
        #
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                xy = XY()
                xy.next1 = lltype.malloc(A, 0)
                xy.next2 = lltype.malloc(A, 0)
                xy.next3 = lltype.malloc(A, 0)
                exctx.topframeref = virtual_ref(xy)
                n -= externalfn(n)
                exctx.topframeref = vref_None
                xy.next1 = lltype.nullptr(A)
                xy.next2 = lltype.nullptr(A)
                xy.next3 = lltype.nullptr(A)
                virtual_ref_finish(xy)
        #
        self.meta_interp(f, [15])
        self.check_loops(new_with_vtable=2,     # the vref, and xy so far,
                         new_array=0)           # but not xy.next1/2/3
        self.check_aborted_count(0)

    def test_simple_force_always(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        #
        A = lltype.GcArray(lltype.Signed)
        class XY:
            pass
        class ExCtx:
            pass
        exctx = ExCtx()
        #
        @dont_look_inside
        def externalfn(n):
            m = exctx.topframeref().n
            assert m == n
            return 1
        #
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                xy = XY()
                xy.next1 = lltype.malloc(A, 0)
                xy.next2 = lltype.malloc(A, 0)
                xy.next3 = lltype.malloc(A, 0)
                xy.n = n
                exctx.topframeref = virtual_ref(xy)
                n -= externalfn(n)
                xy.next1 = lltype.nullptr(A)
                xy.next2 = lltype.nullptr(A)
                xy.next3 = lltype.nullptr(A)
                virtual_ref_finish(xy)
                exctx.topframeref = vref_None
        #
        self.meta_interp(f, [15])
        self.check_loops(new_with_vtable=2,   # XY(), the vref
                         new_array=3)         # next1/2/3
        self.check_aborted_count(0)

    def test_simple_force_sometimes(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        #
        A = lltype.GcArray(lltype.Signed)
        class XY:
            pass
        class ExCtx:
            pass
        exctx = ExCtx()
        #
        @dont_look_inside
        def externalfn(n):
            if n == 13:
                exctx.m = exctx.topframeref().n
            return 1
        #
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                xy = XY()
                xy.next1 = lltype.malloc(A, 0)
                xy.next2 = lltype.malloc(A, 0)
                xy.next3 = lltype.malloc(A, 0)
                xy.n = n
                exctx.topframeref = virtual_ref(xy)
                n -= externalfn(n)
                xy.next1 = lltype.nullptr(A)
                xy.next2 = lltype.nullptr(A)
                xy.next3 = lltype.nullptr(A)
                virtual_ref_finish(xy)
                exctx.topframeref = vref_None
            return exctx.m
        #
        res = self.meta_interp(f, [30])
        assert res == 13
        self.check_loops(new_with_vtable=2,   # the vref, XY() at the end
                         new_array=0)         # but not next1/2/3
        self.check_loop_count(1)
        self.check_aborted_count(0)

    def test_blackhole_forces(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        #
        A = lltype.GcArray(lltype.Signed)
        class XY:
            pass
        class ExCtx:
            pass
        exctx = ExCtx()
        #
        @dont_look_inside
        def externalfn(n):
            exctx.m = exctx.topframeref().n
            return 1
        #
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                xy = XY()
                xy.next1 = lltype.malloc(A, 0)
                xy.next2 = lltype.malloc(A, 0)
                xy.next3 = lltype.malloc(A, 0)
                xy.n = n
                exctx.topframeref = virtual_ref(xy)
                if n == 13:
                    externalfn(n)
                n -= 1
                exctx.topframeref = vref_None
                xy.next1 = lltype.nullptr(A)
                xy.next2 = lltype.nullptr(A)
                xy.next3 = lltype.nullptr(A)
                virtual_ref_finish(xy)
            return exctx.m
        #
        res = self.meta_interp(f, [30])
        assert res == 13
        self.check_loops(new_with_vtable=0, # all virtualized in the n!=13 loop
                         new_array=0)
        self.check_loop_count(1)
        self.check_aborted_count(0)

    def test_bridge_forces(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        #
        A = lltype.GcArray(lltype.Signed)
        class XY:
            pass
        class ExCtx:
            pass
        exctx = ExCtx()
        #
        @dont_look_inside
        def externalfn(n):
            exctx.m = exctx.topframeref().n
            return 1
        #
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                xy = XY()
                xy.next1 = lltype.malloc(A, 0)
                xy.next2 = lltype.malloc(A, 0)
                xy.next3 = lltype.malloc(A, 0)
                xy.next4 = lltype.malloc(A, 0)
                xy.next5 = lltype.malloc(A, 0)
                xy.n = n
                exctx.topframeref = virtual_ref(xy)
                if n % 6 == 0:
                    xy.next1 = lltype.nullptr(A)
                    xy.next2 = lltype.nullptr(A)
                    xy.next3 = lltype.nullptr(A)
                    externalfn(n)
                n -= 1
                exctx.topframeref = vref_None
                xy.next1 = lltype.nullptr(A)
                xy.next2 = lltype.nullptr(A)
                xy.next3 = lltype.nullptr(A)
                xy.next4 = lltype.nullptr(A)
                xy.next5 = lltype.nullptr(A)
                virtual_ref_finish(xy)
            return exctx.m
        #
        res = self.meta_interp(f, [72])
        assert res == 6
        self.check_loop_count(2)     # the loop and the bridge
        self.check_loops(new_with_vtable=2,  # loop: nothing; bridge: vref, xy
                         new_array=2)        # bridge: next4, next5
        self.check_aborted_count(0)

    def test_access_vref_later(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        #
        class XY:
            pass
        class ExCtx:
            pass
        exctx = ExCtx()
        #
        @dont_look_inside
        def g():
            return exctx.later().n
        #
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                xy = XY()
                xy.n = n
                exctx.topframeref = virtual_ref(xy)
                exctx.later = exctx.topframeref
                n -= 1
                exctx.topframeref = vref_None
                virtual_ref_finish(xy)
            return g()
        #
        res = self.meta_interp(f, [15])
        assert res == 1
        self.check_aborted_count(0)

    def test_jit_force_virtual_seen(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        #
        A = lltype.GcArray(lltype.Signed)
        class XY:
            pass
        class ExCtx:
            pass
        exctx = ExCtx()
        #
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                xy = XY()
                xy.n = n
                exctx.topframeref = virtual_ref(xy)
                xy.next1 = lltype.malloc(A, 0)
                n = exctx.topframeref().n - 1
                xy.next1 = lltype.nullptr(A)
                exctx.topframeref = vref_None
                virtual_ref_finish(xy)
            return 1
        #
        res = self.meta_interp(f, [15])
        assert res == 1
        self.check_loops(new_with_vtable=2,     # vref, xy
                         new_array=1)           # next1
        self.check_aborted_count(0)

    def test_recursive_call_1(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'frame', 'rec'])
        #
        class XY:
            pass
        class ExCtx:
            pass
        exctx = ExCtx()
        #
        def f(frame, n, reclevel):
            while n > 0:
                myjitdriver.can_enter_jit(n=n, frame=frame, rec=reclevel)
                myjitdriver.jit_merge_point(n=n, frame=frame, rec=reclevel)
                if reclevel == 0:
                    return n
                xy = XY()
                exctx.topframeref = virtual_ref(xy)
                m = f(xy, n, reclevel-1)
                assert m == n
                n -= 1
                exctx.topframeref = vref_None
                virtual_ref_finish(xy)
            return 2
        def main(n, reclevel):
            return f(XY(), n, reclevel)
        #
        res = self.meta_interp(main, [15, 1])
        assert res == main(15, 1)
        self.check_aborted_count(0)

    def test_recursive_call_2(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'frame', 'rec'])
        #
        class XY:
            n = 0
        class ExCtx:
            pass
        exctx = ExCtx()
        #
        def f(frame, n, reclevel):
            while n > 0:
                myjitdriver.can_enter_jit(n=n, frame=frame, rec=reclevel)
                myjitdriver.jit_merge_point(n=n, frame=frame, rec=reclevel)
                frame.n += 1
                xy = XY()
                xy.n = n
                exctx.topframeref = virtual_ref(xy)
                if reclevel > 0:
                    m = f(xy, frame.n, reclevel-1)
                    assert xy.n == m
                    n -= 1
                else:
                    n -= 2
                exctx.topframeref = vref_None
                virtual_ref_finish(xy)
            return frame.n
        def main(n, reclevel):
            return f(XY(), n, reclevel)
        #
        res = self.meta_interp(main, [10, 2])
        assert res == main(10, 2)
        self.check_aborted_count(0)


class TestLLtype(VRefTests, LLJitMixin):
    pass

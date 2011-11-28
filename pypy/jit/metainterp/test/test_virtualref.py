import py
from pypy.rpython.lltypesystem import lltype, llmemory, lloperation
from pypy.rpython.llinterp import LLException
from pypy.rlib.jit import JitDriver, dont_look_inside, vref_None
from pypy.rlib.jit import virtual_ref, virtual_ref_finish, InvalidVirtualRef
from pypy.rlib.jit import non_virtual_ref
from pypy.rlib.objectmodel import compute_unique_id
from pypy.jit.metainterp.test.support import LLJitMixin, OOJitMixin, _get_jitcodes
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.virtualref import VirtualRefInfo

debug_print = lloperation.llop.debug_print


class VRefTests:

    def finish_setup_for_interp_operations(self):
        self.vrefinfo = VirtualRefInfo(self.warmrunnerstate)
        self.cw.setup_vrefinfo(self.vrefinfo)

    def test_rewrite_graphs(self):
        class X:
            pass
        def fn():
            x = X()
            vref = virtual_ref(x)
            x1 = vref()                  # jit_force_virtual
            virtual_ref_finish(vref, x)
        #
        _get_jitcodes(self, self.CPUClass, fn, [], self.type_system)
        graph = self.all_graphs[0]
        assert graph.name == 'fn'
        self.vrefinfo.replace_force_virtual_with_call([graph])
        #
        def check_call(op, fname):
            assert op.opname == 'direct_call'
            assert op.args[0].value._obj._name == fname
        #
        ops = [op for block, op in graph.iterblockops()]
        check_call(ops[-3], 'virtual_ref')
        check_call(ops[-2], 'force_virtual_if_necessary')
        check_call(ops[-1], 'virtual_ref_finish')

    def test_make_vref_simple(self):
        class X:
            pass
        class ExCtx:
            pass
        exctx = ExCtx()
        #
        def f():
            x = X()
            exctx.topframeref = vref = virtual_ref(x)
            exctx.topframeref = vref_None
            virtual_ref_finish(vref, x)
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
        class FooBarError(Exception):
            pass
        class X:
            def __init__(self, n):
                self.n = n
        class ExCtx:
            _frame = None
        exctx = ExCtx()
        #
        @dont_look_inside
        def external(n):
            if exctx._frame is None:
                raise FooBarError
            if n > 100:
                return exctx.topframeref().n
            return n
        def enter(n):
            x = X(n + 10)
            exctx._frame = x
            exctx.topframeref = virtual_ref(x)
        def leave():
            vref = exctx.topframeref
            exctx.topframeref = vref_None
            virtual_ref_finish(vref, exctx._frame)
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
                         if op.getopnum() == rop.GUARD_NOT_FORCED]
        bxs1 = [box for box in guard_op.getfailargs()
                  if str(box._getrepr_()).endswith('.X')]
        assert len(bxs1) == 1
        bxs2 = [box for box in guard_op.getfailargs()
                  if str(box._getrepr_()).endswith('JitVirtualRef')]
        assert len(bxs2) == 1
        JIT_VIRTUAL_REF = self.vrefinfo.JIT_VIRTUAL_REF
        bxs2[0].getref(lltype.Ptr(JIT_VIRTUAL_REF)).virtual_token = 1234567
        #
        # try reloading from blackhole.py's point of view
        from pypy.jit.metainterp.resume import ResumeDataDirectReader
        cpu = self.metainterp.cpu
        cpu.get_latest_value_count = lambda : len(guard_op.getfailargs())
        cpu.get_latest_value_int = lambda i:guard_op.getfailargs()[i].getint()
        cpu.get_latest_value_ref = lambda i:guard_op.getfailargs()[i].getref_base()
        cpu.clear_latest_values = lambda count: None
        class FakeMetaInterpSd:
            callinfocollection = None
        FakeMetaInterpSd.cpu = cpu
        resumereader = ResumeDataDirectReader(FakeMetaInterpSd(),
                                              guard_op.getdescr())
        vrefinfo = self.metainterp.staticdata.virtualref_info
        lst = []
        vrefinfo.continue_tracing = lambda vref, virtual: \
                                        lst.append((vref, virtual))
        resumereader.consume_vref_and_vable(vrefinfo, None, None)
        del vrefinfo.continue_tracing
        assert len(lst) == 1
        lltype.cast_opaque_ptr(lltype.Ptr(JIT_VIRTUAL_REF),
                               lst[0][0])  # assert correct type
        #
        # try reloading from pyjitpl's point of view
        self.metainterp.rebuild_state_after_failure(guard_op.getdescr())
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
            # we cannot do anything with the vref after the call to finish()
            pass
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
                virtual_ref_finish(vref, x)
                # 'x' and 'vref' can randomly escape after the call to
                # finish().
                g(vref)
                n -= 1
            return 1
        #
        self.meta_interp(f, [10])
        self.check_resops(new_with_vtable=2) # the vref
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
                exctx.topframeref = vref = virtual_ref(xy)
                n -= externalfn(n)
                exctx.topframeref = vref_None
                xy.next1 = lltype.nullptr(A)
                xy.next2 = lltype.nullptr(A)
                xy.next3 = lltype.nullptr(A)
                virtual_ref_finish(vref, xy)
        #
        self.meta_interp(f, [15])
        self.check_resops(new_with_vtable=0, new_array=0)
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
                exctx.topframeref = vref = virtual_ref(xy)
                n -= externalfn(n)
                exctx.topframeref = vref_None
                xy.next1 = lltype.nullptr(A)
                xy.next2 = lltype.nullptr(A)
                xy.next3 = lltype.nullptr(A)
                virtual_ref_finish(vref, xy)
        #
        self.meta_interp(f, [15])
        self.check_resops(new_with_vtable=2,     # the vref: xy doesn't need to be forced
                         new_array=0)           # and neither xy.next1/2/3
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
                exctx.topframeref = vref = virtual_ref(xy)
                n -= externalfn(n)
                xy.next1 = lltype.nullptr(A)
                xy.next2 = lltype.nullptr(A)
                xy.next3 = lltype.nullptr(A)
                virtual_ref_finish(vref, xy)
                exctx.topframeref = vref_None
        #
        self.meta_interp(f, [15])
        self.check_resops(new_with_vtable=4,   # XY(), the vref
                          new_array=6)         # next1/2/3
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
                exctx.topframeref = vref = virtual_ref(xy)
                n -= externalfn(n)
                xy.next1 = lltype.nullptr(A)
                xy.next2 = lltype.nullptr(A)
                xy.next3 = lltype.nullptr(A)
                virtual_ref_finish(vref, xy)
                exctx.topframeref = vref_None
            return exctx.m
        #
        res = self.meta_interp(f, [30])
        assert res == 13
        self.check_resops(new_with_vtable=2,   # the vref, but not XY()
                          new_array=0)         # and neither next1/2/3
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
                exctx.topframeref = vref = virtual_ref(xy)
                if n == 13:
                    externalfn(n)
                n -= 1
                exctx.topframeref = vref_None
                xy.next1 = lltype.nullptr(A)
                xy.next2 = lltype.nullptr(A)
                xy.next3 = lltype.nullptr(A)
                virtual_ref_finish(vref, xy)
            return exctx.m
        #
        res = self.meta_interp(f, [30])
        assert res == 13
        self.check_resops(new_with_vtable=0, # all virtualized in the n!=13 loop
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
                exctx.topframeref = vref = virtual_ref(xy)
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
                virtual_ref_finish(vref, xy)
            return exctx.m
        #
        res = self.meta_interp(f, [72])
        assert res == 6
        self.check_loop_count(2)     # the loop and the bridge
        self.check_resops(new_with_vtable=2,  # loop: nothing; bridge: vref, xy
                         new_array=2)        # bridge: next4, next5
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
                exctx.topframeref = vref = virtual_ref(xy)
                xy.next1 = lltype.malloc(A, 0)
                n = exctx.topframeref().n - 1
                xy.next1 = lltype.nullptr(A)
                exctx.topframeref = vref_None
                virtual_ref_finish(vref, xy)
            return 1
        #
        res = self.meta_interp(f, [15])
        assert res == 1
        self.check_resops(new_with_vtable=4,     # vref, xy
                          new_array=2)           # next1
        self.check_aborted_count(0)

    def test_recursive_call_1(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'rec', 'frame'])
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
                exctx.topframeref = vref = virtual_ref(xy)
                m = f(xy, n, reclevel-1)
                assert m == n
                n -= 1
                exctx.topframeref = vref_None
                virtual_ref_finish(vref, xy)
            return 2
        def main(n, reclevel):
            return f(XY(), n, reclevel)
        #
        res = self.meta_interp(main, [15, 1])
        assert res == main(15, 1)
        self.check_aborted_count(0)

    def test_recursive_call_2(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'rec', 'frame'])
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
                exctx.topframeref = vref = virtual_ref(xy)
                if reclevel > 0:
                    m = f(xy, frame.n, reclevel-1)
                    assert xy.n == m
                    n -= 1
                else:
                    n -= 2
                exctx.topframeref = vref_None
                virtual_ref_finish(vref, xy)
            return frame.n
        def main(n, reclevel):
            return f(XY(), n, reclevel)
        #
        res = self.meta_interp(main, [10, 2])
        assert res == main(10, 2)
        self.check_aborted_count(0)

    def test_alloc_virtualref_and_then_alloc_structure(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        #
        class XY:
            pass
        class ExCtx:
            pass
        exctx = ExCtx()
        @dont_look_inside
        def escapexy(xy):
            print 'escapexy:', xy.n
            if xy.n % 5 == 0:
                vr = exctx.vr
                print 'accessing via vr:', vr()
                assert vr() is xy
        #
        def f(n):
            while n > 0:
                myjitdriver.jit_merge_point(n=n)
                xy = XY()
                xy.n = n
                vr = virtual_ref(xy)
                # force the virtualref to be allocated
                exctx.vr = vr
                # force xy to be allocated
                escapexy(xy)
                # clean up
                exctx.vr = vref_None
                virtual_ref_finish(vr, xy)
                n -= 1
            return 1
        #
        res = self.meta_interp(f, [15])
        assert res == 1
        self.check_resops(new_with_vtable=4)     # vref, xy

    def test_cannot_use_invalid_virtualref(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        #
        class XY:
            n = 0
        #
        def fn(n):
            res = False
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                xy = XY()
                xy.n = n
                vref = virtual_ref(xy)
                virtual_ref_finish(vref, xy)
                vref() # raises InvalidVirtualRef when jitted
                n -= 1
            return res
        #
        py.test.raises(InvalidVirtualRef, "fn(10)")
        py.test.raises(LLException, "self.meta_interp(fn, [10])")

    def test_call_virtualref_already_forced(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'res'])
        #
        class XY:
            n = 0
        #
        @dont_look_inside
        def force_it(vref, n):
            if n % 6 == 0:
                return vref().n
            return 0
        def fn(n):
            res = 0
            while n > 0:
                myjitdriver.can_enter_jit(n=n, res=res)
                myjitdriver.jit_merge_point(n=n, res=res)
                xy = XY()
                xy.n = n
                vref = virtual_ref(xy)
                force_it(vref, n)
                virtual_ref_finish(vref, xy)
                res += force_it(vref, n) # doesn't raise, because it was already forced
                n -= 1
            return res
        #
        assert fn(10) == 6
        res = self.meta_interp(fn, [10])
        assert res == 6

    def test_is_virtual(self):
        myjitdriver = JitDriver(greens=[], reds=['n', 'res1'])
        class X:
            pass
        @dont_look_inside
        def residual(vref):
            return vref.virtual
        #
        def f(n):
            res1 = -42
            while n > 0:
                myjitdriver.jit_merge_point(n=n, res1=res1)
                x = X()
                vref = virtual_ref(x)
                res1 = residual(vref)
                virtual_ref_finish(vref, x)
                n -= 1
            return res1
        #
        res = self.meta_interp(f, [10])
        assert res == 1

    def test_is_not_virtual_none(self):
        myjitdriver = JitDriver(greens=[], reds=['n', 'res1'])
        @dont_look_inside
        def residual(vref):
            return vref.virtual
        #
        def f(n):
            res1 = -42
            while n > 0:
                myjitdriver.jit_merge_point(n=n, res1=res1)
                res1 = residual(vref_None)
                n -= 1
            return res1
        #
        res = self.meta_interp(f, [10])
        assert res == 0

    def test_is_not_virtual_non_none(self):
        myjitdriver = JitDriver(greens=[], reds=['n', 'res1'])
        class X:
            pass
        @dont_look_inside
        def residual(vref):
            return vref.virtual
        #
        def f(n):
            res1 = -42
            while n > 0:
                myjitdriver.jit_merge_point(n=n, res1=res1)
                x = X()
                res1 = residual(non_virtual_ref(x))
                n -= 1
            return res1
        #
        res = self.meta_interp(f, [10])
        assert res == 0


class TestLLtype(VRefTests, LLJitMixin):
    pass
